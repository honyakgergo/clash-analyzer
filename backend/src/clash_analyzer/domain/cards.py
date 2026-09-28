"""Card level normalization, Evo/Hero flags and the upgrade cost table.

The API reports levels on a rarity-relative scale (a max legendary is ``level 8 / maxLevel 8``).
The in-game level is ``level + (MAX_LEVEL - maxLevel)``.

Upgrade costs are not exposed by the API. The table below is the post "Level 16 update"
economy (24 Nov 2025), cross-checked in Sept 2026 against clashest.com's calculator and
timesaver.gg, and against the published totals: 365,625 gold per card and
23,086 / 4,787 / 597 / 68 / 42 copies (including the first copy) for
common / rare / epic / legendary / champion.
"""

from typing import Any

MAX_LEVEL = 16
RARITIES = ("common", "rare", "epic", "legendary", "champion")

STARTING_LEVEL = {"common": 1, "rare": 3, "epic": 6, "legendary": 9, "champion": 11}

# Copies needed to go *to* this in-game level.
CARDS_TO_LEVEL: dict[str, dict[int, int]] = {
    "common": {
        2: 2, 3: 3, 4: 10, 5: 20, 6: 50, 7: 100, 8: 200, 9: 400, 10: 800,
        11: 1000, 12: 1500, 13: 2500, 14: 3500, 15: 5500, 16: 7500,
    },
    "rare": {
        4: 2, 5: 4, 6: 10, 7: 20, 8: 50, 9: 100, 10: 200,
        11: 300, 12: 400, 13: 550, 14: 750, 15: 1000, 16: 1400,
    },
    "epic": {7: 2, 8: 4, 9: 10, 10: 20, 11: 30, 12: 50, 13: 70, 14: 100, 15: 130, 16: 180},
    "legendary": {10: 2, 11: 4, 12: 6, 13: 9, 14: 12, 15: 14, 16: 20},
    "champion": {12: 2, 13: 5, 14: 8, 15: 11, 16: 15},
}  # fmt: skip

# Gold needed to go *to* this in-game level (identical for every rarity since Nov 2025).
GOLD_TO_LEVEL: dict[int, int] = {
    2: 5, 3: 20, 4: 50, 5: 150, 6: 400, 7: 1000, 8: 2000, 9: 4000, 10: 8000,
    11: 15000, 12: 25000, 13: 40000, 14: 60000, 15: 90000, 16: 120000,
}  # fmt: skip

EVO_FLAG = 1
HERO_FLAG = 2


def in_game_level(level: int, max_level: int) -> int:
    return level + (MAX_LEVEL - max_level)


def card_level(card: dict[str, Any]) -> int:
    return in_game_level(card["level"], card["maxLevel"])


def has_evo(flags: int | None) -> bool:
    return bool((flags or 0) & EVO_FLAG)


def has_hero(flags: int | None) -> bool:
    return bool((flags or 0) & HERO_FLAG)


def forms(flags: int | None) -> list[str]:
    out = []
    if has_evo(flags):
        out.append("evo")
    if has_hero(flags):
        out.append("hero")
    return out


def upgrade_cost(rarity: str, from_level: int, to_level: int) -> tuple[int, int]:
    """Return ``(cards, gold)`` to go from ``from_level`` to ``to_level`` (in-game levels)."""
    table = CARDS_TO_LEVEL[rarity]
    cards = gold = 0
    for lvl in range(from_level + 1, to_level + 1):
        cards += table.get(lvl, 0)
        gold += GOLD_TO_LEVEL.get(lvl, 0) if lvl in table else 0
    return cards, gold


def is_tower_troop(card: dict[str, Any]) -> bool:
    return str(card.get("id", "")).startswith("159")


def icon_url(card: dict[str, Any], form: str | None = None) -> str | None:
    icons = card.get("iconUrls") or {}
    if form == "evo" and icons.get("evolutionMedium"):
        return icons["evolutionMedium"]
    if form == "hero" and icons.get("heroMedium"):
        return icons["heroMedium"]
    return icons.get("medium")


def slim_card(card: dict[str, Any]) -> dict[str, Any]:
    """Compact, normalized representation used across the app and stored in the DB."""
    flags = card.get("evolutionLevel") or 0
    form = "hero" if has_hero(flags) else "evo" if has_evo(flags) else None
    out: dict[str, Any] = {
        "id": card["id"],
        "name": card["name"],
        "rarity": card.get("rarity"),
        "elixir": card.get("elixirCost"),
        "form": form,
        "icon": icon_url(card, form),
    }
    if "level" in card and "maxLevel" in card:
        out["level"] = card_level(card)
    return out
