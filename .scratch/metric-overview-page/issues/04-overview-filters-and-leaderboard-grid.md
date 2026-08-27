# 04: Overview — filtros e grid de Top 10 por Metric

**What to build:** A funcionalidade completa da página Overview: escolher Metrics na sidebar e ver, para cada uma, uma tabela com o Top 10 de Players (valor e percentil) calculada sobre a população já filtrada, além dos filtros funcionais e dos placeholders desabilitados de Idade/Nacionalidade.

**Blocked by:** 01 (Formato de Statistic fim a fim), 02 (League atribuída a cada Player na consulta), 03 (Shell multipage — Overview vazia + dashboard atual relocado)

**Status:** ready-for-agent

- [ ] Multiselect de Metrics na sidebar da Overview, reaproveitando as Metrics já disponíveis no dashboard.
- [ ] Cada Metric selecionada adiciona uma tabela com até 10 Players (Top 10), colunas: Nome, Time, Posição, valor da Metric, percentil.
- [ ] Valor da Metric é por-90 por padrão, exceto Statistics percentuais (usando o formato do ticket 01), exibidas como percentual sem aplicar o cálculo por-90.
- [ ] Percentil de cada Player é calculado sobre a população já filtrada pelos filtros ativos no momento — não existe população de referência separada da população exibida nesta página.
- [ ] Tabelas organizadas em grid de 2 por linha, na ordem em que as Metrics foram selecionadas; ao desmarcar uma Metric, a tabela correspondente some e as demais reagrupam sem deixar buraco.
- [ ] Filtros funcionais na sidebar: Team, Position, Position Group, Minutes Floor, e League (usando o join do ticket 02) — hoje resultando numa única opção de League.
- [ ] Filtros de Idade e Nacionalidade aparecem na sidebar desabilitados, com indicação de indisponibilidade temporária ("em breve"), sem filtrar nada.
- [ ] Nova função pura de leaderboard Top-10-por-Metric (Seam B) coberta por testes, incluindo o caso de menos de 10 Players qualificados sob os filtros ativos.
