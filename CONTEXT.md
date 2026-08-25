# Football Analytics

Base de dados e dashboard de estatísticas de futebol: scraping de dados do FotMob, análise comparativa de jogadores e times, e geração de scouting reports para treinadores.

## Language

### Escopo de dados

**League**:
Uma competição (ex: Premier League) que agrupa Seasons.
_Avoid_: Competition, campeonato.

**Season**:
Uma edição específica de uma League, delimitada no tempo (ex: 2025/26). Escopa todas as Statistics e Metrics de um Player.
_Avoid_: Year, campanha, temporada (em código).

**Team**:
Entidade de referência mínima (nome, escudo) à qual um Player pertence. Não carrega estatísticas próprias nesta fase do projeto — isso é escopo de uma fase futura.
_Avoid_: Club, Squad.

**Player**:
Um jogador individual com Statistics e Metrics agregadas por Season. É a unidade central de comparação e scouting do projeto.
_Avoid_: Athlete, atleta.

**Position**:
Um papel que um Player pode ocupar em campo (ex: zagueiro, lateral). Um Player pode ter múltiplas Positions.
_Avoid_: Role.

**Position Group**:
Classificação mais ampla de Positions (ex: defensores, meio-campistas, atacantes), usada para restringir Scout Comparisons a jogadores comparáveis por padrão.

### Estatísticas e métricas

**Statistic**:
Um valor bruto coletado do FotMob para um Player em uma Season (ex: total de gols, passes certos).
_Avoid_: Metric, stat, número.

**Metric**:
Qualquer valor usado para comparação ou visualização — pode ser uma Statistic bruta ou um valor derivado dela (por-90, percentil, z-score). É o que o usuário escolhe na sidebar do dashboard.
_Avoid_: Stat, KPI.

**Snapshot**:
Uma captura datada das Statistics de um Player, feita em um momento do scraping. Permite múltiplos Snapshots por Player-Season ao longo do tempo, mesmo que hoje só exista um scraping único por Season.
_Avoid_: Version, scrape, coleta.

**Minutes Floor**:
O piso mínimo de minutos jogados que um Player precisa atingir para entrar em comparações e rankings, evitando distorção por amostra pequena. Ajustável pelo usuário.

### Scouting e saída

**Scout Comparison**:
Um ranking de Players similares a um Player de referência, calculado a partir de um conjunto de Metrics escolhidas pelo usuário (peso igual entre elas), restrito por padrão ao mesmo Position Group e filtrado pelo Minutes Floor.
_Avoid_: Scout Report, replacement search, busca de substituto.

**Insight**:
Uma observação gerada automaticamente sobre as Metrics de um Player em relação aos percentis da League (baseada em regras, não gerada por LLM).
_Avoid_: Recommendation, recomendação.

**Report**:
Um documento em PDF exportável, contendo o perfil de um único Player ou uma Scout Comparison entre Players, destinado a ser enviado a um treinador.
_Avoid_: Export, scout report.
