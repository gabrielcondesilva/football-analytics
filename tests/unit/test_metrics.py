import pytest

from football_analytics.analysis.metrics import (
    MetricSpec,
    apply_minutes_floor,
    compute_metric,
    filter_by_position_group,
    per_90,
    percentile,
    position_group,
    scout_comparison,
    statistic_value,
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


def test_scout_comparison_excludes_the_reference_player_from_the_results():
    reference = make_player(1, "Reference", "Forward", goals=5.0)
    other = make_player(2, "Other", "Forward", goals=5.0)
    specs = [MetricSpec(key="goals", label="Goals", kind="raw")]

    results = scout_comparison([reference, other], reference, specs)

    assert [p for p, _ in results] == [other]


def test_scout_comparison_ranks_the_closest_match_first():
    reference = make_player(1, "Reference", "Forward", goals=10.0, assists=5.0)
    close = make_player(2, "Close", "Forward", goals=9.0, assists=5.0)
    far = make_player(3, "Far", "Forward", goals=1.0, assists=0.0)
    specs = [
        MetricSpec(key="goals", label="Goals", kind="raw"),
        MetricSpec(key="assists", label="Assists", kind="raw"),
    ]

    results = scout_comparison([reference, close, far], reference, specs)

    assert [p.name for p, _ in results] == ["Close", "Far"]


def test_scout_comparison_restricts_to_the_reference_position_group_by_default():
    reference = make_player(1, "Reference", "Forward", goals=5.0)
    same_group = make_player(2, "SameGroup", "Forward", goals=5.0)
    other_group = make_player(3, "OtherGroup", "Defender", goals=5.0)
    specs = [MetricSpec(key="goals", label="Goals", kind="raw")]

    results = scout_comparison([reference, same_group, other_group], reference, specs)

    assert [p.name for p, _ in results] == ["SameGroup"]


def test_scout_comparison_can_disable_the_position_group_restriction():
    reference = make_player(1, "Reference", "Forward", goals=5.0)
    other_group = make_player(2, "OtherGroup", "Defender", goals=5.0)
    specs = [MetricSpec(key="goals", label="Goals", kind="raw")]

    results = scout_comparison(
        [reference, other_group], reference, specs, restrict_to_position_group=False
    )

    assert [p.name for p, _ in results] == ["OtherGroup"]


def test_scout_comparison_weighs_metrics_equally_regardless_of_scale():
    # "budget" spans millions, "rating" spans single digits. Without z-score
    # normalization, the huge-scale budget difference would swamp the
    # distance calculation. Each candidate matches the reference exactly on
    # one Metric and diverges on the other, in a perfectly symmetric pattern
    # - equal weighting must make both candidates equidistant regardless of
    # which Metric's raw scale is larger.
    reference = make_player(1, "Reference", "Forward", budget=1_000_000.0, rating=100.0)
    similar_budget = make_player(2, "SimilarBudget", "Forward", budget=1_000_000.0, rating=0.0)
    similar_rating = make_player(3, "SimilarRating", "Forward", budget=0.0, rating=100.0)
    specs = [
        MetricSpec(key="budget", label="Budget", kind="raw"),
        MetricSpec(key="rating", label="Rating", kind="raw"),
    ]

    results = scout_comparison([reference, similar_budget, similar_rating], reference, specs)

    distances = {p.name: d for p, d in results}
    assert distances["SimilarBudget"] == pytest.approx(distances["SimilarRating"])


def test_scout_comparison_returns_empty_list_when_no_candidates_remain():
    reference = make_player(1, "Reference", "Forward", goals=5.0)
    specs = [MetricSpec(key="goals", label="Goals", kind="raw")]

    assert scout_comparison([reference], reference, specs) == []
