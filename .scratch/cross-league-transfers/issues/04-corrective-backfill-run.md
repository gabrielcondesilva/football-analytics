# 04: Passe corretivo nas 3 Leagues já ingeridas

**What to build:** Recuperar, agora, os Players que hoje estão fora da base inteiramente por causa do gap que os tickets 01/02 corrigem — casos reais já identificados: Marc Cucurella (Chelsea → Real Madrid) e Axel Witsel (La Liga → Nice), e qualquer outro Player na mesma situação nas 3 Leagues já ingeridas (Premier League, La Liga, Ligue 1). Não é código novo — é executar a capacidade construída no ticket 02 contra os dados reais e confirmar o resultado.

**Blocked by:** 02 (Fallback de Statistics entre Leagues conhecidas na ingestão)

- [ ] Ingestão re-executada para Premier League, La Liga e Ligue 1, usando a lógica de fallback já pronta
- [ ] Marc Cucurella aparece na base com Time = Real Madrid, Liga atual = La Liga, e Statistics vindas do Premier League/Chelsea (com o aviso do ticket 03, se já publicado)
- [ ] Axel Witsel aparece na base com Time = Nice, Liga atual = Ligue 1, e Statistics vindas do La Liga
- [ ] Nenhum Player que já tinha dados corretos antes deste passe perde ou duplica Statistics como efeito colateral da re-ingestão
- [ ] Contagem de Players por Liga na Visão Geral batendo com o esperado depois do passe (sem trocar de página surpresas de contagem)
