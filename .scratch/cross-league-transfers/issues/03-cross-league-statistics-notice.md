# 03: Aviso discreto quando as Statistics mostradas são de outra Liga

**What to build:** Depois do ticket 02, um Player pode legitimamente mostrar Statistics de uma League diferente da sua Liga atual (ex.: Cucurella aparece no Real Madrid/La Liga com números do Chelsea/Premier League). Sem sinalização, isso pode enganar quem está comparando desempenho entre Ligas de nível competitivo diferente. Esta fatia expõe, na leitura, de qual League vieram as Statistics exibidas de cada Player, e mostra um aviso discreto na Visão Geral quando essa League diverge da Liga atual do Player.

**Blocked by:** 01 (Liga atual do Team, independente das Statistics), 02 (Fallback de Statistics entre Leagues conhecidas na ingestão)

- [ ] A leitura usada pelo dashboard passa a expor também a League de onde vieram as Statistics exibidas de cada Player, além da sua Liga atual (via Team)
- [ ] Na Visão Geral, quando essas duas Ligas divergem, a linha do Player no leaderboard mostra um aviso discreto indicando a League de origem das Statistics
- [ ] Quando as duas Ligas coincidem (caso comum, hoje 100% dos casos), nenhum aviso aparece e a linha permanece como está
- [ ] O aviso não compete visualmente com o conteúdo principal da linha (nome, valor da Metric) — mudança visual passa pelo subagent `streamlit-dashboard-designer`, como já é convenção no projeto (CLAUDE.md)
- [ ] Verificação manual: com pelo menos um Player em estado de fallback (ex.: rodar o ticket 02 contra um caso real), abrir a Visão Geral e confirmar que o aviso aparece só nesse Player, nos dois temas (claro/escuro)
