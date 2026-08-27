# Overview por Métrica — nova página inicial do dashboard

Status: ready-for-agent

## Problem Statement

Hoje o dashboard entra direto numa tela única e carregada (filtros, leaderboards, perfil de Player, Scout Comparison, tudo junto), sem um ponto de entrada simples pra "quem está no topo em tal Metric". Não existe uma forma rápida de comparar o Top 10 de Players por uma Metric específica, com o contexto de onde cada um está (percentil) dentro da população que interessa no momento (depois de aplicar filtros como Position, Team, Minutes Floor etc.), sem já cair em gráficos, Scout Comparison ou perfil individual.

## Solution

Criar uma nova página "Overview" como tela inicial do dashboard (usando o suporte nativo de multipage do Streamlit), que começa vazia com a instrução "Selecione uma métrica de desempenho". Ao escolher uma Metric na sidebar, aparece uma tabela com o Top 10 de Players por aquela Metric (Nome, Time, Posição, valor da Metric, percentil), calculada sobre a população já filtrada pelos filtros ativos. Cada Metric selecionada adiciona uma nova tabela ao grid (2 por linha, reagrupando quando uma Metric é desmarcada). O conteúdo atual do dashboard (Player Profile, Insights, Scout Comparison, exportação de PDF) é relocado para uma segunda página da navegação, sem mudanças funcionais — o redesenho dessa segunda página fica para uma spec futura.

## User Stories

1. Como usuário do dashboard, quero que o app abra numa navegação multipage nativa do Streamlit, pra que Overview e o restante das funcionalidades fiquem em telas separadas em vez de uma única tela carregada.
2. Como usuário do dashboard, quero que a página Overview seja a tela inicial (landing page) do app, pra chegar direto na exploração por Metric.
3. Como usuário do dashboard, quero que a página Overview comece vazia com a mensagem "Selecione uma métrica de desempenho", pra entender imediatamente o que fazer antes de escolher qualquer filtro.
4. Como usuário do dashboard, quero escolher uma ou mais Metrics na sidebar da Overview, pra ver o Top 10 de Players em cada uma.
5. Como usuário do dashboard, quero que cada Metric selecionada gere sua própria tabela, pra comparar múltiplas Metrics lado a lado sem precisar navegar entre telas.
6. Como usuário do dashboard, quero que as tabelas apareçam organizadas em duas colunas por linha, crescendo conforme seleciono mais Metrics, pra aproveitar melhor o espaço horizontal da tela.
7. Como usuário do dashboard, quero que, ao desmarcar uma Metric, a tabela correspondente suma e as demais reagrupem sem deixar buraco no grid, pra manter o layout organizado.
8. Como usuário do dashboard, quero que cada tabela mostre Nome, Time, Posição, valor da Metric e percentil do Player, pra ter contexto suficiente sem precisar abrir o perfil individual.
9. Como usuário do dashboard, quero que o valor exibido de cada Metric seja por-90 minutos por padrão, pra comparar Players de forma justa independente do tempo jogado, sem precisar escolher isso manualmente.
10. Como usuário do dashboard, quero que Metrics que já são percentuais na origem (ex: aproveitamento de defesas) sejam exibidas como percentual, sem aplicar o cálculo por-90 nelas, pra não ver números sem sentido.
11. Como usuário do dashboard, quero que o percentil de cada Player na tabela seja calculado apenas entre os Players que atendem aos filtros ativos no momento, pra que o percentil reflita exatamente o grupo que estou olhando, e não uma população mais ampla e não visível.
12. Como usuário do dashboard, quero filtrar por Team, Position, Position Group e Minutes Floor na Overview, reaproveitando os mesmos filtros já existentes no dashboard, pra restringir o Top 10 e o cálculo de percentil ao grupo que me interessa.
13. Como usuário do dashboard, quero filtrar por League, pra restringir a Overview a uma competição específica quando houver mais de uma disponível.
14. Como usuário do dashboard, quero ver os filtros de Idade e Nacionalidade na sidebar mesmo que ainda não funcionem, desabilitados com uma indicação de "em breve", pra saber que estão a caminho sem serem confundidos com filtros ativos que simplesmente não fazem nada.
15. Como usuário do dashboard, quero que o restante das funcionalidades que já existem hoje (Player Profile, Insights, Scout Comparison, exportação de Reports em PDF) continue acessível numa segunda página, sem nenhuma mudança de comportamento, pra não perder nada do que já uso enquanto a Overview é construída.
16. Como mantenedor do projeto, quero que o formato de cada Statistic (numérico vs. percentual) seja capturado na normalização da ingestão a partir do payload bruto do FotMob, pra que o cálculo por-90 saiba quando não deve ser aplicado.
17. Como mantenedor do projeto, quero que essa informação de formato fique persistida junto de cada Statistic, pra que a Analysis não precise inferir o formato a partir do nome ou label da Metric.
18. Como mantenedor do projeto, quero que a consulta de Players usada pela Overview seja capaz de atribuir a League de cada Player (via Season/Snapshot), pra que o filtro de League funcione de verdade mesmo havendo hoje uma única League ingerida.
19. Como mantenedor do projeto, quero que o cálculo de Top 10 e percentil por Metric seja uma função pura, testável sem Streamlit nem banco, reaproveitando o padrão de Seam B já estabelecido no projeto.
20. Como mantenedor do projeto, quero que a extração do formato da Statistic seja testável sem rede, reaproveitando as fixtures de FotMob já existentes (Seam A), pra cobrir tanto Statistics numéricas quanto percentuais (ex: `save_percentage`).

