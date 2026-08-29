"""Pure UI-helper functions shared by more than one dashboard page."""

from __future__ import annotations

from football_analytics.domain.models import Player

# Portuguese display label per Statistic `key` (FotMob's localizedTitleId),
# keyed by key rather than FotMob's own English `label` so the translation
# holds regardless of which raw label FotMob attaches. A key missing here
# (a FotMob stat not yet catalogued) falls back to its raw English label in
# `metric_label_options` rather than breaking.
METRIC_LABEL_PT: dict[str, str] = {
    "ShotsOnTarget": "Finalizações no Alvo",
    "aerials_won": "Duelos Aéreos Vencidos",
    "aerials_won_percent": "Duelos Aéreos Vencidos (%)",
    "assists": "Assistências",
    "big_chance_created_team_title": "Grandes Chances Criadas",
    "blocked_shots": "Finalizações Bloqueadas",
    "chances_created": "Chances Criadas",
    "clean_sheet_team_title": "Jogos sem Sofrer Gols",
    "clean_sheet_title": "Jogos sem Sofrer Gols",
    "clearances": "Cortes",
    "crosses_succeeeded": "Cruzamentos Certos",
    "crosses_succeeeded_accuracy": "Precisão de Cruzamento",
    "defensive_actions": "Ações Defensivas",
    "dispossessed": "Perdas de Posse",
    "dribbled_past": "Driblado",
    "dribbles_succeeded": "Dribles Certos",
    "duel_won": "Duelos Vencidos",
    "duel_won_percent": "Duelos Vencidos (%)",
    "error_led_to_goal": "Erros que Geraram Gol",
    "expected_assists": "Assistências Esperadas (xA)",
    "expected_goals": "Gols Esperados (xG)",
    "expected_goals_against_while_on_pitch": "xG Sofrido em Campo",
    "expected_goals_on_target": "xG no Alvo (xGOT)",
    "fouls": "Faltas Cometidas",
    "fouls_won": "Faltas Sofridas",
    "goals": "Gols",
    "goals_conceded": "Gols Sofridos",
    "goals_conceded_while_on_pitch": "Gols Sofridos em Campo",
    "goals_prevented": "Gols Evitados",
    "goals_subtitle": "Gols de Pênalti",
    "headed_shots": "Finalizações de Cabeça",
    "interceptions": "Interceptações",
    "keeper_high_claim": "Saídas do Gol",
    "keeper_sweeper": "Atuação como Líbero",
    "line_breaking_passes": "Passes que Rompem Linhas",
    "long_ball_succeeeded_accuracy": "Precisão de Lançamento",
    "long_balls_accurate": "Lançamentos Certos",
    "matches_uppercase": "Partidas",
    "matchstats.headers.tackles": "Desarmes",
    "minutes_played": "Minutos Jogados",
    "non_penalty_xg": "xG sem Pênalti",
    "penalty_conceded_title": "Pênaltis Cometidos",
    "penalty_goals_conceded": "Gols de Pênalti Sofridos",
    "penalty_save_percent": "Percentual de Pênaltis Defendidos",
    "penalty_saves": "Pênaltis Defendidos",
    "penalty_won_title": "Pênaltis Sofridos",
    "physical_metrics_distance_covered": "Distância Percorrida",
    "physical_metrics_number_of_sprints": "Número de Sprints",
    "physical_metrics_running": "Corrida",
    "physical_metrics_sprinting": "Sprints (Distância)",
    "physical_metrics_topspeed": "Velocidade Máxima",
    "player_started_matches": "Jogos como Titular",
    "poss_won_att_3rd_team_title": "Posse Recuperada no Terço Final",
    "rating": "Nota",
    "recoveries": "Recuperações de Bola",
    "red_cards": "Cartões Vermelhos",
    "save_percentage": "Percentual de Defesas",
    "saved_penalties": "Pênaltis Defendidos",
    "saves": "Defesas",
    "shots": "Finalizações",
    "successful_passes": "Passes Certos",
    "successful_passes_accuracy": "Precisão de Passe",
    "touches": "Toques na Bola",
    "touches_opp_box": "Toques na Área Adversária",
    "won_contest_subtitle": "Taxa de Sucesso em Dribles",
    "yellow_cards": "Cartões Amarelos",
}


def metric_label_options(players: list[Player]) -> dict[str, str]:
    """Map each available Statistic's Portuguese display label to its key,
    first label wins. Falls back to FotMob's raw English label for a `key`
    not in `METRIC_LABEL_PT`."""
    options: dict[str, str] = {}
    for p in players:
        for s in p.statistics:
            options.setdefault(METRIC_LABEL_PT.get(s.key, s.label), s.key)
    return options


