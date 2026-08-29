# 02: Fallback de Statistics entre Leagues conhecidas na ingestão

**What to build:** Hoje, quando um Player do elenco atual de uma League não tem entrada de Statistics nessa League/Season (ex.: acabou de ser transferido), a ingestão o pula inteiramente — ele some da base mesmo tendo dados completos disponíveis no FotMob sob a League antiga. Esta fatia faz a ingestão procurar, entre as outras competições da mesma Season do Player, alguma que bata com uma League já conhecida, e trazer essas Statistics junto — salvas na Season/League de onde realmente vieram — enquanto Team e dados biográficos sempre refletem a League sendo ingerida agora. Um Player sem nenhuma correspondência conhecida deixa de ser pulado: passa a ser salvo com Team/Liga atuais corretos, só sem Statistics por enquanto.

**Blocked by:** 01 (Liga atual do Team, independente das Statistics)

- [ ] Nova função pura de normalização (Seam A), irmã de `find_entry_id`: dado o payload de `playerData` de um Player, o `season_name` alvo, e o conjunto de Leagues já conhecidas, devolve qual League + entryId usar como fallback — a primeira competição da Season do Player (na ordem em que o FotMob a lista) cujo `tournamentId` bate com uma League conhecida, ou nada se nenhuma bater
- [ ] Testada por fixture (mesmo estilo de `find_entry_id`): encontra a entrada certa entre várias competições da Season; não encontra nada quando só existem competições desconhecidas (ex.: só Copas); mesmo comportamento nulo-seguro já estabelecido pra payload/Season ausente; desempate determinístico quando mais de uma competição bate com uma League conhecida na mesma Season
- [ ] `find_entry_id` não muda — nenhum teste existente dele é alterado
- [ ] A ingestão de uma League tenta primeiro o match exato de hoje; se não achar, tenta o fallback acima
- [ ] Quando o fallback acha uma League diferente da que está sendo ingerida, as Statistics são gravadas na Season/Snapshot dessa outra League, reaproveitando o Snapshot mais recente já existente pra ela (sem criar um Snapshot novo só por causa de um Player) — a League sendo ingerida agora continua sempre ganhando seu próprio Snapshot novo, como hoje
- [ ] Um Player sem match exato nem fallback ainda é salvo (Team/bio atualizados pra League sendo ingerida), só sem nenhuma Statistic — deixa de ser pulado inteiramente
- [ ] Um Player sem nenhuma Statistic não aparece em nenhum leaderboard/Top 10 por Metric (sem erro, sem linha vazia)
- [ ] A ingestão continua idempotente/reentrante com essa lógica nova
- [ ] Verificação manual: re-rodar a ingestão de uma League já ingerida e confirmar que um jogador transferido conhecido (ex.: Cucurella ou Witsel) aparece com o Time novo e as Statistics da League antiga corretamente atribuídas
