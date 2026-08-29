# 01: Liga atual do Team, independente das Statistics

**What to build:** Hoje a Liga exibida/filtrável de um Player é inferida indiretamente de qual Snapshot suas Statistics vieram (Snapshot → Season → League) — o Team em si não guarda nenhuma League. Esta fatia dá ao Team sua própria Liga atual (o elenco mais recente ingerido), desacoplada de onde as Statistics exibidas foram produzidas, e faz a leitura usada pelo dashboard passar a derivar a Liga de cada Player do seu Team. É o prefactor que destrava o fallback entre Leagues (ticket 02) sem quebrar nada do que já existe hoje.

**Blocked by:** None (can start immediately)

- [ ] `teams` ganha uma referência à sua League atual, de forma aditiva/nullable (sem quebrar leituras existentes antes do backfill rodar)
- [ ] A escrita de Team durante a ingestão passa a gravar a League sendo ingerida no momento como a League atual desse Team
- [ ] A leitura usada pelo dashboard passa a derivar a Liga exibida/filtrável de cada Player da League atual do seu Team, não mais de qual Snapshot suas Statistics vieram
- [ ] Todo Team já existente no banco (das 3 Leagues já ingeridas) recebe sua League atual retroativamente, cruzando com as listas de elenco dessas 3 Leagues
- [ ] Rodando a Visão Geral depois dessa mudança, o filtro de Liga e a Liga exibida de cada Player já ingerido continuam idênticos a antes — nenhuma regressão visível pros dados que já temos hoje
- [ ] `CONTEXT.md` e o ADR 0004 (já publicados) documentam essa decisão — nenhuma mudança de vocabulário adicional necessária nesta fatia
