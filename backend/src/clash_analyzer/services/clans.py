"""Clan overview: members, activity and live river race participation."""

from datetime import datetime
from typing import Any

from ..clash.client import ClashAPIError, ClashClient
from ..domain.battles import parse_battle_time
from ..models import utcnow

DECKS_PER_WAR_DAY = 4


async def clan_overview(client: ClashClient, tag: str) -> dict[str, Any]:
    clan = await client.clan(tag)
    try:
        race: dict[str, Any] | None = await client.current_river_race(tag)
    except ClashAPIError:
        race = None  # 404 in the gap between seasons, or the clan isn't in a race.

    participants = {p["tag"]: p for p in ((race or {}).get("clan") or {}).get("participants", [])}
    now = utcnow()
    members = []
    for m in clan.get("memberList") or []:
        last_seen: datetime | None = parse_battle_time(m["lastSeen"]) if m.get("lastSeen") else None
        war = participants.get(m["tag"], {})
        members.append(
            {
                "tag": m["tag"],
                "name": m.get("name"),
                "role": m.get("role"),
                "trophies": m.get("trophies"),
                "arena": (m.get("arena") or {}).get("name"),
                "clan_rank": m.get("clanRank"),
                "donations": m.get("donations", 0),
                "donations_received": m.get("donationsReceived", 0),
                "last_seen": last_seen.isoformat() + "Z" if last_seen else None,
                "days_inactive": round((now - last_seen).total_seconds() / 86400, 1)
                if last_seen
                else None,
                "war_fame": war.get("fame", 0),
                "war_decks_used": war.get("decksUsed", 0),
                "war_decks_today": war.get("decksUsedToday", 0),
                "war_boat_attacks": war.get("boatAttacks", 0),
            }
        )

    period = (race or {}).get("periodType")
    standings = sorted(
        (
            {
                "tag": c["tag"],
                "name": c.get("name"),
                "fame": c.get("fame", 0),
                "period_points": c.get("periodPoints", 0),
                "finished": bool(c.get("finishTime")),
                "is_us": c["tag"] == clan["tag"],
            }
            for c in (race or {}).get("clans") or []
        ),
        key=lambda c: -c["fame"],
    )
    return {
        "tag": clan["tag"],
        "name": clan.get("name"),
        "description": clan.get("description"),
        "type": clan.get("type"),
        "clan_score": clan.get("clanScore"),
        "war_trophies": clan.get("clanWarTrophies"),
        "required_trophies": clan.get("requiredTrophies"),
        "donations_per_week": clan.get("donationsPerWeek"),
        "location": (clan.get("location") or {}).get("name"),
        "member_count": clan.get("members"),
        "members": members,
        "river_race": {
            "period_type": period,
            "is_war_day": period in ("warDay", "colosseum"),
            "decks_per_day": DECKS_PER_WAR_DAY,
            "standings": standings,
            "members_missing_decks_today": sum(
                1
                for m in members
                if period in ("warDay", "colosseum") and m["war_decks_today"] < DECKS_PER_WAR_DAY
            ),
        }
        if race
        else None,
    }
