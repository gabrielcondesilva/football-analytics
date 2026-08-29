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
Um jogador individual com Statistics e Metrics agregadas por Season, além de atributos biográficos (idade, nacionalidade, pé preferido) quando disponíveis. É a unidade central de comparação e scouting do projeto.
_Avoid_: Athlete, atleta.

**Position**:
Um papel que um Player pode ocupar em campo (ex: zagueiro, lateral). Um Player pode ter múltiplas Positions.
_Avoid_: Role.

**Position Group**:
Classificação mais ampla de Positions (ex: defensores, meio-campistas, atacantes), usada por padrão para escopar a População de Comparação de um Player a jogadores comparáveis.

### Estatísticas e métricas

**Statistic**:
Um valor bruto coletado do FotMob para um Player em uma Season (ex: total de gols, passes certos).
_Avoid_: Metric, stat, número.

**Metric**:
Qualquer valor usado para comparação ou visualização — pode ser uma Statistic bruta ou um valor derivado dela (por-90, percentil). É o que o usuário escolhe na sidebar do dashboard.
_Avoid_: Stat, KPI.

**População de Comparação**:
A população de referência usada para calcular o percentil de um Player em uma Metric. Cada tela do dashboard escopa essa população com seus próprios filtros — ex.: a Análise de Jogadores escopa por Position (código exato do próprio Player, correspondência em qualquer uma de suas Positions — não apenas o Position Group) e Minutes Floor, sem usar Team/League.
_Avoid_: Peer group, referência, população de referência.

**Quartil**:
A faixa de 25 pontos percentuais em que o percentil de uma Metric do Player se encontra em relação à População de Comparação (Q1 = 0–25, Q2 = 25–50, Q3 = 50–75, Q4 = 75–100). Derivado do percentil já calculado, não é um cálculo independente. Ainda não tem uso implementado no app — reservado para uma visualização futura, distinto do Tercil.

**Tercil**:
A faixa de aproximadamente 33 pontos percentuais em que o percentil de uma Metric do Player se encontra em relação à População de Comparação (pior terço = 0–33, terço médio = 33–67, melhor terço = 67–100). Usado para classificar visualmente (vermelho/amarelo/verde) o desempenho relativo do Player nas Metrics escolhidas na Análise de Jogadores. Derivado do percentil já calculado, não é um cálculo independente, e coexiste com o Quartil como um esquema de faixas separado, não um substituto.

**Snapshot**:
Uma captura datada das Statistics de um Player, feita em um momento do scraping. Permite múltiplos Snapshots por Player-Season ao longo do tempo, mesmo que hoje só exista um scraping único por Season.
_Avoid_: Version, scrape, coleta.

**Minutes Floor**:
O piso mínimo de minutos jogados que um Player precisa atingir para entrar em comparações e rankings, evitando distorção por amostra pequena. Ajustável pelo usuário.
