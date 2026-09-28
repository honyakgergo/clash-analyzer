"""Deterministic deck archetype naming.

A deck is named after its highest-priority win condition plus a family (Beatdown, Cycle,
Siege, Bait, Bridge Spam, Control). These rules follow common community vocabulary. They
label a deck's shape and say nothing about how strong it is.
"""

from collections.abc import Iterable
from dataclasses import dataclass

GOLEM, LAVA, EGIANT, GOBGIANT, EGOLEM, THREE_M = (
    26000009, 26000029, 26000085, 26000060, 26000067, 26000028,
)  # fmt: skip
GIANT, ROYAL_GIANT, RUNE_GIANT = 26000003, 26000024, 26000101
XBOW, MORTAR = 27000008, 27000002
GRAVEYARD, PEKKA, MEGA_KNIGHT = 28000010, 26000004, 26000055
BALLOON, HOG, RAM_RIDER, ROYAL_HOGS, BATTLE_RAM = 26000006, 26000021, 26000051, 26000059, 26000036
DRILL, MINER, WALL_BREAKERS, GOB_BARREL, SKELLY_BARREL = (
    27000013, 26000032, 26000058, 28000004, 26000056,
)  # fmt: skip
SPARKY, ROCKET, BOSS_BANDIT, GOB_MACHINE, ELITE_BARBS = (
    26000033, 28000003, 26000103, 26000096, 26000043,
)  # fmt: skip
MINION_GIANT, GOBLINSTEIN = 26000107, 26000099

# Battle Ram, Bandit, Royal Ghost, Dark Prince, Prince, Ram Rider, Magic Archer, Electro Wizard
BRIDGE_PARTNERS = {
    BATTLE_RAM, 26000046, 26000050, 26000027, 26000016, RAM_RIDER, 26000062, 26000042,
}  # fmt: skip
# Cards that punish at the bridge; two or more of them in a control deck make it bridge spam.
# Battle Ram, Bandit, Royal Ghost, Dark Prince, Prince, Ram Rider, Ronin, Boss Bandit, E-Barbs
BRIDGE_PRESSURE = {
    BATTLE_RAM, 26000046, 26000050, 26000027, 26000016, RAM_RIDER, 26000106, BOSS_BANDIT,
    ELITE_BARBS,
}  # fmt: skip

# (card id, display name, family). Order = naming priority.
WIN_CONDITIONS: list[tuple[int, str, str]] = [
    (GOLEM, "Golem", "beatdown"),
    (LAVA, "Lava Hound", "beatdown"),
    (EGIANT, "Electro Giant", "beatdown"),
    (GOBGIANT, "Goblin Giant", "beatdown"),
    (EGOLEM, "Elixir Golem", "beatdown"),
    (THREE_M, "Three Musketeers", "beatdown"),
    (GIANT, "Giant", "beatdown"),
    (ROYAL_GIANT, "Royal Giant", "beatdown"),
    (RUNE_GIANT, "Rune Giant", "beatdown"),
    (GOBLINSTEIN, "Goblinstein", "beatdown"),
    (XBOW, "X-Bow", "siege"),
    (MORTAR, "Mortar", "siege"),
    (GRAVEYARD, "Graveyard", "control"),
    (PEKKA, "P.E.K.K.A", "control"),
    (MEGA_KNIGHT, "Mega Knight", "control"),
    (BALLOON, "Balloon", "control"),
    (HOG, "Hog Rider", "control"),
    (RAM_RIDER, "Ram Rider", "control"),
    (ROYAL_HOGS, "Royal Hogs", "control"),
    (BATTLE_RAM, "Battle Ram", "control"),
    (DRILL, "Goblin Drill", "control"),
    (MINER, "Miner", "control"),
    (WALL_BREAKERS, "Wall Breakers", "control"),
    (MINION_GIANT, "Minion Giant", "control"),
    (GOB_BARREL, "Goblin Barrel", "bait"),
    (SKELLY_BARREL, "Skeleton Barrel", "bait"),
    (SPARKY, "Sparky", "control"),
    (BOSS_BANDIT, "Boss Bandit", "control"),
    (GOB_MACHINE, "Goblin Machine", "control"),
    (ELITE_BARBS, "Elite Barbarians", "control"),
    (ROCKET, "Rocket", "control"),
]

CYCLE_MAX_ELIXIR = 3.1
FAMILY_LABEL = {
    "beatdown": "Beatdown",
    "siege": "Siege",
    "control": "Control",
    "cycle": "Cycle",
    "bait": "Bait",
    "bridge_spam": "Bridge Spam",
    "other": "",
}


@dataclass(frozen=True)
class Archetype:
    name: str
    family: str
    win_condition: str | None


def classify_deck(card_ids: Iterable[int], avg_elixir: float | None) -> Archetype:
    ids = set(card_ids)
    if not ids:
        return Archetype("Unknown", "other", None)

    present = [wc for wc in WIN_CONDITIONS if wc[0] in ids]
    if not present:
        return Archetype("Other", "other", None)

    wc_id, wc_name, family = present[0]
    if LAVA in ids and BALLOON in ids:
        return Archetype("LavaLoon", "beatdown", "Lava Hound")
    if wc_id in (GOB_BARREL, SKELLY_BARREL) or (GOB_BARREL in ids and family == "control"):
        return Archetype("Log Bait", "bait", wc_name)
    if wc_id in (PEKKA, MEGA_KNIGHT) and ids & BRIDGE_PARTNERS:
        return Archetype(f"{wc_name} Bridge Spam", "bridge_spam", wc_name)
    if family == "control" and len(ids & BRIDGE_PRESSURE) >= 2:
        return Archetype(f"{wc_name} Bridge Spam", "bridge_spam", wc_name)
    if family == "control" and avg_elixir is not None and avg_elixir <= CYCLE_MAX_ELIXIR:
        family = "cycle"
    label = FAMILY_LABEL[family]
    return Archetype(f"{wc_name} {label}".strip(), family, wc_name)
