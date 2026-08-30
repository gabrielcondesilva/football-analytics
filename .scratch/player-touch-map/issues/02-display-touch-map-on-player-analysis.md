# 02: Exibir o Mapa de Toques na Análise de Jogadores

**What to build:** Uma seção nova, sempre visível, abaixo da Matriz/Radar já existentes na Análise de Jogadores. Assim que um Player é selecionado, um campo desenhado de forma simples (grade 6×4, sem gradiente suave) mostra a % dos toques dele em cada célula, usando o Mapa de Toques capturado no ticket 01. Independente do multiselect de Métricas, do toggle Por Temporada/Por 90 min e do Minutes Floor — não é uma Metric comparada contra População de Comparação, é a distribuição bruta de toques do próprio Player.

**Blocked by:** 01 (Capturar e guardar o Mapa de Toques na ingestão)

- [ ] Nova consulta de leitura, independente de `list_players()`, que busca o Mapa de Toques de um único Player pelo id — só chamada pela Análise de Jogadores, só pro Player selecionado no momento (não engorda nenhuma consulta usada por outras páginas)
- [ ] Nova seção na página, abaixo da Matriz/Radar, disparada só pela seleção do Player — não pelo multiselect de Métricas, toggle Por Temporada/Por 90 min, ou Minutes Floor
- [ ] Busca o Mapa de Toques do Player selecionado, roda pela função de bucketing do ticket 01, e desenha o campo com formas do Plotly (retângulos + texto de porcentagem por célula) — sem biblioteca nova, mesmo padrão já usado pelo Radar da página
- [ ] Layout exato, cores, bordas das células e formatação da porcentagem definidos pelo subagent `streamlit-dashboard-designer`, conforme o CLAUDE.md deste repositório
- [ ] Mensagem clara de "sem dados" quando o Player selecionado ainda não tem Mapa de Toques (não backfilled, ou sem nenhuma Statistic pra se basear) — nunca um gráfico vazio ou quebrado
- [ ] Verificação manual: re-rodar a ingestão de uma Liga (ticket 01) e selecionar, na Análise de Jogadores, um Player dela que tenha Mapa de Toques — confirmar que a grade aparece com percentuais somando 100%
- [ ] Verificação manual: selecionar um Player sem Mapa de Toques ainda e confirmar a mensagem de "sem dados", sem erro

**Status:** ready-for-agent
