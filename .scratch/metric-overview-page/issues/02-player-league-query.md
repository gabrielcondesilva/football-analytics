# 02: League atribuída a cada Player na consulta

**What to build:** Fazer a consulta de Players retornar a League de cada um, via join até `leagues`, pra que um filtro de League tenha dado real por trás mesmo havendo hoje uma única League ingerida.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A consulta de Players (`list_players` ou equivalente) faz join `snapshots → seasons → leagues` e retorna a League de cada Player.
- [ ] Funciona corretamente com os dados atuais (uma única League: Premier League 2025/26).
- [ ] Coberto por teste automatizado ou, na ausência de testes de I/O nesta camada (mesmo padrão do resto do projeto), por verificação manual documentada da consulta.
