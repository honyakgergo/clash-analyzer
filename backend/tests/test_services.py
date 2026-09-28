from datetime import timedelta

import pytest
from sqlmodel import Session, select

from clash_analyzer.domain.battles import parse_battle
from clash_analyzer.models import Battle, MetaBattle, MetaCrawl, Player, PlayerSnapshot
from clash_analyzer.services import analytics, meta, progress, upgrades
from clash_analyzer.services.clans import clan_overview
from clash_analyzer.services.ingest import refresh_player, snapshot_from_profile, store_battles

from .conftest import CLAN_TAG, PLAYER_TAG, load, raw_battle

# -- ingest -------------------------------------------------------------------------------------


async def test_refresh_stores_profile_snapshot_and_battles(session: Session, client) -> None:
    result = await refresh_player(session, client, "pqggvojp")
    assert result.tag == PLAYER_TAG
    assert result.new_battles == 30 and result.snapshot_taken
    player = session.get(Player, PLAYER_TAG)
    assert player and player.name == "NokedliPredator" and player.clan_tag == CLAN_TAG
    assert len(session.exec(select(PlayerSnapshot)).all()) == 1


async def test_refresh_is_idempotent(session: Session, client) -> None:
    await refresh_player(session, client, PLAYER_TAG)
    again = await refresh_player(session, client, PLAYER_TAG)
    assert again.new_battles == 0
    assert not again.snapshot_taken  # inside the snapshot interval
    assert len(session.exec(select(Battle)).all()) == 30


async def test_refresh_respects_min_interval(session: Session, client, fake_api) -> None:
    await refresh_player(session, client, PLAYER_TAG)
    calls = len(fake_api.calls)
    skipped = await refresh_player(
        session, client, PLAYER_TAG, min_refresh_interval=timedelta(minutes=5)
    )
    assert skipped.skipped and len(fake_api.calls) == calls


async def test_snapshot_interval_zero_always_snapshots(session: Session, client) -> None:
    await refresh_player(session, client, PLAYER_TAG, snapshot_interval=timedelta(0))
    client._cache.clear()
    await refresh_player(session, client, PLAYER_TAG, snapshot_interval=timedelta(0))
    assert len(session.exec(select(PlayerSnapshot)).all()) == 2


def test_snapshot_from_profile() -> None:
    snap = snapshot_from_profile(load("player"))
    assert snap.trophies == 11313
    assert snap.king_tower_level == 15 and snap.collection_level == 1515
    assert snap.cards_owned == 122 and snap.cards_maxed >= 1
    assert snap.mastery_levels > 0


# -- helpers ------------------------------------------------------------------------------------


def _store(session: Session, raws: list[dict]) -> list[Battle]:
    session.add(Player(tag=PLAYER_TAG, name="Me", profile=load("player")))
    store_battles(session, PLAYER_TAG, raws)
    session.commit()
    return analytics.load_battles(session, PLAYER_TAG, "all")


# -- analytics ----------------------------------------------------------------------------------


def test_wilson_interval() -> None:
    assert analytics.wilson(0, 0) == (0.0, 0.0)
    low, high = analytics.wilson(5, 10)
    assert low < 50 < high
    assert analytics.wilson(10, 10)[1] == 100.0


def test_tilt_detects_losses_in_a_row(session: Session) -> None:
    # Pattern: L L L W  repeated -> after 2 losses you win 1/3 of the time
    results = ["L", "L", "L", "W"] * 3
    raws = [
        raw_battle(i * 3, *((0, 1) if r == "L" else (1, 0)), opp_tag=f"#O{i}")
        for i, r in enumerate(results)
    ]
    battles = _store(session, raws)
    tilt = analytics.streaks_and_tilt(battles)
    assert tilt["longest_loss_streak"] == 3
    assert tilt["after_2_losses"]["games"] == 6
    assert tilt["after_2_losses"]["wins"] == 3
    assert tilt["sessions"]["count"] == 1  # 3 minutes apart -> one session


def test_sessions_split_on_gap(session: Session) -> None:
    raws = [raw_battle(0, opp_tag="#A"), raw_battle(5, opp_tag="#B"), raw_battle(120, opp_tag="#C")]
    battles = _store(session, raws)
    assert analytics.streaks_and_tilt(battles)["sessions"]["count"] == 2


