"""Meta snapshot from the top Path of Legends (Ranked) players' battlelogs.

The API has no meta statistics, so we crawl the Ranked leaderboard, pull each top player's
battlelog, and aggregate the decks. Every match is stored once (perspective-independent
key), and both decks count as observations.
"""

import logging
from collections import Counter, defaultdict
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta
from typing import Any

from sqlmodel import Session, col, select

from ..clash.client import ClashAPIError, ClashClient
from ..domain.battles import match_key, parse_battle
from ..models import MetaBattle, MetaCrawl, utcnow
from .analytics import wilson

log = logging.getLogger(__name__)

META_MODES = ("ranked", "ladder")
INVERSE = {"win": "loss", "loss": "win", "draw": "draw", "unknown": "unknown"}


async def top_players(client: ClashClient, limit: int) -> tuple[str, list[dict[str, Any]]]:
    """Current Ranked board, falling back to the latest finished season early in a season."""
    players = await client.path_of_legend_ranking("global", limit)
    if players:
        return "current season", players
    for season in reversed((await client.seasons())[-3:]):
        try:
            players = await client.path_of_legend_season_ranking(season, limit)
        except ClashAPIError:
            continue
        if players:
            return f"season {season}", players
    return "none", []


def store_meta_battles(session: Session, source_tag: str, raw_battles: list[dict[str, Any]]) -> int:
    added = 0
    for raw in raw_battles:
        pb = parse_battle(raw, source_tag)
        if pb.mode_group not in META_MODES or len(pb.deck) != 8 or len(pb.opp_deck) != 8:
            continue
        tags = [p.get("tag", "") for side in ("team", "opponent") for p in raw.get(side) or []]
        key = match_key(raw["battleTime"], tags)
        if session.get(MetaBattle, key):
            continue
        session.add(
            MetaBattle(
                id=key,
                battle_time=pb.battle_time,
                mode_group=pb.mode_group,
                source_player=source_tag,
                result_a=pb.result,
                deck_a=pb.deck,
                deck_b=pb.opp_deck,
                archetype_a=pb.archetype,
                archetype_b=pb.opp_archetype,
                avg_elixir_a=pb.avg_elixir,
                avg_elixir_b=pb.opp_avg_elixir,
            )
        )
        added += 1
    return added


async def crawl_meta(
    session_factory: Callable[[], AbstractContextManager[Session]],
    client: ClashClient,
    top_n: int,
) -> int:
    with session_factory() as session:
        crawl = MetaCrawl()
        session.add(crawl)
        session.commit()
        crawl_id = crawl.id

    try:
        source, players = await top_players(client, top_n)
        with session_factory() as session:
            crawl = session.get(MetaCrawl, crawl_id)
            assert crawl is not None
            crawl.source, crawl.players_total = source, len(players)
            session.commit()

        for i, p in enumerate(players, start=1):
            try:
                battles = await client.battlelog(p["tag"])
            except ClashAPIError as exc:
                log.warning("meta crawl: skipping %s (%s)", p["tag"], exc)
                battles = []
            with session_factory() as session:
                added = store_meta_battles(session, p["tag"], battles)
                crawl = session.get(MetaCrawl, crawl_id)
                assert crawl is not None
                crawl.players_done = i
                crawl.battles_added += added
                session.commit()

        with session_factory() as session:
            crawl = session.get(MetaCrawl, crawl_id)
            assert crawl is not None
            crawl.status, crawl.finished_at = "done", utcnow()
            session.commit()
    except Exception as exc:
        log.exception("meta crawl failed")
        with session_factory() as session:
            crawl = session.get(MetaCrawl, crawl_id)
            if crawl:
                crawl.status, crawl.error, crawl.finished_at = "failed", str(exc), utcnow()
                session.commit()
    assert crawl_id is not None
    return crawl_id


def latest_crawl(session: Session) -> MetaCrawl | None:
    return session.exec(select(MetaCrawl).order_by(col(MetaCrawl.id).desc())).first()


# -- aggregation --------------------------------------------------------------------------------


def _observations(
    session: Session, mode: str, days: int
) -> list[tuple[list[dict], str, str, float | None]]:
    query = select(MetaBattle).where(col(MetaBattle.battle_time) >= utcnow() - timedelta(days=days))
    if mode in META_MODES:
        query = query.where(MetaBattle.mode_group == mode)
    obs = []
    for m in session.exec(query).all():
        obs.append((m.deck_a, m.result_a, m.archetype_a, m.avg_elixir_a))
        obs.append((m.deck_b, INVERSE[m.result_a], m.archetype_b, m.avg_elixir_b))
    return obs


def _wr(wins: float, n: int) -> dict[str, Any]:
    low, high = wilson(wins, n)
    return {
        "games": n,
        "win_rate": round(100 * wins / n, 1) if n else None,
        "ci_low": low,
        "ci_high": high,
    }


def _points(result: str) -> float:
    return 1.0 if result == "win" else 0.5 if result == "draw" else 0.0


