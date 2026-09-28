"""Upgrade planner: costs, deck readiness and which upgrades give the most for the gold.

The API reports copies held but not gold or wild cards, so "can upgrade now" means
"you have enough copies"; the gold is shown separately.
"""

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlmodel import Session, col, select

from ..domain.cards import (
    CARDS_TO_LEVEL,
    GOLD_TO_LEVEL,
    MAX_LEVEL,
    card_level,
    is_tower_troop,
    upgrade_cost,
)
from ..models import Battle, utcnow


def _card_plan(card: dict[str, Any], target_level: int) -> dict[str, Any]:
    rarity = card["rarity"]
    level = card_level(card)
    count = card.get("count", 0)
    maxed = level >= MAX_LEVEL
    next_cards = CARDS_TO_LEVEL[rarity].get(level + 1) if not maxed else None
    next_gold = GOLD_TO_LEVEL.get(level + 1) if not maxed else None
    to_max_cards, to_max_gold = upgrade_cost(rarity, level, MAX_LEVEL)
    to_target_cards, to_target_gold = upgrade_cost(rarity, level, max(level, target_level))

    # How many levels the copies you already hold would pay for.
    levels_affordable, spare, gold_for_affordable = 0, count, 0
    for lvl in range(level + 1, MAX_LEVEL + 1):
        need = CARDS_TO_LEVEL[rarity].get(lvl, 0)
        if spare < need:
            break
        spare -= need
        levels_affordable += 1
        gold_for_affordable += GOLD_TO_LEVEL[lvl]

    return {
        "id": card["id"],
        "name": card["name"],
        "rarity": rarity,
        "elixir": card.get("elixirCost"),
        "icon": (card.get("iconUrls") or {}).get("medium"),
        "level": level,
        "count": count,
        "maxed": maxed,
        "next_cards": next_cards,
        "next_gold": next_gold,
        "can_upgrade": bool(next_cards is not None and count >= next_cards),
        "copies_missing_next": max(0, (next_cards or 0) - count) if not maxed else 0,
        "levels_affordable": levels_affordable,
        "gold_for_affordable": gold_for_affordable,
        "to_max_cards": max(0, to_max_cards - count),
        "to_max_gold": to_max_gold,
        "to_target_cards": max(0, to_target_cards - count),
        "to_target_gold": to_target_gold,
    }


def card_usage(session: Session, tag: str, days: int = 30) -> tuple[Counter[int], int]:
    """How many of the player's recent collection-deck games each card appeared in."""
    since = utcnow() - timedelta(days=days)
    decks = session.exec(
        select(Battle.deck).where(
            Battle.player_tag == tag,
            col(Battle.battle_time) >= since,
            Battle.deck_selection == "collection",
        )
    ).all()
    usage: Counter[int] = Counter()
    for deck in decks:
        usage.update({c["id"] for c in deck})
    return usage, len(decks)


def opponent_avg_level(session: Session, tag: str, days: int = 30) -> float | None:
    since = utcnow() - timedelta(days=days)
    levels = session.exec(
        select(Battle.opp_avg_level).where(
            Battle.player_tag == tag,
            col(Battle.battle_time) >= since,
            col(Battle.mode_group).in_(["ladder", "ranked"]),
        )
    ).all()
    levels = [lvl for lvl in levels if lvl is not None]
    return round(sum(levels) / len(levels), 2) if levels else None


def upgrade_plan(
    session: Session, profile: dict[str, Any], target_level: int = MAX_LEVEL
) -> dict[str, Any]:
    target_level = max(1, min(MAX_LEVEL, target_level))
    cards = [c for c in profile.get("cards") or [] if not is_tower_troop(c) and c.get("rarity")]
    plans = {c["id"]: _card_plan(c, target_level) for c in cards}

    usage, total_games = card_usage(session, profile["tag"])
    for pid, plan in plans.items():
        plan["usage"] = round(usage.get(pid, 0) / total_games, 3) if total_games else 0.0

    deck_ids = [c["id"] for c in profile.get("currentDeck") or [] if c["id"] in plans]
    deck = [plans[i] for i in deck_ids]
    opp_level = opponent_avg_level(session, profile["tag"])
    for plan in deck:
        plan["vs_opponents"] = round(plan["level"] - opp_level, 2) if opp_level else None

    # Priority: cards you actually play, cheapest real level gain first.
    relevant = {i for i in plans if usage.get(i)} | set(deck_ids)
    upgradable_now = sorted(
        (plans[i] for i in relevant if plans[i]["can_upgrade"]),
        key=lambda p: (-(p["usage"] + (1 if p["id"] in deck_ids else 0)), p["next_gold"] or 0),
    )
    blocked = sorted(
        (plans[i] for i in relevant if not plans[i]["maxed"] and not plans[i]["can_upgrade"]),
        key=lambda p: p["copies_missing_next"] / max(1, p["next_cards"] or 1),
    )

    all_plans = list(plans.values())
    return {
        "target_level": target_level,
        "opponent_avg_level": opp_level,
        "games_analyzed": total_games,
        "deck": deck,
        "deck_summary": {
            "avg_level": round(sum(p["level"] for p in deck) / len(deck), 2) if deck else None,
            "gold_to_target": sum(p["to_target_gold"] for p in deck),
            "copies_missing_to_target": sum(p["to_target_cards"] for p in deck),
            "cards_at_target": sum(p["level"] >= target_level for p in deck),
            "gold_to_max": sum(p["to_max_gold"] for p in deck),
            "gold_for_affordable": sum(p["gold_for_affordable"] for p in deck),
        },
        "upgradable_now": upgradable_now[:12],
        "closest_blocked": blocked[:12],
        "collection_summary": {
            "cards": len(all_plans),
            "maxed": sum(p["maxed"] for p in all_plans),
            "upgradable_now": sum(p["can_upgrade"] for p in all_plans),
            "gold_to_max_all": sum(p["to_max_gold"] for p in all_plans),
            "gold_for_all_affordable": sum(p["gold_for_affordable"] for p in all_plans),
            "by_level": dict(sorted(Counter(p["level"] for p in all_plans).items())),
        },
        "cards": sorted(all_plans, key=lambda p: (-p["level"], p["name"])),
        "notes": [
            "Costs are the post Level-16 (Nov 2025) table; the API doesn't expose them.",
            "'Can upgrade' only checks copies. The API doesn't report gold, gems or wild cards.",
        ],
    }
