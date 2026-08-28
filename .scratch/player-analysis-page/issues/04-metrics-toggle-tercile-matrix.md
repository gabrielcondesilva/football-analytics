# 04: Multiselect de Metrics, toggle Por Temporada/Por 90, e matriz colorida por Tercil

**What to build:** Abaixo do nome no card, um multiselect dedicado de Metrics e um toggle Por Temporada/Por 90 min. As Metrics selecionadas populam, ao lado do card, uma matriz (Métrica, Valor, Percentual) calculada sobre a População de Comparação (Position Group + Minutes Floor ativos), com o Percentual colorido por Tercil (vermelho/amarelo/verde).

**Blocked by:** 03 (shell, busca, filtros, card)

**Status:** done

- [x] Multiselect de Metrics é dedicado a esta seção, independente de qualquer filtro de Metrics de outra página.
- [x] Toggle Por Temporada/Por 90 min recalcula os valores das Metrics já selecionadas sem misturar os dois tipos.
- [x] Matriz mostra Métrica, Valor e Percentual para cada Metric selecionada, população = Players do Position Group ativo (ou todos) filtrados por Minutes Floor.
- [x] Percentual colorido pela banda de Tercil correspondente (pior terço vermelho, médio amarelo, melhor terço verde), via função pura testada isoladamente.
- [x] Sem nenhuma Metric selecionada, exibe mensagem de instrução em vez da matriz.