def meta_stats(
    session: Session, mode: str = "ranked", days: int = 14, min_deck_games: int = 3
) -> dict[str, Any]:
    obs = _observations(session, mode, days)
    total = len(obs)
    card_games: Counter[int] = Counter()
    card_wins: Counter[int] = Counter()
    card_evo: Counter[int] = Counter()
    card_info: dict[int, dict[str, Any]] = {}
    arch_games: Counter[str] = Counter()
    arch_wins: Counter[str] = Counter()
    deck_games: Counter[tuple[int, ...]] = Counter()
    deck_wins: Counter[tuple[int, ...]] = Counter()
    deck_cards: dict[tuple[int, ...], list[dict]] = {}
    deck_arch: dict[tuple[int, ...], str] = {}

    for deck, result, arch, _elixir in obs:
        pts = _points(result)
        for c in deck:
            card_games[c["id"]] += 1
            card_wins[c["id"]] += pts
            if c.get("form"):
                card_evo[c["id"]] += 1
            card_info.setdefault(
                c["id"],
                {
                    "id": c["id"],
                    "name": c["name"],
                    "icon": c.get("icon"),
                    "elixir": c.get("elixir"),
                    "rarity": c.get("rarity"),
                },
            )
        arch_games[arch] += 1
        arch_wins[arch] += pts
        key = tuple(sorted(c["id"] for c in deck))
        deck_games[key] += 1
        deck_wins[key] += pts
        deck_cards[key] = deck
        deck_arch[key] = arch

    cards = [
        {
            **card_info[cid],
            "usage": round(100 * n / total, 1) if total else 0,
            "special_form_rate": round(100 * card_evo[cid] / n, 1),
            **_wr(card_wins[cid], n),
        }
        for cid, n in card_games.items()
    ]
    cards.sort(key=lambda c: -c["games"])
    archetypes = sorted(
        (
            {"archetype": a, "usage": round(100 * n / total, 1), **_wr(arch_wins[a], n)}
            for a, n in arch_games.items()
        ),
        key=lambda a: -a["games"],
    )
    decks = sorted(
        (
            {"archetype": deck_arch[k], "cards": deck_cards[k], **_wr(deck_wins[k], n)}
            for k, n in deck_games.items()
            if n >= min_deck_games
        ),
        key=lambda d: (-d["games"], -(d["win_rate"] or 0)),
    )
    return {
        "mode": mode,
        "days": days,
        "decks_observed": total,
        "matches": total // 2,
        "cards": cards,
        "archetypes": archetypes,
        "top_decks": decks[:25],
    }


def compare_deck(
    session: Session, deck: list[dict[str, Any]], mode: str = "ranked", days: int = 14
) -> dict[str, Any]:
    """How a player's deck lines up with the meta: per-card stats, similar decks, swaps."""
    stats = meta_stats(session, mode, days, min_deck_games=1)
    by_id = {c["id"]: c for c in stats["cards"]}
    my_ids = {c["id"] for c in deck}

    my_cards = [
        {
            "id": c["id"],
            "name": c["name"],
            "icon": c.get("icon"),
            "meta_usage": by_id.get(c["id"], {}).get("usage", 0),
            "meta_win_rate": by_id.get(c["id"], {}).get("win_rate"),
            "meta_games": by_id.get(c["id"], {}).get("games", 0),
        }
        for c in deck
    ]

    exact: list[str] = []
    near: list[tuple[int, list[dict], str, str]] = []
    swap_games: Counter[int] = Counter()
    swap_wins: defaultdict[int, float] = defaultdict(float)
    for obs_deck, result, arch, _ in _observations(session, mode, days):
        ids = {c["id"] for c in obs_deck}
        if ids == my_ids:
            exact.append(result)
            continue
        shared = len(ids & my_ids)
        if shared < 5:
            continue
        near.append((shared, obs_deck, result, arch))
        for cid in ids - my_ids:
            swap_games[cid] += 1
            swap_wins[cid] += _points(result)

    suggestions = [
        {
            **by_id[cid],
            "in_similar_decks": n,
            "similar_win_rate": round(100 * swap_wins[cid] / n, 1),
        }
        for cid, n in swap_games.most_common(12)
        if cid in by_id and n >= 2
    ]
    suggestions.sort(key=lambda s: (-s["similar_win_rate"], -s["in_similar_decks"]))

    near_decks: dict[tuple[int, ...], dict[str, Any]] = {}
    for shared, obs_deck, result, arch in near:
        key = tuple(sorted(c["id"] for c in obs_deck))
        row = near_decks.setdefault(
            key, {"shared": shared, "archetype": arch, "cards": obs_deck, "games": 0, "points": 0.0}
        )
        row["games"] += 1
        row["points"] += _points(result)
    near_rows = sorted(
        (
            {
                **{k: v for k, v in r.items() if k != "points"},
                "win_rate": round(100 * r["points"] / r["games"], 1),
                "missing": [c for c in r["cards"] if c["id"] not in my_ids],
            }
            for r in near_decks.values()
        ),
        key=lambda r: (-r["shared"], -r["games"]),
    )[:10]

    return {
        "mode": mode,
        "days": days,
        "decks_observed": stats["decks_observed"],
        "my_cards": my_cards,
        "exact_matches": _wr(sum(map(_points, exact)), len(exact)),
        "similar_decks": near_rows,
        "swap_suggestions": suggestions[:8],
        "off_meta_cards": [c for c in my_cards if c["meta_usage"] < 2],
    }
