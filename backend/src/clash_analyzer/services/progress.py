"""Profile summary, progress over time, mastery and achievements."""

import re
from datetime import timedelta
from typing import Any

from sqlmodel import Session, col, select

from ..domain.cards import card_level, forms, is_tower_troop, slim_card
from ..models import Battle, PlayerSnapshot

# Mastery badges use internal card names; most match the display name, these do not.
MASTERY_ALIASES = {
    "RageBarbarian": "Lumberjack",
    "AxeMan": "Executioner",
    "AngryBarbarians": "Elite Barbarians",
    "BlowdartGoblin": "Dart Goblin",
    "FirespiritHut": "Furnace",
    "MiniSparkys": "Zappies",
    "BarbLog": "Barbarian Barrel",
    "DarkWitch": "Night Witch",
    "IceSpirits": "Ice Spirit",
    "FireSpirits": "Fire Spirit",
    "ZapMachine": "Sparky",
    "SkeletonHorde": "Skeleton Army",
    "SkeletonWarriors": "Guards",
    "SkeletonBalloon": "Skeleton Barrel",
    "MovingCannon": "Cannon Cart",
    "IceGolemite": "Ice Golem",
    "Ghost": "Royal Ghost",
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _pretty(internal: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", internal)


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    wins, losses = profile.get("wins", 0), profile.get("losses", 0)
    badges = {b["name"]: b for b in profile.get("badges") or []}
    deck = [slim_card(c) for c in profile.get("currentDeck") or []]
    elixirs = [c["elixir"] for c in deck if c.get("elixir") is not None]
    support = profile.get("currentDeckSupportCards") or []
    return {
        "tag": profile["tag"],
        "name": profile.get("name"),
        "trophies": profile.get("trophies"),
        "best_trophies": profile.get("bestTrophies"),
        "legacy_best_trophies": profile.get("legacyTrophyRoadHighScore"),
        "arena": (profile.get("arena") or {}).get("name"),
        "king_tower_level": profile.get("kingTowerLevel"),
        "collection_level": profile.get("collectionLevel"),
        "wins": wins,
        "losses": losses,
        "win_rate": round(100 * wins / (wins + losses), 1) if wins + losses else None,
        "battle_count": profile.get("battleCount"),
        "three_crown_wins": profile.get("threeCrownWins"),
        "three_crown_rate": round(100 * profile.get("threeCrownWins", 0) / wins, 1)
        if wins
        else None,
        "win_streak": profile.get("currentWinLoseStreak"),
        "challenge_max_wins": profile.get("challengeMaxWins"),
        "challenge_cards_won": profile.get("challengeCardsWon"),
        "tournament_battles": profile.get("tournamentBattleCount"),
        "donations": profile.get("donations"),
        "donations_received": profile.get("donationsReceived"),
        "total_donations": profile.get("totalDonations"),
        "war_day_wins": profile.get("warDayWins"),
        "star_points": profile.get("starPoints"),
        "days_played": (badges.get("YearsPlayed") or {}).get("progress"),
        "clan": profile.get("clan"),
        "role": profile.get("role"),
        "ranked": {
            "current": profile.get("currentPathOfLegendSeasonResult"),
            "last": profile.get("lastPathOfLegendSeasonResult"),
            "best": profile.get("bestPathOfLegendSeasonResult"),
        },
        "league_statistics": profile.get("leagueStatistics"),
        "current_deck": deck,
        "current_deck_avg_elixir": round(sum(elixirs) / len(elixirs), 2) if elixirs else None,
        "current_deck_avg_level": round(sum(c["level"] for c in deck) / len(deck), 2)
        if deck
        else None,
        "tower_troop": slim_card(support[0]) if support else None,
        "favourite_card": slim_card(profile["currentFavouriteCard"])
        if profile.get("currentFavouriteCard")
        else None,
        "other_modes": [
            {
                "key": key,
                "arena": (val.get("arena") or {}).get("name"),
                "trophies": val.get("trophies"),
                "best_trophies": val.get("bestTrophies"),
            }
            for key, val in (profile.get("progress") or {}).items()
        ],
    }


def collection(profile: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for c in profile.get("cards") or []:
        item = slim_card({**c, "evolutionLevel": 0})
        item.update(
            count=c.get("count", 0),
            star_level=c.get("starLevel", 0),
            owned_forms=forms(c.get("evolutionLevel")),
            possible_forms=forms(c.get("maxEvolutionLevel")),
            icons=c.get("iconUrls") or {},
        )
        out.append(item)
    return sorted(out, key=lambda c: (-c["level"], c["name"]))


def progress_timeseries(session: Session, tag: str) -> dict[str, Any]:
    snaps = session.exec(
        select(PlayerSnapshot)
        .where(PlayerSnapshot.player_tag == tag)
        .order_by(col(PlayerSnapshot.taken_at))
    ).all()
    battles = session.exec(
        select(Battle)
        .where(Battle.player_tag == tag, col(Battle.mode_group).in_(["ladder", "ranked"]))
        .order_by(col(Battle.battle_time))
    ).all()

    trophy_path = [
        {
            "time": b.battle_time.isoformat() + "Z",
            "mode": b.mode_group,
            "trophies": b.starting_trophies + (b.trophy_change or 0),
            "change": b.trophy_change or 0,
            "result": b.result,
        }
        for b in battles
        if b.starting_trophies is not None
    ]

    series = [
        {
            "time": s.taken_at.isoformat() + "Z",
            **s.model_dump(exclude={"id", "player_tag", "taken_at"}),
        }
        for s in snaps
    ]

    deltas: dict[str, Any] = {}
    if snaps:
        latest = snaps[-1]
        for label, days in (("day", 1), ("week", 7), ("month", 30)):
            cutoff = latest.taken_at - timedelta(days=days)
            base = next((s for s in reversed(snaps) if s.taken_at <= cutoff), snaps[0])
            if base is latest:
                deltas[label] = None
                continue
            deltas[label] = {
                "since": base.taken_at.isoformat() + "Z",
                "trophies": latest.trophies - base.trophies,
                "collection_level": _diff(latest.collection_level, base.collection_level),
                "king_tower_level": _diff(latest.king_tower_level, base.king_tower_level),
                "wins": latest.wins - base.wins,
                "battles": latest.battle_count - base.battle_count,
                "mastery_levels": latest.mastery_levels - base.mastery_levels,
                "cards_maxed": latest.cards_maxed - base.cards_maxed,
            }
    return {"snapshots": series, "trophy_path": trophy_path, "deltas": deltas}


def _diff(a: int | None, b: int | None) -> int | None:
    return a - b if a is not None and b is not None else None


def mastery_overview(profile: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    by_norm = {_norm(c["name"]): c for c in catalog}
    owned = {c["id"]: c for c in profile.get("cards") or []}
    mastery, other = [], []
    for b in profile.get("badges") or []:
        name = b.get("name", "")
        level, max_level = b.get("level"), b.get("maxLevel")
        progress, target = b.get("progress", 0), b.get("target")
        entry: dict[str, Any] = {
            "badge": name,
            "level": level,
            "max_level": max_level,
            "progress": progress,
            "target": target,
            "icon": (b.get("iconUrls") or {}).get("large"),
            "maxed": level is not None and level == max_level,
            "completion": round(progress / target, 3) if target else 1.0,
        }
        if name.startswith("Mastery"):
            internal = name.removeprefix("Mastery").replace(" ", "")
            card = by_norm.get(_norm(MASTERY_ALIASES.get(internal, internal)))
            entry["card"] = card["name"] if card else _pretty(internal)
            entry["card_icon"] = (card.get("iconUrls") or {}).get("medium") if card else None
            if card and card["id"] in owned:
                entry["card_level"] = card_level(owned[card["id"]])
            mastery.append(entry)
        else:
            entry["title"] = _pretty(name)
            other.append(entry)

    in_progress = [m for m in mastery if not m["maxed"]]
    in_progress.sort(key=lambda m: -m["completion"])
    achievements = [
        {
            "name": a.get("name"),
            "info": a.get("info"),
            "stars": a.get("stars", 0),
            "value": a.get("value", 0),
            "target": a.get("target", 0),
            "completion": min(1.0, round(a["value"] / a["target"], 3)) if a.get("target") else 1.0,
        }
        for a in profile.get("achievements") or []
    ]
    owned_ids = {c["id"] for c in profile.get("cards") or [] if not is_tower_troop(c)}
    return {
        "mastery": sorted(mastery, key=lambda m: (-(m["level"] or 0), m["card"])),
        "closest_mastery": in_progress[:10],
        "mastery_total_levels": sum(m["level"] or 0 for m in mastery),
        "mastery_maxed": sum(m["maxed"] for m in mastery),
        "mastery_started": len(mastery),
        "cards_without_mastery": max(0, len(owned_ids) - len(mastery)),
        "badges": other,
        "achievements": achievements,
    }
