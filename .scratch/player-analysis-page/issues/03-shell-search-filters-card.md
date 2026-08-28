# 03: Shell da página Análise de Jogadores — busca, filtros e card

**What to build:** A página é renomeada para "Análise de Jogadores" e reconstruída com uma sidebar própria: busca de Player por nome (seleção única), Position Group (auto-preenchido com o grupo do Player selecionado, editável, resetado a cada troca de Player) e Minutes Floor. Selecionar um Player exibe um card com avatar placeholder, nome, posições, time, e idade/nacionalidade/pé preferido (hoje sempre "-", já que esse dado ainda não é ingerido). Sem Player selecionado, exibe uma mensagem de instrução.

**Blocked by:** 01 (Player biográfico), 02 (remoção do conteúdo antigo)

**Status:** done

- [x] Página aparece na navegação como "Análise de Jogadores".
- [x] Busca de Player é seleção única com filtro embutido; sem Player selecionado, exibe mensagem de instrução em vez do card.
- [x] Ao selecionar um Player, o filtro de Position Group é preenchido automaticamente com o grupo dele, permanece editável (inclusive pra "Todos"), e volta a ser preenchido automaticamente sempre que o Player muda.
- [x] Filtro de Minutes Floor disponível na sidebar desta página.
- [x] Card exibe avatar placeholder genérico, nome, posições, time, e idade/nacionalidade/pé preferido como "-".
