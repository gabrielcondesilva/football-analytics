from football_analytics.analysis.metrics import (
    MetricSpec,
    apply_minutes_floor,
    compute_metric,
    filter_by_position_group,
    filter_by_shared_position,
    per_90,
    percentile,
    position_group,
    statistic_value,
    tercile_band,
    top_metric_leaderboard,
)
from football_analytics.domain.models import Player, Position, Statistic, Team

TEAM = Team(fotmob_id=1, name="Test United")


def make_player(fotmob_id: int, name: str, group: str, **stats: float) -> Player:
    statistics = tuple(Statistic(key=key, label=key, value=value) for key, value in stats.items())
    positions = (Position(code="X", group=group),) if group else ()
    return Player(
        fotmob_id=fotmob_id, name=name, team=TEAM, positions=positions, statistics=statistics
    )


def test_statistic_value_returns_none_when_the_player_has_no_such_statistic():
    player = make_player(1, "A", "Forward", goals=5.0)

    assert statistic_value(player, "assists") is None


def test_position_group_returns_none_when_the_player_has_no_positions():
    player = make_player(1, "A", group=None)

    assert position_group(player) is None


def test_filter_by_position_group_keeps_only_matching_players():
    forward = make_player(1, "Forward Player", "Forward")
    defender = make_player(2, "Defender Player", "Defender")

    filtered = filter_by_position_group([forward, defender], "Forward")

    assert filtered == [forward]


def test_filter_by_shared_position_keeps_players_with_any_matching_code():
    def make_positioned_player(fotmob_id: int, name: str, *codes: str) -> Player:
        positions = tuple(Position(code=code, group="Midfielder") for code in codes)
        return Player(fotmob_id=fotmob_id, name=name, team=TEAM, positions=positions, statistics=())

    target = make_positioned_player(1, "Target", "CAM", "CDM")
    shares_cam = make_positioned_player(2, "SharesCAM", "CAM")
    shares_cdm = make_positioned_player(3, "SharesCDM", "CDM", "CM")
    no_overlap = make_positioned_player(4, "NoOverlap", "ST")

    filtered = filter_by_shared_position([target, shares_cam, shares_cdm, no_overlap], target)

    assert filtered == [target, shares_cam, shares_cdm]


def test_apply_minutes_floor_excludes_players_below_the_floor():
    below = make_player(1, "Below", "Forward", minutes_played=500.0)
    above = make_player(2, "Above", "Forward", minutes_played=1000.0)

    filtered = apply_minutes_floor([below, above], minutes_floor=900.0)

    assert filtered == [above]


def test_apply_minutes_floor_excludes_players_with_no_minutes_statistic():
    no_minutes = make_player(1, "NoMinutes", "Forward")

    filtered = apply_minutes_floor([no_minutes], minutes_floor=1.0)

    assert filtered == []


def test_per_90_scales_the_statistic_by_minutes_played():
    player = make_player(1, "A", "Forward", goals=9.0, minutes_played=900.0)

    assert per_90(player, "goals") == 0.9


def test_per_90_returns_none_when_minutes_played_is_missing():
    player = make_player(1, "A", "Forward", goals=9.0)

    assert per_90(player, "goals") is None


def test_per_90_returns_none_when_minutes_played_is_zero():
    player = make_player(1, "A", "Forward", goals=9.0, minutes_played=0.0)

    assert per_90(player, "goals") is None


def test_per_90_returns_the_raw_value_for_a_percentage_statistic_without_dividing():
    save_percentage = Statistic(
        key="save_percentage", label="Save percentage", value=64.8, format="percent"
    )
    minutes = Statistic(key="minutes_played", label="Minutes", value=900.0, format="number")
    player = Player(
        fotmob_id=1,
        name="Goalkeeper",
        team=TEAM,
        positions=(Position(code="GK", group="Goalkeeper"),),
        statistics=(save_percentage, minutes),
    )

    assert per_90(player, "save_percentage") == 64.8


def test_per_90_returns_the_raw_percentage_even_without_minutes_played():
    save_percentage = Statistic(
        key="save_percentage", label="Save percentage", value=64.8, format="percent"
    )
    player = Player(
        fotmob_id=1,
        name="Goalkeeper",
        team=TEAM,
        positions=(Position(code="GK", group="Goalkeeper"),),
        statistics=(save_percentage,),
    )

    assert per_90(player, "save_percentage") == 64.8


def test_percentile_ranks_the_player_against_the_given_peers():
    low = make_player(1, "Low", "Forward", goals=1.0)
    mid = make_player(2, "Mid", "Forward", goals=5.0)
    high = make_player(3, "High", "Forward", goals=10.0)

    assert percentile([low, mid, high], mid, "goals") == 100 * 2 / 3


def test_percentile_returns_none_when_the_player_lacks_the_statistic():
    peer = make_player(1, "Peer", "Forward", goals=5.0)
    target = make_player(2, "Target", "Forward")

    assert percentile([peer, target], target, "goals") is None


def test_percentile_ignores_peers_missing_the_statistic():
    peer_without_stat = make_player(1, "PeerWithout", "Forward")
    peer_with_stat = make_player(2, "PeerWith", "Forward", goals=3.0)
    target = make_player(3, "Target", "Forward", goals=5.0)

    assert percentile([peer_without_stat, peer_with_stat, target], target, "goals") == 100.0


