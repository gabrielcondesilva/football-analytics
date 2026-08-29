import json
from pathlib import Path

from football_analytics.domain.models import Player, Position, Statistic, Team
from football_analytics.ingestion.normalize import (
    find_entry_id,
    find_known_league_entry,
    parse_all_stats,
    parse_category_stats,
    parse_squad,
    parse_teams,
    parse_top_stats,
    photo_url,
    with_bio,
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


def test_parse_squad_gives_an_empty_positions_tuple_when_position_ids_desc_is_null():
    payload = load_fixture("team_squad.json")
    team = Team(fotmob_id=9825, name="Arsenal")
    payload["squad"]["squad"][1]["members"][0]["positionIdsDesc"] = None

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


def test_find_entry_id_returns_none_when_stat_seasons_is_null():
    payload = load_fixture("player_data.json")
    payload["statSeasons"] = None

    entry_id = find_entry_id(payload, season_name="2025/2026", tournament_id=47)

    assert entry_id is None


def test_find_entry_id_returns_none_when_tournaments_is_null_for_the_matched_season():
    payload = load_fixture("player_data.json")
    payload["statSeasons"][1]["tournaments"] = None

    entry_id = find_entry_id(payload, season_name="2025/2026", tournament_id=47)

    assert entry_id is None


def test_find_entry_id_returns_none_when_the_whole_payload_is_null():
    """FotMob's `playerData` endpoint returns a bare `null` body for some
    player ids (seen live for a Ligue 1 squad member) rather than an empty
    object."""
    entry_id = find_entry_id(None, season_name="2025/2026", tournament_id=47)

    assert entry_id is None


def test_find_known_league_entry_finds_the_tournament_matching_a_known_league():
    """Bukayo Saka's 2025/2026 Season has six competitions (Premier League,
    Community Shield, FA Cup, EFL Cup, Champions League, World Cup UEFA
    qualification) — only tournamentId 47 (Premier League) is a League we
    track."""
    payload = load_fixture("player_data.json")

    result = find_known_league_entry(
        payload, season_name="2025/2026", known_league_tournament_ids={47, 87, 53}
    )

    assert result == (47, "1-0")


def test_find_known_league_entry_returns_none_when_no_competition_is_a_known_league():
    """Same Season, but the caller only tracks Leagues Saka didn't play in
    that Season (e.g. a Player transferred from a League we've never
    ingested) — every one of his competitions that Season is a Cup/
    qualifier we don't track as a League, so there's no fallback to use."""
    payload = load_fixture("player_data.json")

    result = find_known_league_entry(
        payload, season_name="2025/2026", known_league_tournament_ids={87, 53}
    )

    assert result is None


def test_find_known_league_entry_breaks_ties_by_fotmob_listing_order():
    """The rare case of two known-League entries in the same season_name
    (e.g. a mid-season transfer within one Season label, not yet
    disambiguated by a Season selector — see the spec's Out of Scope):
    picks whichever comes first in FotMob's own listing, not the lowest
    tournamentId or any other ordering."""
    payload = load_fixture("player_data.json")
    season_2025_26 = next(s for s in payload["statSeasons"] if s["seasonName"] == "2025/2026")
    season_2025_26["tournaments"].insert(
        0, {"name": "La Liga", "tournamentId": 87, "entryId": "9-9", "hasDeepStats": True}
    )

    result = find_known_league_entry(
        payload, season_name="2025/2026", known_league_tournament_ids={47, 87}
    )

    assert result == (87, "9-9")


def test_find_known_league_entry_returns_none_when_the_season_is_not_present():
    payload = load_fixture("player_data.json")

    result = find_known_league_entry(
        payload, season_name="1999/2000", known_league_tournament_ids={47, 87, 53}
    )

    assert result is None


def test_find_known_league_entry_returns_none_when_stat_seasons_is_null():
    payload = load_fixture("player_data.json")
    payload["statSeasons"] = None

    result = find_known_league_entry(
        payload, season_name="2025/2026", known_league_tournament_ids={47, 87, 53}
    )

    assert result is None


def test_find_known_league_entry_returns_none_when_tournaments_is_null_for_the_matched_season():
    payload = load_fixture("player_data.json")
    payload["statSeasons"][1]["tournaments"] = None

    result = find_known_league_entry(
        payload, season_name="2025/2026", known_league_tournament_ids={47, 87, 53}
    )

    assert result is None


def test_find_known_league_entry_returns_none_when_the_whole_payload_is_null():
    result = find_known_league_entry(
        None, season_name="2025/2026", known_league_tournament_ids={47, 87, 53}
    )

    assert result is None


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


def test_parse_category_stats_extracts_stats_from_every_outfield_category():
    payload = load_fixture("player_stats.json")

    statistics = parse_category_stats(payload)

    assert Statistic(key="shots", label="Shots", value=71.0) in statistics
    assert Statistic(key="chances_created", label="Chances created", value=53.0) in statistics
    assert Statistic(key="dribbles_succeeded", label="Dribbles", value=27.0) in statistics
    assert Statistic(key="interceptions", label="Interceptions", value=20.0) in statistics
    assert Statistic(key="yellow_cards", label="Yellow cards", value=3.0) in statistics


def test_parse_category_stats_extracts_stats_from_the_goalkeeper_specific_categories():
    payload = load_fixture("goalkeeper_player_stats.json")

    statistics = parse_category_stats(payload)

    assert Statistic(key="saves", label="Saves", value=57.0, format="number") in statistics
    assert (
        Statistic(key="save_percentage", label="Save percentage", value=64.8, format="percent")
        in statistics
    )
    assert (
        Statistic(key="goals_prevented", label="Goals prevented", value=-2.70, format="fraction")
        in statistics
    )
    assert (
        Statistic(key="successful_passes", label="Accurate passes", value=644.0, format="number")
        in statistics
    )


def test_parse_stat_items_captures_the_format_of_each_statistic():
    payload = load_fixture("goalkeeper_player_stats.json")

    statistics = parse_category_stats(payload)

    save_percentage = next(s for s in statistics if s.key == "save_percentage")
    saves = next(s for s in statistics if s.key == "saves")
    assert save_percentage.format == "percent"
    assert saves.format == "number"


def test_parse_stat_items_defaults_the_format_to_number_when_stat_format_is_missing():
    payload = {
        "topStatCard": {
            "items": [{"localizedTitleId": "goals", "title": "Goals", "statValue": "7"}]
        }
    }

    statistics = parse_top_stats(payload)

    assert statistics == [Statistic(key="goals", label="Goals", value=7.0, format="number")]


def test_parse_category_stats_skips_items_with_a_non_numeric_stat_value():
    payload = load_fixture("goalkeeper_player_stats.json")

    statistics = parse_category_stats(payload)

    assert all(s.key != "saved_penalties" for s in statistics)


def test_parse_category_stats_returns_empty_list_when_there_is_no_stats_section():
    statistics = parse_category_stats({})

    assert statistics == []


def test_parse_all_stats_combines_top_stats_and_every_category_for_an_outfield_player():
    payload = load_fixture("player_stats.json")

    statistics = parse_all_stats(payload)

    keys = {s.key for s in statistics}
    assert "rating" in keys  # from topStatCard
    assert "shots" in keys  # from the shooting category
    assert "chances_created" in keys  # from the passing category
    assert "interceptions" in keys  # from the defending category


def test_parse_all_stats_deduplicates_keys_shared_by_top_stats_and_a_category():
    payload = load_fixture("player_stats.json")

    statistics = parse_all_stats(payload)

    assert [s for s in statistics if s.key == "goals"] == [Statistic(key="goals", label="Goals", value=7.0)]


def test_parse_all_stats_covers_the_goalkeeper_specific_categories():
    payload = load_fixture("goalkeeper_player_stats.json")

    statistics = parse_all_stats(payload)

    keys = {s.key for s in statistics}
    assert "saves" in keys
    assert "save_percentage" in keys
    assert "successful_passes" in keys  # from the distribution category


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


def test_photo_url_is_deterministic_from_the_fotmob_id():
    assert photo_url(961995) == "https://images.fotmob.com/image_resources/playerimages/961995.png"


def test_with_bio_merges_age_nationality_preferred_foot_and_photo_url():
    payload = load_fixture("player_data.json")
    team = Team(fotmob_id=9825, name="Arsenal")
    player = Player(
        fotmob_id=961995,
        name="Bukayo Saka",
        team=team,
        positions=(Position(code="RW", group="Forward"),),
        statistics=(),
    )

    updated = with_bio(player, payload)

    assert updated.age == 24
    assert updated.nationality == "England"
    assert updated.preferred_foot == "Left"
    assert updated.photo_url == "https://images.fotmob.com/image_resources/playerimages/961995.png"
    assert updated.fotmob_id == player.fotmob_id


def test_with_bio_leaves_a_missing_field_at_its_default():
    payload = {"playerInformation": [{"title": "Age", "value": {"numberValue": 24}}]}
    team = Team(fotmob_id=9825, name="Arsenal")
    player = Player(
        fotmob_id=961995,
        name="Bukayo Saka",
        team=team,
        positions=(),
        statistics=(),
    )

    updated = with_bio(player, payload)

    assert updated.age == 24
    assert updated.nationality is None
    assert updated.preferred_foot is None


def test_with_bio_handles_a_missing_player_information_section():
    team = Team(fotmob_id=9825, name="Arsenal")
    player = Player(
        fotmob_id=961995, name="Bukayo Saka", team=team, positions=(), statistics=()
    )

    updated = with_bio(player, {})

    assert updated.age is None
    assert updated.nationality is None
    assert updated.preferred_foot is None
    assert updated.photo_url == "https://images.fotmob.com/image_resources/playerimages/961995.png"


def test_with_bio_handles_a_null_payload():
    """FotMob's `playerData` endpoint returns a bare `null` body for some
    player ids (seen live for a Ligue 1 squad member) rather than an empty
    object — `photo_url` is still deterministic from the Player's own id, so
    it's populated even though every other bio field stays at its default."""
    team = Team(fotmob_id=9825, name="Arsenal")
    player = Player(
        fotmob_id=961995, name="Bukayo Saka", team=team, positions=(), statistics=()
    )

    updated = with_bio(player, None)

    assert updated.age is None
    assert updated.nationality is None
    assert updated.preferred_foot is None
    assert updated.photo_url == "https://images.fotmob.com/image_resources/playerimages/961995.png"
