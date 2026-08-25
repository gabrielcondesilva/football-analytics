import json
from pathlib import Path

from football_analytics.domain.models import Player, Position, Statistic, Team
from football_analytics.ingestion.normalize import (
    find_entry_id,
    parse_squad,
    parse_teams,
    parse_top_stats,
    with_statistics,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fotmob"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_teams_extracts_every_team_from_the_league_table():
    payload = load_fixture("league_table.json")

    teams = parse_teams(payload)

    assert teams == [
        Team(fotmob_id=9825, name="Arsenal"),
        Team(fotmob_id=8456, name="Manchester City"),
        Team(fotmob_id=10260, name="Manchester United"),
    ]


def test_parse_squad_excludes_the_coach_and_keeps_a_single_position_player():
    payload = load_fixture("team_squad.json")
    team = Team(fotmob_id=9825, name="Arsenal")

    players = parse_squad(payload, team)

    assert all(p.name != "Mikel Arteta" for p in players)

    raya = next(p for p in players if p.fotmob_id == 562727)
    assert raya.name == "David Raya"
    assert raya.team == team
    assert raya.positions == (Position(code="GK", group="Goalkeeper"),)
    assert raya.statistics == ()


def test_parse_squad_keeps_every_position_for_a_multi_position_player():
    payload = load_fixture("team_squad.json")
    team = Team(fotmob_id=9825, name="Arsenal")

    players = parse_squad(payload, team)

    mosquera = next(p for p in players if p.fotmob_id == 1298907)
    assert mosquera.positions == (
        Position(code="CB", group="Defender"),
        Position(code="RB", group="Defender"),
    )


def test_parse_squad_gives_an_empty_positions_tuple_when_position_ids_desc_is_blank():
    payload = load_fixture("team_squad.json")
    team = Team(fotmob_id=9825, name="Arsenal")
    payload["squad"]["squad"][1]["members"][0]["positionIdsDesc"] = ""

    players = parse_squad(payload, team)

    raya = next(p for p in players if p.fotmob_id == 562727)
    assert raya.positions == ()


def test_find_entry_id_locates_the_season_and_tournament_requested():
    payload = load_fixture("player_data.json")

    entry_id = find_entry_id(payload, season_name="2025/2026", tournament_id=47)

    assert entry_id == "1-0"


def test_find_entry_id_returns_none_when_the_season_is_not_present():
    payload = load_fixture("player_data.json")

    entry_id = find_entry_id(payload, season_name="1999/2000", tournament_id=47)

    assert entry_id is None


def test_parse_top_stats_extracts_the_raw_value_of_each_top_stat():
    payload = load_fixture("player_stats.json")

    statistics = parse_top_stats(payload)

    assert Statistic(key="goals", label="Goals", value=7.0) in statistics
    assert Statistic(key="assists", label="Assists", value=5.0) in statistics


def test_parse_top_stats_returns_empty_list_when_the_player_has_no_top_stat_card():
    payload = {"statsSection": {"id": "stats-section", "items": []}}

    statistics = parse_top_stats(payload)

    assert statistics == []


def test_parse_top_stats_skips_items_with_a_non_numeric_stat_value():
    payload = {
        "topStatCard": {
            "items": [
                {"localizedTitleId": "goals", "title": "Goals", "statValue": "7"},
                {"localizedTitleId": "rating", "title": "Rating", "statValue": "-"},
            ]
        }
    }

    statistics = parse_top_stats(payload)

    assert statistics == [Statistic(key="goals", label="Goals", value=7.0)]


def test_with_statistics_returns_a_player_carrying_the_given_statistics():
    team = Team(fotmob_id=9825, name="Arsenal")
    player = Player(
        fotmob_id=961995,
        name="Bukayo Saka",
        team=team,
        positions=(Position(code="RW", group="Forward"),),
        statistics=(),
    )
    statistics = [Statistic(key="goals", label="Goals", value=7.0)]

    updated = with_statistics(player, statistics)

    assert updated.statistics == (Statistic(key="goals", label="Goals", value=7.0),)
    assert updated.fotmob_id == player.fotmob_id
    assert updated.positions == player.positions
