from football_analytics.domain.models import Player, Position, Statistic, Team

TEAM = Team(fotmob_id=1, name="Test United")
POSITIONS = (Position(code="CM", group="Midfielder"),)
STATISTICS: tuple[Statistic, ...] = ()


def test_player_biographical_fields_default_to_none():
    player = Player(
        fotmob_id=1, name="A", team=TEAM, positions=POSITIONS, statistics=STATISTICS
    )

    assert player.age is None
    assert player.nationality is None
    assert player.preferred_foot is None
    assert player.photo_url is None


def test_player_accepts_biographical_fields_when_provided():
    player = Player(
        fotmob_id=1,
        name="A",
        team=TEAM,
        positions=POSITIONS,
        statistics=STATISTICS,
        age=27,
        nationality="Brazil",
        preferred_foot="Right",
        photo_url="https://example.com/photo.png",
    )

    assert player.age == 27
    assert player.nationality == "Brazil"
    assert player.preferred_foot == "Right"
    assert player.photo_url == "https://example.com/photo.png"