## Implementation Decisions

- **Navegação multipage (Dashboard)**: introduzir `st.navigation` com uma pasta `dashboard/pages/`. Duas entradas: **Overview** (nova, construída nesta spec, página padrão/inicial) e uma segunda página contendo o conteúdo integral do `app.py` atual (filtros gerais, leaderboards por Metric com gráfico, Player Profile, Insights, Scout Comparison, downloads de PDF) **relocado sem alterações funcionais** — apenas movido de arquivo. O redesenho ou reorganização dessa segunda página não faz parte desta spec.
- **Estado vazio (Overview)**: nenhuma Metric selecionada → exibe apenas o texto "Selecione uma métrica de desempenho", sem tabelas, sem filtros de resultado renderizados abaixo.
- **Seletor de Metrics (Overview)**: multiselect na sidebar reaproveitando `metric_label_options` já existente. Cada Metric selecionada adiciona uma tabela; a ordem das tabelas segue a ordem de seleção. Não existe nesta página o seletor de "tipo de Metric" (Raw/Per-90/Percentile) que existe na tela atual — aqui o tipo é implícito (ver próximo item).
- **Cálculo do valor exibido**: por padrão, valor por-90 (reaproveitando `per_90()` de `analysis/metrics.py`). `per_90()` passa a checar o formato da Statistic (novo campo, ver abaixo): se for percentual, retorna o valor bruto sem dividir por minutos; caso contrário, mantém o cálculo atual (`value * 90 / minutos`).
- **Formato da Statistic (Ingestão + Persistência)**: capturar o campo de formato do payload bruto do FotMob (presente como `statFormat`, ex: `"percentage"`, em categorias como goleiro) em `parse_all_stats`/`parse_category_stats`/`parse_top_stats` (`ingestion/normalize.py`). Adicionar esse valor como novo atributo do registro de domínio `Statistic` (`domain/models.py`). Adicionar coluna correspondente na tabela `statistics` do schema (migration), e persistir/ler esse valor na camada de persistência.
- **Top 10 e percentil (Analysis)**: nova função pura de leaderboard que recebe a população já filtrada (Team, Position, Position Group, Minutes Floor, League, e futuramente Age/Nationality) e uma `MetricSpec`, retorna até 10 Players ordenados pelo valor exibido (per-90 ou percentual, conforme acima), com o percentil de cada um calculado **sobre essa mesma população filtrada** — não existe, nesta página, separação entre "população de referência" e "população exibida" como no leaderboard atual da tela existente.
- **Quartil**: termo já definido em `CONTEXT.md` (faixas de 25 pontos percentuais derivadas do percentil), mas não é usado em nenhuma tela construída por esta spec — fica reservado para uma spec futura.
- **Filtros funcionais (Overview)**: Team, Position, Position Group, Minutes Floor — reaproveitam os mesmos filtros/funções já existentes (`filter_by_position_group`, `apply_minutes_floor`). League — filtro real, requer que a consulta de Players (`persistence/player_queries.py`) seja capaz de atribuir a League de cada Player via join `snapshots → seasons → leagues`; hoje resulta numa única opção selecionável (Premier League), mas o filtro já deve funcionar de fato quando uma segunda League existir.
- **Filtros desabilitados (Overview)**: Idade e Nacionalidade aparecem na sidebar como controles desabilitados (ex: `disabled=True`, com texto indicando indisponibilidade temporária). Não filtram nada nesta spec — não há coluna de idade/nacionalidade em `Player` nem no schema ainda.