def position_codes(player: Player) -> str:
    """Comma-separated Position codes for display (e.g. "CB, RB")."""
    return ", ".join(pos.code for pos in player.positions)


# Portuguese display label per `Player.preferred_foot` raw value (FotMob's
# "Preferred foot" playerInformation entry).
PREFERRED_FOOT_PT: dict[str, str] = {
    "Right": "Direito",
    "Left": "Esquerdo",
    "Both": "Ambidestro",
}


def preferred_foot_label(preferred_foot: str | None) -> str | None:
    """Portuguese label for a Player's preferred foot. Falls back to the raw
    value for one not in `PREFERRED_FOOT_PT`; `None` stays `None`."""
    if preferred_foot is None:
        return None
    return PREFERRED_FOOT_PT.get(preferred_foot, preferred_foot)


# Portuguese display label per `Player.nationality` raw value (FotMob's
# "Country" playerInformation entry) — every country seen across the
# Premier League and La Liga 2025/2026 rosters. A country not in this dict
# (a future League adds one we haven't catalogued) falls back to its raw
# English name in `nationality_label` rather than breaking.
NATIONALITY_PT: dict[str, str] = {
    "Albania": "Albânia",
    "Algeria": "Argélia",
    "Angola": "Angola",
    "Argentina": "Argentina",
    "Australia": "Austrália",
    "Austria": "Áustria",
    "Belgium": "Bélgica",
    "Brazil": "Brasil",
    "Bulgaria": "Bulgária",
    "Burkina Faso": "Burquina Faso",
    "Cameroon": "Camarões",
    "Canada": "Canadá",
    "Cape Verde": "Cabo Verde",
    "Chile": "Chile",
    "Colombia": "Colômbia",
    "Croatia": "Croácia",
    "Czechia": "Tchéquia",
    "DR Congo": "RD Congo",
    "Denmark": "Dinamarca",
    "Dominican Republic": "República Dominicana",
    "Ecuador": "Equador",
    "Egypt": "Egito",
    "England": "Inglaterra",
    "Finland": "Finlândia",
    "France": "França",
    "Georgia": "Geórgia",
    "Germany": "Alemanha",
    "Ghana": "Gana",
    "Greece": "Grécia",
    "Guadeloupe": "Guadalupe",
    "Guinea": "Guiné",
    "Guinea-Bissau": "Guiné-Bissau",
    "Haiti": "Haiti",
    "Hungary": "Hungria",
    "Iceland": "Islândia",
    "Ireland": "Irlanda",
    "Israel": "Israel",
    "Italy": "Itália",
    "Ivory Coast": "Costa do Marfim",
    "Jamaica": "Jamaica",
    "Japan": "Japão",
    "Malaysia": "Malásia",
    "Mauritania": "Mauritânia",
    "Mexico": "México",
    "Morocco": "Marrocos",
    "Mozambique": "Moçambique",
    "Netherlands": "Holanda",
    "New Zealand": "Nova Zelândia",
    "Nigeria": "Nigéria",
    "North Macedonia": "Macedônia do Norte",
    "Northern Ireland": "Irlanda do Norte",
    "Norway": "Noruega",
    "Paraguay": "Paraguai",
    "Peru": "Peru",
    "Poland": "Polônia",
    "Portugal": "Portugal",
    "Romania": "Romênia",
    "Russia": "Rússia",
    "Scotland": "Escócia",
    "Senegal": "Senegal",
    "Serbia": "Sérvia",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovênia",
    "South Africa": "África do Sul",
    "South Korea": "Coreia do Sul",
    "Spain": "Espanha",
    "Suriname": "Suriname",
    "Sweden": "Suécia",
    "Switzerland": "Suíça",
    "The Gambia": "Gâmbia",
    "Togo": "Togo",
    "Tunisia": "Tunísia",
    "Turkiye": "Turquia",
    "USA": "Estados Unidos",
    "Ukraine": "Ucrânia",
    "Uruguay": "Uruguai",
    "Uzbekistan": "Uzbequistão",
    "Venezuela": "Venezuela",
    "Wales": "País de Gales",
    "Zimbabwe": "Zimbábue",
}


def nationality_label(nationality: str | None) -> str | None:
    """Portuguese label for a Player's nationality. Falls back to the raw
    value for a country not in `NATIONALITY_PT`; `None` stays `None`."""
    if nationality is None:
        return None
    return NATIONALITY_PT.get(nationality, nationality)
