# 01: Capturar e guardar o Mapa de Toques na ingestão

**What to build:** Hoje a ingestão busca `playerStats` do FotMob só pra extrair Statistics — mas essa mesma resposta já traz as coordenadas de cada toque na bola do Player na Season (`heatmap.coordinates`), sem nenhum custo extra de requisição. Esta fatia captura essas coordenadas e guarda numa tabela nova, própria, com uma linha por Player (upsert, sem `snapshot_id`) — um fato current-state dele, como idade ou foto, substituído por completo a cada ingestão, nunca acumulado por Snapshot (ADR-0005). Inclui as duas funções puras que sustentam o resto da feature: extração null-safe do payload (Seam A) e bucketing numa grade fixa 6×4 (Seam B), ambas testadas. Ainda não aparece em lugar nenhum do dashboard — isso é o ticket 02.

**Blocked by:** None (can start immediately)

- [ ] Tabela nova, independente de `statistics`/`snapshots`: uma linha por Player (chave/índice único em `player_id`, referência a `players(id)` com `on delete cascade`), uma coluna `jsonb` com as coordenadas brutas de toque
- [ ] Escrita é sempre upsert — insere ou substitui por completo a linha existente daquele Player, nunca uma segunda linha pro mesmo Player
- [ ] Nova função pura no Seam A (`normalize.py`), irmã de `parse_all_stats`: extrai `heatmap.coordinates` do payload de `playerStats` pra uma lista simples de pares `(x, y)` — payload ausente, `heatmap` ausente, `coordinates` ausente/nulo/vazio todos devolvem lista vazia, nunca uma exceção (mesmo padrão dos guards `or []` já usados por `find_entry_id`)
- [ ] Testada por fixture, mesmo estilo de `parse_top_stats`/`parse_all_stats`: payload normal com coordenadas presentes; payload sem a chave `heatmap`; `heatmap` presente mas `coordinates` ausente/nulo/vazio
- [ ] Nova função pura no Seam B (`analysis/`): recebe a lista de pares `(x, y)` (escala 0–100 em cada eixo) e devolve a % de toques em cada célula de uma grade de 6 linhas (3 cobrindo x de 0 a 50, 3 cobrindo x de 50 a 100, cada terço dividido em 3 faixas iguais) × 4 colunas iguais (cobrindo y de 0 a 100)
- [ ] Testada: distribuição cobrindo as 24 células soma exatamente 100%; ponto exatamente na borda entre duas células cai numa regra determinística e documentada; lista vazia devolve um sinal claro de "sem dados" (nunca divisão por zero); todos os pontos numa única célula confirma que as outras 23 ficam em 0%
- [ ] Na ingestão (`run.py`), no mesmo ponto em que o `entry_id` resolvido (exato ou fallback) já busca `playerStats` pra `parse_all_stats`, a nova função do Seam A extrai as coordenadas do mesmo payload já em mãos e uma nova operação de persistência faz o upsert na tabela nova
- [ ] Um Player salvo sem nenhuma Statistic (nem exato, nem fallback) também não ganha Mapa de Toques — mesmo log de "sem dados" já usado hoje pra Statistics, sem tratar como erro
- [ ] Verificação manual: re-rodar a ingestão de uma Liga já ingerida e confirmar, direto no banco, que um Player conhecido dessa Liga ganhou uma linha na tabela nova com coordenadas plausíveis

**Status:** ready-for-agent
