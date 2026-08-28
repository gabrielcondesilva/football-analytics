# 01: Estender Player com atributos biográficos opcionais

**What to build:** `Player` passa a carregar `age`, `nationality`, `preferred_foot` e `photo_url`, todos opcionais e vazios por padrão. Nenhuma extração de ingestão ainda — é só a base de domínio que o card da Análise de Jogadores vai consumir.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `Player` aceita `age`/`nationality`/`preferred_foot`/`photo_url` opcionais, default vazio/nulo.
- [x] Fixtures/testes existentes continuam passando sem alteração (compatibilidade retroativa).
- [x] Testes cobrindo construção de `Player` com e sem esses campos.
