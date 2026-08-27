# 01: Formato de Statistic (percentual vs. numérico), fim a fim

**What to build:** Capturar o formato de cada Statistic (numérico ou percentual, ex: `save_percentage`) a partir do payload bruto do FotMob, persistir esse formato, e corrigir o cálculo por-90 pra não distorcer Statistics que já são percentuais.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] O formato de cada Statistic (`statFormat` no payload do FotMob, ex: `"percentage"`) é extraído durante a normalização, tanto pra Statistics numéricas quanto percentuais.
- [ ] O registro de domínio `Statistic` expõe esse formato como um novo atributo.
- [ ] A tabela `statistics` do schema tem uma coluna correspondente (migration), e a camada de persistência grava e lê esse valor.
- [ ] `per_90()` retorna o valor bruto (sem dividir por minutos) quando a Statistic é percentual, e mantém o cálculo por-90 normal para as demais.
- [ ] Testes de Seam A (normalização) cobrem a extração do formato usando as fixtures existentes de FotMob, incluindo `goalkeeper_player_stats.json` (`save_percentage`).
- [ ] Testes de Seam B (análise) cobrem `per_90()` para os dois casos: Statistic percentual e Statistic numérica.
