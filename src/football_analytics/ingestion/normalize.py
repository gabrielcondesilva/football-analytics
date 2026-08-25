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
    for season in player_data_payload["statSeasons"]:
        if season["seasonName"] != season_name:
            continue
        for tournament in season["tournaments"]:
            if tournament["tournamentId"] == tournament_id:
                return tournament["entryId"]
    return None


def parse_top_stats(player_stats_payload: dict) -> list[Statistic]:
    statistics = []
    for item in player_stats_payload.get("topStatCard", {}).get("items", []):
        try:
            value = float(item["statValue"])
        except (TypeError, ValueError):
            continue
        statistics.append(Statistic(key=item["localizedTitleId"], label=item["title"], value=value))
    return statistics


def with_statistics(player: Player, statistics: list[Statistic]) -> Player:
    return replace(player, statistics=tuple(statistics))