## Testing Decisions

- Um bom teste aqui valida apenas comportamento externo (dado um input, o output esperado), sem depender de como a normalização ou o cálculo são implementados por dentro — mesmo critério já usado no restante do projeto.
- **Seam A — Normalização** (estendido): novos casos de teste com as fixtures existentes de FotMob (`tests/fixtures/fotmob/`), incluindo `goalkeeper_player_stats.json` (que já contém `save_percentage` com `statFormat: "percentage"`), garantindo que o formato de cada Statistic é extraído corretamente e refletido no registro `Statistic` normalizado — tanto pra Statistics numéricas quanto percentuais.
- **Seam B — Análise** (estendido): novos casos de teste com fixtures em código (conjuntos construídos de Players/Statistics), cobrindo: `per_90()` retornando o valor bruto sem dividir para Statistics percentuais e o cálculo por-90 normal para as demais; a nova função de leaderboard Top-10-por-Metric retornando o ranking e o percentil corretos para uma população arbitrária passada como argumento (incluindo o caso de menos de 10 Players qualificados, retornando menos linhas, como já ocorre no leaderboard atual).
- Não há testes automatizados para a camada de I/O (chamadas HTTP ao FotMob, join de League no Supabase, renderização Streamlit, navegação multipage, estado desabilitado dos filtros) — verificação manual apenas, mesmo padrão já adotado no restante do projeto.

## Out of Scope

- Filtros de Idade e Nacionalidade funcionais — nesta spec eles existem só como controles desabilitados na sidebar; a ingestão/normalização/schema necessários (capturar `age`/`dateOfBirth`/`ccode`/`cname` do FotMob) ficam para uma spec futura.
- Gráficos na página Overview — cada Metric selecionada gera apenas uma tabela, sem chart.
- Exibição de Quartil em qualquer tela — o termo está definido no glossário, mas não é implementado nesta spec.
- Redesenho, reorganização ou qualquer mudança de comportamento da segunda página (conteúdo atual do dashboard) além de movê-la de arquivo dentro da nova estrutura multipage.
- Ingestão de uma segunda League — o filtro de League fica funcionalmente pronto, mas apenas Premier League 2025/26 é ingerida nesta spec.
- Toggle de tipo de Metric (Raw/Per-90/Percentile) na página Overview.
- Qualquer mudança na Scout Comparison, Insights ou geração de PDF existentes, além da relocação de arquivo.

## Further Notes

- As rotas do FotMob usadas pela Ingestão continuam sem API oficial documentada (mesma ressalva da spec anterior) — o campo `statFormat` deve ser tratado com o mesmo cuidado de "quebrar de forma visível, não silenciosa" caso o formato mude ou desapareça do payload.
- `CONTEXT.md` já foi atualizado com o termo **Quartil** durante o grilling que originou esta spec.
- Vocabulário do domínio usado nesta spec: League, Season, Team, Player, Position, Position Group, Statistic, Metric, Quartil, Minutes Floor (todos já definidos em `CONTEXT.md`).
- Esta spec depende de dois ajustes de dados que **não** são adiáveis como Idade/Nacionalidade: captura de `statFormat` e o join de League na consulta de Players — sem eles, a Overview exibiria valores por-90 incorretos para Statistics percentuais e um filtro de League inoperante.
