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


def find_entry_id(player_data_payload: dict | None, *, season_name: str, tournament_id: int) -> str | None:
    if not player_data_payload:
        return None
    for season in player_data_payload["statSeasons"] or []:
        if season["seasonName"] != season_name:
            continue
        for tournament in season["tournaments"] or []:
            if tournament["tournamentId"] == tournament_id:
                return tournament["entryId"]
    return None


def find_known_league_entry(
    player_data_payload: dict | None,
    *,
    season_name: str,
    known_league_tournament_ids: set[int],
) -> tuple[int, str] | None:
    """Fallback for a Player with no Statistics entry in the League being
    ingested (`find_entry_id` returned `None`) — e.g. a recently-transferred
    Player whose Statistics for `season_name` still belong to their old
    League (ADR-0004).

    Among the Player's other competitions for `season_name`, finds the first
    whose `tournamentId` is one of the Leagues already tracked in
    `known_league_tournament_ids` — never a Cup, and never a League this
    project doesn't track yet (that's left to a future spec, see
    `.scratch/cross-league-transfers/spec.md`'s Out of Scope). Returns
    `(tournament_id, entry_id)` for that League, or `None` if none of the
    Player's competitions that Season is a known League.

    Ties (more than one known League matched for the same `season_name` —
    e.g. a genuine mid-season transfer within one Season label) are broken
    by FotMob's own listing order, first match wins: a deterministic but
    imperfect stand-in for a proper Season selector, which doesn't exist
    yet (same Out of Scope note).
    """
    if not player_data_payload:
        return None
    for season in player_data_payload["statSeasons"] or []:
        if season["seasonName"] != season_name:
            continue
        for tournament in season["tournaments"] or []:
            tournament_id = tournament["tournamentId"]
            if tournament_id in known_league_tournament_ids:
                return tournament_id, tournament["entryId"]
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


def parse_touch_coordinates(player_stats_payload: dict | None) -> list[tuple[float, float]]:
    """Raw touch coordinates from a `playerStats` payload's `heatmap` field,
    for the Mapa de Toques (CONTEXT.md) — a Player's own positional
    distribution, distinct from Statistic. Stored as-is and turned into a
    percentage-per-grid-cell view later, at read time (ADR-0005), not here.

    Null-safe like the rest of this module (`find_entry_id`, `with_bio`): a
    missing payload, missing `heatmap`, or missing/null `coordinates` all
    resolve to an empty list rather than raising — FotMob's own payloads are
    inconsistent about which fields a given entry actually has (seen live: a
    fresh transfer's entry can lack a `heatmap` key entirely). A malformed
    individual point (missing `x`/`y`, or a non-numeric value) is skipped
    rather than raising, same convention as `_parse_stat_items` below."""
    if not player_stats_payload:
        return []
    heatmap = player_stats_payload.get("heatmap") or {}
    coordinates = heatmap.get("coordinates") or []
    result: list[tuple[float, float]] = []
    for c in coordinates:
        try:
            result.append((float(c["x"]), float(c["y"])))
        except (KeyError, TypeError, ValueError):
            continue
    return result


def with_statistics(player: Player, statistics: list[Statistic]) -> Player:
    return replace(player, statistics=tuple(statistics))


def photo_url(fotmob_id: int) -> str:
    """FotMob's player photo CDN URL — deterministic from the Player's own
    id (verified live: returns a 200 image/png), so no extra request is
    needed to populate it."""
    return f"https://images.fotmob.com/image_resources/playerimages/{fotmob_id}.png"


def with_bio(player: Player, player_data_payload: dict | None) -> Player:
    """Merge age/nationality/preferred foot (from `playerData`'s
    `playerInformation` list) and the photo URL onto `player`.

    `playerInformation` is a list of `{"title": ..., "value": {...}}` rows
    whose membership varies by Player (FotMob doesn't always have every
    field, e.g. Preferred foot for a fringe squad player) — matched by
    `title` rather than a fixed shape, and a field it doesn't have is simply
    left at Player's own default (None) rather than overwritten. FotMob's
    `playerData` endpoint returns a bare `null` body for some player ids
    (seen live for a Ligue 1 squad member) rather than an empty object, so
    `player_data_payload` itself may be `None` — every field then falls back
    to Player's own default, same as an empty `playerInformation` list.

    `player_data_payload` is the same `playerData` response already fetched
    for `find_entry_id` — no extra request needed.
    """
    info = {
        item.get("title"): item.get("value", {})
        for item in (player_data_payload or {}).get("playerInformation", [])
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