def test_level_gap_buckets(session: Session) -> None:
    raws = [raw_battle(i, 0, 1, my_level=12, opp_level=14, opp_tag=f"#U{i}") for i in range(4)]
    raws += [raw_battle(10 + i, 1, 0, opp_tag=f"#E{i}") for i in range(4)]
    lv = analytics.level_analysis(_store(session, raws))
    buckets = {b["bucket"]: b for b in lv["buckets"]}
    assert buckets["≤ -1"]["games"] == 4 and buckets["≤ -1"]["win_rate"] == 0.0
    assert buckets["even"]["games"] == 4 and buckets["even"]["win_rate"] == 100.0
    assert lv["share_losses_underleveled"] == 100.0


def test_modes_are_separated(session: Session) -> None:
    raws = [
        raw_battle(0, opp_tag="#A"),
        raw_battle(1, btype="pathOfLegend", mode="Ranked1v1", opp_tag="#B"),
        raw_battle(2, btype="trail", mode="Ladder", opp_tag="#C"),  # seasonal: excluded
    ]
    _store(session, raws)
    assert len(analytics.load_battles(session, PLAYER_TAG, "competitive")) == 2
    assert len(analytics.load_battles(session, PLAYER_TAG, "seasonal")) == 1
    assert len(analytics.load_battles(session, PLAYER_TAG, "all")) == 3


def test_full_report_on_real_battlelog(session: Session) -> None:
    _store(session, load("battlelog"))
    report = analytics.analytics_report(session, PLAYER_TAG, tz="Europe/Amsterdam")
    s = report["summary"]
    assert s["games"] == 30 and s["wins"] + s["losses"] + s["draws"] == 30
    assert sum(h["games"] for h in report["timeline"]["hourly"]) == 30
    assert sum(m["games"] for m in report["close_games"]["margins"]) == 30
    assert report["decks"] and report["matchups"]["most_faced"]
    assert report["insights"]
    assert report["timezone"] == "Europe/Amsterdam"


def test_report_with_no_battles(session: Session) -> None:
    session.add(Player(tag=PLAYER_TAG))
    session.commit()
    report = analytics.analytics_report(session, PLAYER_TAG)
    assert report["summary"]["games"] == 0
    assert report["insights"][0]["level"] == "info"


def test_bad_timezone_falls_back_to_utc(session: Session) -> None:
    session.add(Player(tag=PLAYER_TAG))
    session.commit()
    assert analytics.analytics_report(session, PLAYER_TAG, tz="Not/AZone")["timezone"] == "UTC"


def test_elixir_insight(session: Session) -> None:
    raws = [raw_battle(i * 60, 0, 1, leaked=5.0, opp_tag=f"#L{i}") for i in range(5)]
    raws += [raw_battle(1000 + i * 60, 1, 0, leaked=0.5, opp_tag=f"#W{i}") for i in range(5)]
    _store(session, raws)
    texts = " ".join(i["text"] for i in analytics.analytics_report(session, PLAYER_TAG)["insights"])
    assert "leak" in texts


# -- upgrades -----------------------------------------------------------------------------------


def test_upgrade_plan_on_real_profile(session: Session) -> None:
    _store(session, load("battlelog"))
    plan = upgrades.upgrade_plan(session, load("player"))
    assert len(plan["deck"]) == 8
    assert plan["games_analyzed"] == 30
    assert plan["collection_summary"]["cards"] == len(
        load("player")["cards"]
    )  # tower troops live in supportCards
    for c in plan["cards"]:
        assert c["maxed"] == (c["level"] == 16)
        if c["maxed"]:
            assert c["to_max_gold"] == 0 and c["next_cards"] is None
        assert c["can_upgrade"] == (not c["maxed"] and c["count"] >= c["next_cards"])
    assert all(c["usage"] == 1.0 for c in plan["deck"])  # played the same deck all 30 games


def test_card_plan_affordable_levels() -> None:
    raw = {"id": 1, "name": "K", "rarity": "common", "level": 10, "maxLevel": 16, "count": 2600}
    p = upgrades._card_plan(raw, target_level=13)
    # 10 -> 11 (1000) -> 12 (1500) uses 2500 copies; 13 needs 2500 more.
    assert p["levels_affordable"] == 2 and p["gold_for_affordable"] == 15000 + 25000
    assert p["to_target_gold"] == 15000 + 25000 + 40000
    assert p["to_target_cards"] == 1000 + 1500 + 2500 - 2600


# -- progress / mastery -------------------------------------------------------------------------


def test_profile_summary() -> None:
    s = progress.profile_summary(load("player"))
    assert s["name"] == "NokedliPredator" and len(s["current_deck"]) == 8
    assert s["win_rate"] == pytest.approx(55.7, abs=0.1)
    assert s["days_played"] == 3598
    assert s["tower_troop"]["name"]


