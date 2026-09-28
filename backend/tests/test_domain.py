import pytest

from clash_analyzer.clash.tags import InvalidTagError, encode_tag, normalize_tag
from clash_analyzer.domain.archetypes import classify_deck
from clash_analyzer.domain.battles import detect_result, mode_group, parse_battle, parse_battle_time
from clash_analyzer.domain.cards import (
    CARDS_TO_LEVEL,
    MAX_LEVEL,
    STARTING_LEVEL,
    card_level,
    forms,
    in_game_level,
    slim_card,
    upgrade_cost,
)

from .conftest import PLAYER_TAG, load, raw_battle

# -- tags ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["#PQGGV0JP", "PQGGV0JP", "pqggvojp", "  #pqggv0jp ", "%23PQGGV0JP", "##PQGGVOJP"],
)
def test_normalize_tag_variants(raw: str) -> None:
    assert normalize_tag(raw) == "#PQGGV0JP"


@pytest.mark.parametrize("raw", ["", "#", "#AB", "#HELLO123", "#PQGG V0JP", "#" + "P" * 20])
def test_normalize_tag_rejects_invalid(raw: str) -> None:
    with pytest.raises(InvalidTagError):
        normalize_tag(raw)


def test_encode_tag() -> None:
    assert encode_tag("pqggvojp") == "%23PQGGV0JP"


# -- card levels & costs ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "max_level", "expected"),
    [
        (16, 16, 16),
        (1, 16, 1),
        (14, 14, 16),
        (1, 14, 3),
        (11, 11, 16),
        (1, 11, 6),
        (8, 8, 16),
        (1, 8, 9),
        (6, 6, 16),
        (1, 6, 11),
    ],
)
def test_in_game_level(level: int, max_level: int, expected: int) -> None:
    assert in_game_level(level, max_level) == expected


def test_fixture_levels_are_in_range() -> None:
    for c in load("player")["cards"]:
        lvl = card_level(c)
        assert STARTING_LEVEL[c["rarity"]] <= lvl <= MAX_LEVEL, c["name"]


# Published totals: copies to max *including* the first copy, and total gold for a common.
@pytest.mark.parametrize(
    ("rarity", "copies"),
    [("common", 23086), ("rare", 4787), ("epic", 597), ("legendary", 68), ("champion", 42)],
)
def test_upgrade_table_matches_published_totals(rarity: str, copies: int) -> None:
    cards, _gold = upgrade_cost(rarity, STARTING_LEVEL[rarity], MAX_LEVEL)
    assert cards + 1 == copies


def test_common_gold_total() -> None:
    assert upgrade_cost("common", 1, MAX_LEVEL) == (23085, 365625)


def test_upgrade_cost_partial_and_noop() -> None:
    assert upgrade_cost("legendary", 14, 16) == (14 + 20, 90000 + 120000)
    assert upgrade_cost("epic", 16, 16) == (0, 0)


def test_tables_cover_every_level_from_start() -> None:
    for rarity, table in CARDS_TO_LEVEL.items():
        assert sorted(table) == list(range(STARTING_LEVEL[rarity] + 1, MAX_LEVEL + 1))


def test_forms_bitflags() -> None:
    assert forms(0) == []
    assert forms(1) == ["evo"]
    assert forms(2) == ["hero"]
    assert forms(3) == ["evo", "hero"]


def test_slim_card_uses_form_icon() -> None:
    raw = {
        "id": 1, "name": "X", "level": 8, "maxLevel": 8, "rarity": "legendary", "elixirCost": 4,
        "evolutionLevel": 1,
        "iconUrls": {"medium": "m", "evolutionMedium": "e"},
    }  # fmt: skip
    assert slim_card(raw) == {
        "id": 1, "name": "X", "rarity": "legendary", "elixir": 4, "form": "evo", "icon": "e", "level": 16,
    }  # fmt: skip


# -- battles ------------------------------------------------------------------------------------


def test_parse_battle_time() -> None:
    dt = parse_battle_time("20260309T135844.000Z")
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) == (2026, 3, 9, 13, 58, 44)
    assert dt.tzinfo is None


