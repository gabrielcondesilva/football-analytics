# 03: Backfill do Mapa de Toques para jogadores já existentes

**What to build:** Todo Player ingerido antes desta feature existir não tem Mapa de Toques — precisa de uma passada dedicada, sem re-rodar a ingestão completa de cada Liga (cara e demorada). Um script novo e independente (mesmo espírito do `backfill_bio.py` já existente) itera todo Player já no banco, descobre qual League/Season já sustenta as Statistics atuais de cada um, busca só essa entrada específica no FotMob, e faz o upsert do Mapa de Toques reaproveitando exatamente as funções e a operação de persistência do ticket 01.

**Blocked by:** 01 (Capturar e guardar o Mapa de Toques na ingestão), 02 (Exibir o Mapa de Toques na Análise de Jogadores)

- [ ] Script novo, iterando todo Player já no banco
- [ ] Para cada Player, descobre a League/Season que já produz suas Statistics atuais (via o Snapshot de qualquer uma das suas linhas de `statistics` existentes — o mesmo dado que já alimenta `statistics_league`), sem re-rodar a busca de fallback do zero
- [ ] Chama `find_entry_id` diretamente contra esse tournament_id/season_name já conhecido, busca `playerStats` só pra essa entrada, extrai as coordenadas via a função do Seam A (ticket 01), e faz o upsert via a mesma operação de persistência que a ingestão normal usa
- [ ] Um Player sem nenhuma Statistic é pulado (logado, não tratado como erro) — não há League/Season conhecida pra se basear
- [ ] Idempotente: rodar de novo só repete o mesmo upsert, sem duplicar nem falhar
- [ ] Rodado de verdade contra o banco atual, cobrindo todas as Leagues já ingeridas
- [ ] Verificação manual: um Player que já estava na base antes desta feature existir (ex.: Joey Veerman) passa a mostrar o Mapa de Toques na Análise de Jogadores (tela do ticket 02), vindo da mesma League/Season que já sustenta as Statistics dele hoje

**Status:** ready-for-agent