def test_mastery_maps_every_badge_to_a_card() -> None:
    m = progress.mastery_overview(load("player"), load("cards")["items"])
    assert m["mastery_started"] == 58
    assert all(x["card_icon"] for x in m["mastery"]), [
        x["card"] for x in m["mastery"] if not x["card_icon"]
    ]
    assert all(not x["maxed"] for x in m["closest_mastery"])
    assert len(m["achievements"]) == 12


def test_progress_deltas(session: Session) -> None:
    session.add(Player(tag=PLAYER_TAG))
    base = snapshot_from_profile(load("player"))
    old = PlayerSnapshot(**{**base.model_dump(exclude={"id"}), "trophies": 11000})
    old.taken_at = base.taken_at - timedelta(days=8)
    session.add(old)
    session.add(base)
    session.commit()
    out = progress.progress_timeseries(session, PLAYER_TAG)
    assert len(out["snapshots"]) == 2
    assert out["deltas"]["week"]["trophies"] == 313
    assert out["deltas"]["day"]["trophies"] == 313  # falls back to the oldest snapshot


# -- meta ---------------------------------------------------------------------------------------


def test_meta_dedups_same_match_from_both_perspectives(session: Session) -> None:
    raw = raw_battle(0, 2, 1, btype="pathOfLegend", mode="Ranked1v1", opp_tag="#OPP0")
    flipped = {**raw, "team": raw["opponent"], "opponent": raw["team"]}
    assert meta.store_meta_battles(session, PLAYER_TAG, [raw]) == 1
    session.commit()
    assert meta.store_meta_battles(session, "#OPP0", [flipped]) == 0
    session.commit()
    stats = meta.meta_stats(session, "ranked", days=3650, min_deck_games=1)
    assert stats["matches"] == 1 and stats["decks_observed"] == 2
    golem = next(c for c in stats["cards"] if c["name"] == "Golem")
    assert golem["win_rate"] == 0.0  # the Golem side lost


def test_meta_ignores_non_competitive(session: Session) -> None:
    assert (
        meta.store_meta_battles(
            session, PLAYER_TAG, [raw_battle(0, btype="friendly", mode="Friendly")]
        )
        == 0
    )


async def test_crawl_meta_end_to_end(engine, client) -> None:
    from contextlib import contextmanager

    @contextmanager
    def factory():
        with Session(engine) as s:
            yield s

    crawl_id = await meta.crawl_meta(factory, client, top_n=3)
    with Session(engine) as s:
        crawl = s.get(MetaCrawl, crawl_id)
        assert crawl and crawl.status == "done" and crawl.players_done == 3
        assert crawl.battles_added == len(s.exec(select(MetaBattle)).all()) > 0
        # Compare the fixture player's deck against the crawled meta.
        deck = progress.profile_summary(load("player"))["current_deck"]
        cmp = meta.compare_deck(s, deck, mode="all", days=3650)
        assert len(cmp["my_cards"]) == 8


def test_compare_deck_finds_similar_and_swaps(session: Session) -> None:
    from .conftest import DEFAULT_DECK, card

    my = parse_battle(raw_battle(), PLAYER_TAG).deck
    variant = [*DEFAULT_DECK[:7], card(26000038, "Ice Golem")]
    for i in range(3):
        raw = raw_battle(
            i, 1, 0, btype="pathOfLegend", mode="Ranked1v1", opp_tag=f"#V{i}", my_cards=variant
        )
        meta.store_meta_battles(session, f"#TOP{i}", [raw])
    session.commit()
    cmp = meta.compare_deck(session, my, mode="ranked", days=3650)
    assert cmp["similar_decks"][0]["shared"] == 7
    assert cmp["swap_suggestions"][0]["name"] == "Ice Golem"


# -- clans --------------------------------------------------------------------------------------


async def test_clan_overview_merges_river_race(client) -> None:
    out = await clan_overview(client, CLAN_TAG)
    clan = load("clan")
    assert out["name"] == clan["name"] and len(out["members"]) == len(clan["memberList"])
    assert out["river_race"] is not None and len(out["river_race"]["standings"]) == 5
    assert all(m["days_inactive"] is not None for m in out["members"])


async def test_clan_overview_without_race(fake_api, make_client) -> None:
    del fake_api.routes[f"/v1/clans/{CLAN_TAG}/currentriverrace"]
    out = await clan_overview(make_client(fake_api), CLAN_TAG)
    assert out["river_race"] is None
