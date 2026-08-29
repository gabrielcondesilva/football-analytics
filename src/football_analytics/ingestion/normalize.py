"""Seam A: raw FotMob JSON responses -> normalized domain records."""

from __future__ import annotations

from dataclasses import replace

from football_analytics.domain.models import Player, Position, Statistic, Team

_POSITION_GROUP_BY_SQUAD_TITLE = {
    "keepers": "Goalkeeper",
    "defenders": "Defender",
    "midfielders": "Midfielder",
    "attackers": "Forward",
}


def parse_teams(league_table_payload: dict) -> list[Team]:
    rows = league_table_payload["table"][0]["data"]["table"]["all"]
    return [Team(fotmob_id=row["id"], name=row["name"]) for row in rows]


def parse_squad(team_payload: dict, team: Team) -> list[Player]:
    players = []
    for group in team_payload["squad"]["squad"]:
        position_group = _POSITION_GROUP_BY_SQUAD_TITLE.get(group["title"])
        if position_group is None:
            continue
        for member in group["members"]:
            position_ids_desc = member["positionIdsDesc"] or ""
            positions = tuple(
                Position(code=code, group=position_group)
                for code in position_ids_desc.split(",")
                if code
            )
            players.append(
                Player(
                    fotmob_id=member["id"],
                    name=member["name"],
                    team=team,
                    positions=positions,
                    statistics=(),
                )
            )
    return players


def find_entry_id(player_data_payload: dict, *, season_name: str, tournament_id: int) -> str | None:
    for season in player_data_payload["statSeasons"] or []:
        if season["seasonName"] != season_name:
            continue
        for tournament in season["tournaments"] or []:
            if tournament["tournamentId"] == tournament_id:
                return tournament["entryId"]
    return None


def parse_top_stats(player_stats_payload: dict) -> list[Statistic]:
    return _parse_stat_items(player_stats_payload.get("topStatCard", {}).get("items", []))


def parse_category_stats(player_stats_payload: dict) -> list[Statistic]:
    """Normalize every Statistic category FotMob returns for a Player's profile.

    Covers both outfield categories (e.g. Shooting, Passing, Possession,
    Defending) and the goalkeeper-specific ones (Goalkeeping, Distribution):
    FotMob returns whichever set applies to the Player under the same
    `statsSection.items` shape, so no goalkeeper-specific branching is needed
    here.
    """
    statistics = []
    for category in player_stats_payload.get("statsSection", {}).get("items", []):
        statistics.extend(_parse_stat_items(category.get("items", [])))
    return statistics


def parse_all_stats(player_stats_payload: dict) -> list[Statistic]:
    """All Statistics for a Player's profile: Top Stats plus every category.

    A handful of keys (e.g. "goals") are surfaced in both topStatCard and a
    category with the same value, so duplicates are collapsed, keeping the
    first (Top Stats) occurrence.
    """
    by_key: dict[str, Statistic] = {}
    for stat in [*parse_top_stats(player_stats_payload), *parse_category_stats(player_stats_payload)]:
        by_key.setdefault(stat.key, stat)
    return list(by_key.values())


def _parse_stat_items(items: list[dict]) -> list[Statistic]:
    statistics = []
    for item in items:
        try:
            value = float(item["statValue"])
        except (TypeError, ValueError):
            continue
        stat_format = item.get("statFormat") or "number"
        statistics.append(
            Statistic(key=item["localizedTitleId"], label=item["title"], value=value, format=stat_format)
        )
    return statistics


def with_statistics(player: Player, statistics: list[Statistic]) -> Player:
    return replace(player, statistics=tuple(statistics))


def photo_url(fotmob_id: int) -> str:
    """FotMob's player photo CDN URL — deterministic from the Player's own
    id (verified live: returns a 200 image/png), so no extra request is
    needed to populate it."""
    return f"https://images.fotmob.com/image_resources/playerimages/{fotmob_id}.png"


def with_bio(player: Player, player_data_payload: dict) -> Player:
    """Merge age/nationality/preferred foot (from `playerData`'s
    `playerInformation` list) and the photo URL onto `player`.

    `playerInformation` is a list of `{"title": ..., "value": {...}}` rows
    whose membership varies by Player (FotMob doesn't always have every
    field, e.g. Preferred foot for a fringe squad player) — matched by
    `title` rather than a fixed shape, and a field it doesn't have is simply
    left at Player's own default (None) rather than overwritten.

    `player_data_payload` is the same `playerData` response already fetched
    for `find_entry_id` — no extra request needed.
    """
    info = {
        item.get("title"): item.get("value", {})
        for item in player_data_payload.get("playerInformation", [])
    }
    updates: dict = {"photo_url": photo_url(player.fotmob_id)}
    age = info.get("Age", {}).get("numberValue")
    if age is not None:
        updates["age"] = int(age)
    foot = info.get("Preferred foot", {}).get("fallback")
    if foot:
        updates["preferred_foot"] = foot
    country = info.get("Country", {}).get("fallback")
    if country:
        updates["nationality"] = country
    return replace(player, **updates)
