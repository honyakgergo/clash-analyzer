"""Battle analytics over the stored battle history.

Every aggregate reports its sample size, and the insight generator only speaks up above a
minimum sample. Small samples lie, especially with a battlelog of only ~30 games.
"""

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session, col, select

from ..models import Battle, utcnow

MODE_FILTERS: dict[str, tuple[str, ...] | None] = {
    "competitive": ("ladder", "ranked"),
    "all": None,
    "ladder": ("ladder",),
    "ranked": ("ranked",),
    "seasonal": ("seasonal",),
    "war": ("war",),
    "2v2": ("2v2",),
    "event": ("event", "tournament"),
    "friendly": ("friendly",),
}

SESSION_GAP = timedelta(minutes=20)
MIN_SAMPLE = 5


# -- helpers ------------------------------------------------------------------------------------


def wilson(wins: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a win rate, as percentages."""
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (centre - margin) / denom, 1), round(100 * (centre + margin) / denom, 1)


def _score(b: Battle) -> float:
    return 1.0 if b.result == "win" else 0.5 if b.result == "draw" else 0.0


def rate(battles: list[Battle]) -> dict[str, Any]:
    n = len(battles)
    wins = sum(b.result == "win" for b in battles)
    losses = sum(b.result == "loss" for b in battles)
    draws = sum(b.result == "draw" for b in battles)
    score = sum(_score(b) for b in battles)
    low, high = wilson(score, n)
    return {
        "games": n,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": round(100 * score / n, 1) if n else None,
        "ci_low": low if n else None,
        "ci_high": high if n else None,
    }


def _group(battles: Iterable[Battle], key: Callable[[Battle], Any]) -> dict[Any, list[Battle]]:
    groups: dict[Any, list[Battle]] = defaultdict(list)
    for b in battles:
        k = key(b)
        if k is not None:
            groups[k].append(b)
    return groups


def _buckets(
    battles: list[Battle],
    value: Callable[[Battle], float | None],
    edges: list[tuple[str, float, float]],
) -> list[dict[str, Any]]:
    out = []
    for label, lo, hi in edges:
        members = [b for b in battles if (v := value(b)) is not None and lo <= v < hi]
        out.append({"bucket": label, **rate(members)})
    return out


def _tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _local(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt.replace(tzinfo=UTC).astimezone(tz)


# -- loading ------------------------------------------------------------------------------------


def load_battles(
    session: Session, tag: str, mode: str = "competitive", days: int | None = None
) -> list[Battle]:
    query = select(Battle).where(Battle.player_tag == tag)
    groups = MODE_FILTERS.get(mode, MODE_FILTERS["competitive"])
    if groups:
        query = query.where(col(Battle.mode_group).in_(groups))
    if days:
        query = query.where(col(Battle.battle_time) >= utcnow() - timedelta(days=days))
    return list(session.exec(query.order_by(col(Battle.battle_time))).all())


# -- sections -----------------------------------------------------------------------------------


def summary(battles: list[Battle]) -> dict[str, Any]:
    wins = [b for b in battles if b.result == "win"]
    losses = [b for b in battles if b.result == "loss"]
    gaps = [b.avg_level - b.opp_avg_level for b in battles if b.avg_level and b.opp_avg_level]
    leaked = [b.elixir_leaked for b in battles if b.elixir_leaked is not None]
    tc = [b.trophy_change for b in battles if b.mode_group == "ladder" and b.trophy_change]
    return {
        **rate(battles),
        "three_crown_wins": sum(b.crowns == 3 for b in wins),
        "three_crowned": sum(b.opp_crowns == 3 for b in losses),
        "avg_elixir_leaked": round(sum(leaked) / len(leaked), 2) if leaked else None,
        "avg_level_gap": round(sum(gaps) / len(gaps), 2) if gaps else None,
        "net_trophies": sum(tc),
        "avg_trophies_win": _mean([t for t in tc if t > 0]),
        "avg_trophies_loss": _mean([t for t in tc if t < 0]),
        "first_battle": battles[0].battle_time.isoformat() + "Z" if battles else None,
        "last_battle": battles[-1].battle_time.isoformat() + "Z" if battles else None,
    }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def by_mode(all_battles: list[Battle]) -> list[dict[str, Any]]:
    groups = _group(all_battles, lambda b: b.mode_group)
    return sorted(({"mode": m, **rate(bs)} for m, bs in groups.items()), key=lambda r: -r["games"])


def timeline(battles: list[Battle], tz: ZoneInfo) -> dict[str, Any]:
    daily = _group(battles, lambda b: _local(b.battle_time, tz).date().isoformat())
    hourly = _group(battles, lambda b: _local(b.battle_time, tz).hour)
    weekday = _group(battles, lambda b: _local(b.battle_time, tz).weekday())
    return {
        "daily": [
            {
                "date": d,
                **rate(bs),
                "net_trophies": sum(b.trophy_change or 0 for b in bs if b.mode_group == "ladder"),
            }
            for d, bs in sorted(daily.items())
        ],
        "hourly": [{"hour": h, **rate(hourly.get(h, []))} for h in range(24)],
        "weekday": [{"weekday": d, **rate(weekday.get(d, []))} for d in range(7)],
    }


def streaks_and_tilt(battles: list[Battle]) -> dict[str, Any]:
    decided = [b for b in battles if b.result in ("win", "loss", "draw")]
    after_win, after_loss, after_2_losses, after_3_wins = [], [], [], []
    run_kind, run_len = None, 0
    longest = {"win": 0, "loss": 0}
    for b in decided:
        if run_kind == "win":
            after_win.append(b)
            if run_len >= 3:
                after_3_wins.append(b)
        elif run_kind == "loss":
            after_loss.append(b)
            if run_len >= 2:
                after_2_losses.append(b)
        if b.result == run_kind:
            run_len += 1
        else:
            run_kind, run_len = (b.result, 1) if b.result != "draw" else (None, 0)
        if run_kind in longest:
            longest[run_kind] = max(longest[run_kind], run_len)

    sessions: list[list[Battle]] = []
    for b in decided:
        if sessions and b.battle_time - sessions[-1][-1].battle_time <= SESSION_GAP:
            sessions[-1].append(b)
        else:
            sessions.append([b])

    by_index: dict[str, list[Battle]] = defaultdict(list)
    for s in sessions:
        for i, b in enumerate(s, start=1):
            label = str(i) if i <= 3 else "4-5" if i <= 5 else "6-9" if i <= 9 else "10+"
            by_index[label].append(b)

    return {
        "current": {"kind": run_kind, "length": run_len},
        "longest_win_streak": longest["win"],
        "longest_loss_streak": longest["loss"],
        "after_win": rate(after_win),
        "after_loss": rate(after_loss),
        "after_2_losses": rate(after_2_losses),
        "after_3_wins": rate(after_3_wins),
        "sessions": {
            "count": len(sessions),
            "avg_length": round(sum(map(len, sessions)) / len(sessions), 1) if sessions else 0,
            "by_game_index": [
                {"index": k, **rate(by_index[k])}
                for k in ("1", "2", "3", "4-5", "6-9", "10+")
                if by_index.get(k)
            ],
            "recent": [
                {
                    "start": s[0].battle_time.isoformat() + "Z",
                    "end": s[-1].battle_time.isoformat() + "Z",
                    **rate(s),
                    "net_trophies": sum(
                        b.trophy_change or 0 for b in s if b.mode_group == "ladder"
                    ),
                }
                for s in sessions[-10:][::-1]
            ],
        },
    }


LEVEL_GAP_EDGES = [
    ("≤ -1", -99.0, -1.0),
    ("-1 to -0.3", -1.0, -0.3),
    ("even", -0.3, 0.3),
    ("+0.3 to +1", 0.3, 1.0),
    ("≥ +1", 1.0, 99.0),
]


def level_analysis(battles: list[Battle]) -> dict[str, Any]:
    gap = lambda b: (b.avg_level - b.opp_avg_level) if b.avg_level and b.opp_avg_level else None  # noqa: E731
    losses = [b for b in battles if b.result == "loss" and gap(b) is not None]
    under = [b for b in losses if gap(b) <= -0.5]  # type: ignore[operator]
    return {
        "buckets": _buckets(battles, gap, LEVEL_GAP_EDGES),
        "losses_underleveled": len(under),
        "losses_total": len(losses),
        "share_losses_underleveled": round(100 * len(under) / len(losses), 1) if losses else None,
        "even_level": rate([b for b in battles if (g := gap(b)) is not None and abs(g) < 0.3]),
    }


def _margin(b: Battle) -> int | None:
    if b.crowns is None or b.opp_crowns is None:
        return None
    return b.crowns - b.opp_crowns


def close_games(battles: list[Battle]) -> dict[str, Any]:
    margins = _group(battles, _margin)
    one_crown = [b for b in battles if (m := _margin(b)) is not None and abs(m) == 1]
    blowouts = [b for b in battles if (m := _margin(b)) is not None and abs(m) >= 2]
    one_crown_losses = [b for b in one_crown if b.result == "loss"]
    # HP left on the opponent's weakest standing princess tower when you lost by one crown.
    near_miss_hp = [min(b.opp_princess_hp) for b in one_crown_losses if b.opp_princess_hp]
    return {
        "margins": [{"margin": m, "games": len(bs)} for m, bs in sorted(margins.items())],
        "one_crown": rate(one_crown),
        "blowouts": rate(blowouts),
        "one_crown_losses": len(one_crown_losses),
        "near_miss_tower_hp": round(sum(near_miss_hp) / len(near_miss_hp))
        if near_miss_hp
        else None,
        "avg_king_hp_left_in_wins": _mean(
            [b.king_hp for b in battles if b.result == "win" and b.king_hp]
        ),
    }


ELIXIR_EDGES = [("< 1", 0.0, 1.0), ("1-2.5", 1.0, 2.5), ("2.5-5", 2.5, 5.0), ("5+", 5.0, 999.0)]


def elixir_analysis(battles: list[Battle]) -> dict[str, Any]:
    wins = [b.elixir_leaked for b in battles if b.result == "win" and b.elixir_leaked is not None]
    losses = [
        b.elixir_leaked for b in battles if b.result == "loss" and b.elixir_leaked is not None
    ]
    return {
        "buckets": _buckets(battles, lambda b: b.elixir_leaked, ELIXIR_EDGES),
        "avg_in_wins": _mean(wins),
        "avg_in_losses": _mean(losses),
    }


def evo_analysis(battles: list[Battle]) -> dict[str, Any]:
    advantage = lambda b: (b.evo_count + b.hero_count) - (b.opp_evo_count + b.opp_hero_count)  # noqa: E731
    return {
        "by_my_evos": [
            {"count": k, **rate(v)}
            for k, v in sorted(_group(battles, lambda b: min(b.evo_count, 2)).items())
        ],
        "with_hero": rate([b for b in battles if b.hero_count]),
        "without_hero": rate([b for b in battles if not b.hero_count]),
        "special_advantage": [
            {"bucket": label, **rate([b for b in battles if cond(advantage(b))])}
            for label, cond in (
                ("fewer", lambda a: a < 0),
                ("equal", lambda a: a == 0),
                ("more", lambda a: a > 0),
            )
        ],
    }


def matchups(battles: list[Battle], min_games: int = 3) -> dict[str, Any]:
    per_card: dict[int, list[Battle]] = defaultdict(list)
    card_info: dict[int, dict[str, Any]] = {}
    for b in battles:
        for c in b.opp_deck:
            per_card[c["id"]].append(b)
            card_info.setdefault(c["id"], {"id": c["id"], "name": c["name"], "icon": c.get("icon")})
    overall = rate(battles)["win_rate"] or 0
    rows = []
    for cid, bs in per_card.items():
        r = rate(bs)
        rows.append({**card_info[cid], **r, "delta": round((r["win_rate"] or 0) - overall, 1)})
    eligible = [r for r in rows if r["games"] >= min_games]
    archetypes = _group(battles, lambda b: b.opp_archetype or "Unknown")
    return {
        "min_games": min_games,
        "nemesis": sorted(eligible, key=lambda r: (r["win_rate"], -r["games"]))[:8],
        "prey": sorted(eligible, key=lambda r: (-r["win_rate"], -r["games"]))[:8],
        "most_faced": sorted(rows, key=lambda r: -r["games"])[:12],
        "archetypes": sorted(
            ({"archetype": a, **rate(bs)} for a, bs in archetypes.items()),
            key=lambda r: -r["games"],
        ),
    }


def my_decks(battles: list[Battle]) -> list[dict[str, Any]]:
    decks = _group(battles, lambda b: tuple(sorted(c["id"] for c in b.deck)) if b.deck else None)
    rows = []
    for _key, bs in decks.items():
        latest = bs[-1]
        rows.append(
            {
                "archetype": latest.archetype,
                "cards": latest.deck,
                "avg_elixir": latest.avg_elixir,
                "last_played": latest.battle_time.isoformat() + "Z",
                **rate(bs),
            }
        )
    return sorted(rows, key=lambda r: (-r["games"], r["last_played"]))[:10]


def card_performance(battles: list[Battle]) -> list[dict[str, Any]]:
    per_card: dict[int, list[Battle]] = defaultdict(list)
    info: dict[int, dict[str, Any]] = {}
    for b in battles:
        for c in b.deck:
            per_card[c["id"]].append(b)
            info[c["id"]] = {
                "id": c["id"],
                "name": c["name"],
                "icon": c.get("icon"),
                "level": c.get("level"),
            }
    return sorted(
        ({**info[cid], **rate(bs)} for cid, bs in per_card.items()), key=lambda r: -r["games"]
    )


# -- insights -----------------------------------------------------------------------------------


def insights(report: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    s = report["summary"]
    if s["games"] < MIN_SAMPLE:
        return [
            {"level": "info", "text": "Play a few more games. Insights need at least 5 battles."}
        ]
    overall = s["win_rate"] or 0

    t = report["tilt"]
    a2 = t["after_2_losses"]
    if a2["games"] >= MIN_SAMPLE and (a2["win_rate"] or 0) <= overall - 8:
        out.append(
            {
                "level": "warn",
                "text": f"Tilt alert: after two losses in a row you win {a2['win_rate']}% "
                f"(vs {overall}% overall, {a2['games']} games). Take a break after 2 losses.",
            }
        )
    idx = [r for r in t["sessions"]["by_game_index"] if r["games"] >= MIN_SAMPLE]
    if len(idx) >= 2 and (idx[-1]["win_rate"] or 0) <= (idx[0]["win_rate"] or 0) - 10:
        out.append(
            {
                "level": "warn",
                "text": f"Long sessions hurt: game {idx[-1]['index']} of a session wins {idx[-1]['win_rate']}% "
                f"vs {idx[0]['win_rate']}% for game {idx[0]['index']}.",
            }
        )

    lv = report["levels"]
    if lv["share_losses_underleveled"] is not None and lv["losses_total"] >= MIN_SAMPLE:
        share = lv["share_losses_underleveled"]
        if share >= 50:
            out.append(
                {
                    "level": "warn",
                    "text": f"{share}% of your losses came against decks at least half a level higher. Upgrades will help more than deck changes.",
                }
            )
        elif share <= 20:
            out.append(
                {
                    "level": "info",
                    "text": f"Only {share}% of your losses were level-related. Most losses happen at even levels, so focus on matchups and play.",
                }
            )

    ex = report["elixir"]
    if (
        ex["avg_in_losses"] is not None
        and ex["avg_in_wins"] is not None
        and ex["avg_in_losses"] - ex["avg_in_wins"] >= 1
    ):
        out.append(
            {
                "level": "warn",
                "text": f"You leak {ex['avg_in_losses']} elixir in losses vs {ex['avg_in_wins']} in wins. Place cards sooner at full elixir.",
            }
        )

    nem = report["matchups"]["nemesis"]
    if nem and (nem[0]["win_rate"] or 0) < overall - 15:
        worst = nem[0]
        out.append(
            {
                "level": "warn",
                "text": f"Nemesis card: {worst['name']}. You win {worst['win_rate']}% against it over {worst['games']} games.",
            }
        )
    arche = [a for a in report["matchups"]["archetypes"] if a["games"] >= MIN_SAMPLE]
    if arche:
        worst_a = min(arche, key=lambda a: a["win_rate"] or 0)
        best_a = max(arche, key=lambda a: a["win_rate"] or 0)
        if (worst_a["win_rate"] or 0) < overall - 10:
            out.append(
                {
                    "level": "warn",
                    "text": f"Worst matchup archetype: {worst_a['archetype']} ({worst_a['win_rate']}% over {worst_a['games']} games).",
                }
            )
        if (best_a["win_rate"] or 0) > overall + 10:
            out.append(
                {
                    "level": "good",
                    "text": f"You farm {best_a['archetype']}: {best_a['win_rate']}% over {best_a['games']} games.",
                }
            )

    close = report["close_games"]
    if close["one_crown"]["games"] >= MIN_SAMPLE and (close["one_crown"]["win_rate"] or 0) < 45:
        out.append(
            {
                "level": "warn",
                "text": f"You win only {close['one_crown']['win_rate']}% of one-crown games. Tighten up defense and the final minute of your games.",
            }
        )

    hourly = [h for h in report["timeline"]["hourly"] if h["games"] >= MIN_SAMPLE]
    if len(hourly) >= 2:
        best_h = max(hourly, key=lambda h: h["win_rate"] or 0)
        worst_h = min(hourly, key=lambda h: h["win_rate"] or 0)
        if (best_h["win_rate"] or 0) - (worst_h["win_rate"] or 0) >= 20:
            out.append(
                {
                    "level": "info",
                    "text": f"Best hour: {best_h['hour']:02d}:00 ({best_h['win_rate']}%). Worst: {worst_h['hour']:02d}:00 ({worst_h['win_rate']}%).",
                }
            )

    if not out:
        out.append(
            {"level": "good", "text": "No red flags in this sample. Your results are consistent."}
        )
    return out


def analytics_report(
    session: Session,
    tag: str,
    mode: str = "competitive",
    days: int | None = None,
    tz: str | None = None,
) -> dict[str, Any]:
    zone = _tz(tz)
    battles = load_battles(session, tag, mode, days)
    all_battles = load_battles(session, tag, "all", days)
    report = {
        "mode": mode,
        "days": days,
        "timezone": str(zone),
        "summary": summary(battles),
        "by_mode": by_mode(all_battles),
        "timeline": timeline(battles, zone),
        "tilt": streaks_and_tilt(battles),
        "levels": level_analysis(battles),
        "close_games": close_games(battles),
        "elixir": elixir_analysis(battles),
        "evolutions": evo_analysis(battles),
        "matchups": matchups(battles),
        "decks": my_decks(battles),
        "cards": card_performance(battles),
        "tower_troops": [
            {"tower_troop": k, **rate(v)}
            for k, v in _group(battles, lambda b: b.tower_troop).items()
        ],
    }
    report["insights"] = insights(report)
    return report