def test_compute_metric_dispatches_to_raw():
    player = make_player(1, "A", "Forward", goals=5.0)
    spec = MetricSpec(key="goals", label="Goals", kind="raw")

    assert compute_metric([player], player, spec) == 5.0


def test_compute_metric_dispatches_to_per_90():
    player = make_player(1, "A", "Forward", goals=9.0, minutes_played=900.0)
    spec = MetricSpec(key="goals", label="Goals per 90", kind="per_90")

    assert compute_metric([player], player, spec) == 0.9


def test_compute_metric_dispatches_to_percentile():
    low = make_player(1, "Low", "Forward", goals=1.0)
    high = make_player(2, "High", "Forward", goals=10.0)
    spec = MetricSpec(key="goals", label="Goals percentile", kind="percentile")

    assert compute_metric([low, high], high, spec) == 100.0


def test_tercile_band_returns_bottom_at_the_lowest_percentile():
    assert tercile_band(0.0) == "bottom"


def test_tercile_band_returns_bottom_just_below_the_first_boundary():
    assert tercile_band(32.9) == "bottom"


def test_tercile_band_returns_middle_at_the_first_boundary():
    assert tercile_band(33.0) == "middle"


def test_tercile_band_returns_middle_between_the_boundaries():
    assert tercile_band(50.0) == "middle"


def test_tercile_band_returns_middle_just_below_the_second_boundary():
    assert tercile_band(66.9) == "middle"


def test_tercile_band_returns_top_at_the_second_boundary():
    assert tercile_band(67.0) == "top"


def test_tercile_band_returns_top_at_the_highest_percentile():
    assert tercile_band(100.0) == "top"


def test_top_metric_leaderboard_ranks_players_by_per_90_value_descending_by_default():
    low = make_player(1, "Low", "Forward", goals=1.0, minutes_played=900.0)
    high = make_player(2, "High", "Forward", goals=9.0, minutes_played=900.0)
    mid = make_player(3, "Mid", "Forward", goals=4.5, minutes_played=900.0)

    leaderboard = top_metric_leaderboard([low, high, mid], "goals")

    assert [entry[0].name for entry in leaderboard] == ["High", "Mid", "Low"]


def test_top_metric_leaderboard_ranks_by_the_per_90_value_not_the_raw_value():
    # Raw goals: MoreRaw (10) > FewerRaw (8). Per-90: FewerRaw (3.6) > MoreRaw (1.0),
    # since FewerRaw played far fewer minutes for those goals. The leaderboard must
    # follow the per-90 ranking (what it displays), not the raw one.
    more_raw = make_player(1, "MoreRaw", "Forward", goals=10.0, minutes_played=900.0)
    fewer_raw = make_player(2, "FewerRaw", "Forward", goals=8.0, minutes_played=200.0)

    leaderboard = top_metric_leaderboard([more_raw, fewer_raw], "goals")

    assert [entry[0].name for entry in leaderboard] == ["FewerRaw", "MoreRaw"]


def test_top_metric_leaderboard_ranks_by_the_raw_value_when_kind_is_raw():
    more_raw = make_player(1, "MoreRaw", "Forward", goals=10.0, minutes_played=900.0)
    fewer_raw = make_player(2, "FewerRaw", "Forward", goals=8.0, minutes_played=200.0)

    leaderboard = top_metric_leaderboard([more_raw, fewer_raw], "goals", kind="raw")

    assert leaderboard == [(more_raw, 10.0), (fewer_raw, 8.0)]


def test_top_metric_leaderboard_returns_the_raw_value_for_a_percent_statistic():
    stat = Statistic(key="save_percentage", label="Save %", value=64.8, format="percent")
    minutes = Statistic(key="minutes_played", label="Minutes", value=900.0, format="number")
    player = Player(
        fotmob_id=1,
        name="Goalkeeper",
        team=TEAM,
        positions=(Position(code="GK", group="Goalkeeper"),),
        statistics=(stat, minutes),
    )

    leaderboard = top_metric_leaderboard([player], "save_percentage")

    assert leaderboard == [(player, 64.8)]


def test_top_metric_leaderboard_limits_results_to_the_requested_size():
    players = [
        make_player(i, f"Player{i}", "Forward", goals=float(i), minutes_played=900.0)
        for i in range(1, 6)
    ]

    leaderboard = top_metric_leaderboard(players, "goals", size=2)

    assert [entry[0].name for entry in leaderboard] == ["Player5", "Player4"]


def test_top_metric_leaderboard_returns_fewer_than_size_when_fewer_players_qualify():
    players = [
        make_player(i, f"Player{i}", "Forward", goals=float(i), minutes_played=900.0)
        for i in range(1, 4)
    ]

    leaderboard = top_metric_leaderboard(players, "goals", size=10)

    assert len(leaderboard) == 3


def test_top_metric_leaderboard_excludes_players_the_metric_cannot_be_computed_for():
    no_minutes = make_player(1, "NoMinutes", "Forward", goals=5.0)
    qualifies = make_player(2, "Qualifies", "Forward", goals=5.0, minutes_played=900.0)

    leaderboard = top_metric_leaderboard([no_minutes, qualifies], "goals")

    assert [entry[0].name for entry in leaderboard] == ["Qualifies"]


def test_top_metric_leaderboard_returns_empty_list_when_no_players_qualify():
    no_minutes = make_player(1, "NoMinutes", "Forward", goals=5.0)

    assert top_metric_leaderboard([no_minutes], "goals") == []