def test_parse_real_battlelog() -> None:
    battles = [parse_battle(b, PLAYER_TAG) for b in load("battlelog")]
    assert len(battles) == 30
    assert len({b.id for b in battles}) == 30
    for b in battles:
        assert b.mode_group == "ladder"
        assert len(b.deck) == 8 and len(b.opp_deck) == 8
        assert b.result in ("win", "loss", "draw")
        # Ladder: trophy direction must agree with the result.
        if b.trophy_change:
            assert (b.trophy_change > 0) == (b.result == "win")
        assert 1 <= b.avg_level <= 16
        assert b.archetype


def test_result_precedence() -> None:
    me, opp = {"crowns": 0}, {"crowns": 1}
    assert detect_result({"boatBattleWon": True}, me, opp) == "win"
    assert (
        detect_result({}, {"crowns": 1, "trophyChange": 30}, {"crowns": 1, "trophyChange": -30})
        == "win"
    )
    # Path of Legends draw: both lose rating -> falls through to crowns -> draw.
    assert (
        detect_result({}, {"crowns": 1, "trophyChange": -5}, {"crowns": 1, "trophyChange": -5})
        == "draw"
    )
    assert detect_result({}, {"crowns": 3}, {"crowns": 1}) == "win"
    assert detect_result({}, {"crowns": 0}, {"crowns": 1}) == "loss"
    assert detect_result({}, {}, {}) == "unknown"


@pytest.mark.parametrize(
    ("btype", "mode", "expected"),
    [
        ("PvP", "Ladder", "ladder"),
        ("PvP", "Ladder_GoldRush", "ladder"),
        ("pathOfLegend", "Ranked1v1_NewArena2", "ranked"),
        ("trail", "Ladder", "seasonal"),
        ("riverRacePvP", "CW_Battle_1v1", "war"),
        ("boatBattle", "ClanWar_BoatBattle", "war"),
        ("tournament", "Tournament", "tournament"),
        ("trail", "Challenge_AllCards", "event"),
        ("friendly", "Friendly", "friendly"),
        ("unknown", "X", "other"),
    ],
)
def test_mode_group(btype: str, mode: str, expected: str) -> None:
    assert mode_group({"type": btype, "gameMode": {"name": mode}, "team": [{}]}) == expected


def test_two_v_two_finds_me_by_tag() -> None:
    raw = raw_battle(crowns=2, opp_crowns=1)
    partner = {**raw["team"][0], "tag": "#PARTNER", "crowns": 2}
    raw["team"] = [partner, raw["team"][0]]
    raw["opponent"].append({**raw["opponent"][0], "tag": "#OPP2"})
    b = parse_battle(raw, PLAYER_TAG)
    assert b.mode_group == "2v2"
    assert b.result == "win"


def test_level_gap_and_evo_counts() -> None:
    cards = [dict(c) for c in raw_battle()["team"][0]["cards"]]
    cards[0]["evolutionLevel"] = 1
    cards[1]["evolutionLevel"] = 2
    b = parse_battle(raw_battle(my_level=13, opp_level=14, my_cards=cards), PLAYER_TAG)
    assert b.level_gap == -1.0
    assert (b.evo_count, b.hero_count) == (1, 1)


# -- archetypes ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ids", "elixir", "name"),
    [
        ({26000009, 26000017}, 4.5, "Golem Beatdown"),
        ({26000029, 26000006}, 4.0, "LavaLoon"),
        ({26000021, 26000030}, 2.6, "Hog Rider Cycle"),
        ({26000021, 26000030}, 3.8, "Hog Rider Control"),
        ({28000004, 26000026}, 2.9, "Log Bait"),
        ({26000004, 26000046}, 4.0, "P.E.K.K.A Bridge Spam"),
        ({26000036, 26000046, 26000050}, 3.5, "Battle Ram Bridge Spam"),
        ({27000008, 26000038}, 3.0, "X-Bow Siege"),
        ({26000000, 26000001}, 3.0, "Other"),
        (set(), None, "Unknown"),
    ],
)
def test_classify_deck(ids: set[int], elixir: float | None, name: str) -> None:
    assert classify_deck(ids, elixir).name == name


def test_win_condition_ids_exist_in_catalog() -> None:
    from clash_analyzer.domain.archetypes import BRIDGE_PRESSURE, WIN_CONDITIONS

    catalog = {c["id"]: c["name"] for c in load("cards")["items"]}
    for cid, name, _ in WIN_CONDITIONS:
        assert catalog.get(cid) == name
    assert set(catalog) >= BRIDGE_PRESSURE
