# Análise de Jogadores — reconstrução da página de perfil individual

Status: ready-for-agent

## Problem Statement

Hoje a página "Player Workspace" mistura três coisas num só lugar: um leaderboard geral por Metric, uma Scout Comparison entre múltiplos Players, e um perfil individual raso (sem contexto biográfico, com Insights gerados por regras fixas e dependente de exportação em PDF). Não existe uma tela focada só em "escolhi um Player, quero entender como ele se compara aos jogadores da mesma posição", com contexto visual (card) e uma leitura rápida de onde ele está — entre os melhores, na média, ou entre os piores — em cada Metric relevante.

## Solution

Reconstruir a página do zero, renomeada para "Análise de Jogadores". Sidebar própria da página: busca de Player por nome (seleção única, com filtro embutido), Position Group (auto-preenchido com o grupo do Player selecionado, editável, resetado a cada troca de Player) e Minutes Floor. Ao selecionar um Player, um card exibe avatar placeholder, nome, posições, time, e idade/nacionalidade/pé preferido (hoje sempre "-", pois esse dado ainda não é ingerido). Abaixo do nome, um multiselect de Metrics dedicado a esta seção, com um toggle Por Temporada/Por 90 min. As Metrics selecionadas alimentam, lado a lado com o card, uma matriz (Métrica, Valor, Percentual — colorida por Tercil dentro da População de Comparação) ou, via um segundo toggle, um gráfico de radar (um eixo por Metric, valor = percentil, cor única). Scout Comparison, o leaderboard geral e o Insight antigo — com seus Reports em PDF — são removidos do código (ADR 0003), não apenas escondidos.

## User Stories

1. Como usuário do dashboard, quero buscar um Player pelo nome numa página dedicada, pra focar a análise nele sem o ruído de leaderboards e comparações que não me interessam nesse momento.
2. Como usuário do dashboard, quero que a busca seja um único campo com filtro embutido (não texto livre + botão separado), pra selecionar o Player em um passo só.
3. Como usuário do dashboard, quero selecionar só um Player por vez, pra manter o foco da análise nesse jogador específico.
4. Como usuário do dashboard, quero que a página comece vazia com uma instrução clara antes de eu escolher um Player, pra saber o que fazer.
5. Como usuário do dashboard, quero que, ao selecionar um Player, o filtro de Position Group já venha preenchido com o grupo dele, pra comparar automaticamente com jogadores comparáveis sem precisar configurar nada.
6. Como usuário do dashboard, quero poder trocar manualmente o Position Group depois (inclusive pra "Todos"), pra comparar o Player contra outro grupo quando eu quiser.
7. Como usuário do dashboard, quero que o Position Group volte a ser preenchido automaticamente com o grupo do novo Player sempre que eu trocar de Player, pra não comparar sem querer contra o grupo do Player anterior.
8. Como usuário do dashboard, quero filtrar a População de Comparação por Minutes Floor, pra excluir jogadores com amostra pequena de minutos da comparação.
9. Como usuário do dashboard, quero ver um card do Player selecionado com um avatar (genérico por enquanto, sem foto real), pra identificar visualmente quem estou analisando.
10. Como usuário do dashboard, quero ver nome, posições e time do Player no card, pra ter o contexto básico sem procurar em outro lugar.
11. Como usuário do dashboard, quero ver idade, nacionalidade e pé preferido no card, mesmo que hoje apareçam como "-" por falta de dado ingerido, pra já ter o layout pronto pra quando esse dado existir.
12. Como usuário do dashboard, quero escolher quais Metrics ver na análise desse Player através de um filtro dedicado a essa seção (não o filtro de Metrics de outras páginas), pra montar exatamente a comparação que me interessa.
13. Como usuário do dashboard, quero alternar entre ver os valores Por Temporada ou Por 90 min, pra comparar da forma que fizer mais sentido pro contexto.
14. Como usuário do dashboard, quero que trocar esse toggle recalcule automaticamente os valores das Metrics já selecionadas, sem eu precisar reselecionar nada, pra não perder minha seleção ao mudar de visão.
15. Como usuário do dashboard, quero que nunca haja mistura de valores Por Temporada e Por 90 min na mesma visão, pra não comparar números em escalas diferentes por engano.
16. Como usuário do dashboard, quero ver uma matriz com o nome de cada Metric, o valor do Player nela, e o percentil dele dentro da População de Comparação, pra entender o desempenho relativo de forma objetiva.
17. Como usuário do dashboard, quero que o percentil na matriz seja colorido por Tercil (vermelho no pior terço, amarelo no terço médio, verde no melhor terço), pra identificar rapidamente pontos fortes e fracos sem ler os números um por um.
18. Como usuário do dashboard, quero que a População de Comparação desta página considere só Position Group e Minutes Floor (sem Team/League), pra manter o filtro simples nesta primeira versão, podendo evoluir depois.
19. Como usuário do dashboard, quero alternar entre a matriz e um gráfico de radar através de um botão, pra escolher a visualização que preferir sem perder a seleção de Metrics.
20. Como usuário do dashboard, quero que o radar mostre um eixo por Metric selecionada, com o valor sendo o percentil do Player (0–100%), pra visualizar o perfil dele de forma comparativa num único gráfico.
21. Como usuário do dashboard, quero que o radar use uma cor única, sem o esquema vermelho/amarelo/verde da matriz, pra manter a leitura do gráfico limpa.
22. Como usuário do dashboard, quero ver uma mensagem clara quando nenhuma Metric estiver selecionada, pra saber que preciso escolher pelo menos uma pra ver a matriz/radar.
23. Como usuário do dashboard, quero que a página se chame "Análise de Jogadores" na navegação, pra refletir o novo foco da tela.
24. Como usuário do dashboard, quero que Scout Comparison, o leaderboard geral por Metric e os Insights automáticos antigos (com seus Reports em PDF) deixem de existir nesta página, pra não ter funcionalidade órfã ou inconsistente com o novo design.
25. Como mantenedor do projeto, quero que o Player carregue campos biográficos opcionais (idade, nacionalidade, pé preferido, foto) no domínio, mesmo sem ingestão populando-os ainda, pra que o dashboard já tenha onde ler esse dado quando a ingestão existir.
26. Como mantenedor do projeto, quero que a classificação de percentil em Tercil seja uma função pura testável sem Streamlit nem banco, reaproveitando o padrão de Seam B já estabelecido no projeto.
27. Como mantenedor do projeto, quero que a remoção de Scout Comparison, Insight e Report inclua o código morto associado (funções de análise, módulos de report, e seus testes), pra não deixar código sem dono no repositório.

## Implementation Decisions

- Página renomeada de "Player Workspace" para "Análise de Jogadores", reconstruída do zero — não é uma edição incremental da página atual.
- Domain model (`Player`): adicionar campos opcionais `age`, `nationality`, `preferred_foot`, `photo_url`, todos com default vazio/nulo. Nenhuma extração de ingestão nesta spec — os campos ficam vazios até uma spec futura de ingestão populá-los a partir do payload já buscado do FotMob.
- Sidebar própria da página, independente dos filtros da Overview: busca de Player por nome (seleção única, com filtro embutido), Position Group (com opção "Todos", auto-preenchido a partir do Player selecionado, editável, resetado a cada troca de Player), Minutes Floor.
- Card do Player: avatar placeholder genérico (sem foto real), nome, posições, time, e idade/nacionalidade/pé preferido exibidos com o rótulo do campo e "-" enquanto os campos do domínio estiverem vazios.
- Multiselect de Metrics dedicado a esta seção (não reaproveita nem interfere com o multiselect de Metrics de outras páginas), mais um toggle Por Temporada/Por 90 min reaproveitando os rótulos já usados no restante do app. Trocar o toggle recalcula os valores das Metrics já selecionadas, sem misturar os dois tipos na mesma visão.
- População de Comparação: Players filtrados pelo Position Group selecionado (ou todos, se "Todos") e pelo Minutes Floor ativo — sem Team/League nesta spec.
- Matriz: colunas Métrica, Valor (Por Temporada ou Por 90 min, conforme o toggle) e Percentual (calculado sobre a População de Comparação) — Percentual colorido pela banda de Tercil correspondente.
- Nova função pura de classificação de Tercil em `analysis/metrics.py`, mapeando um percentil (0–100) pra uma de três bandas (pior terço 0–33, terço médio 33–67, melhor terço 67–100), reaproveitada tanto pela matriz quanto pelo radar.
- Toggle Matriz ↔ Radar preserva a seleção de Metrics ao alternar. Radar usa um eixo por Metric selecionada, valor = percentil (mesmo cálculo da matriz), cor única (cor de marca do app, sem o esquema de três cores).
- Remoção completa: as funções de Scout Comparison e de Insight (incluindo o tipo `Insight`) em `analysis/metrics.py`; os dois módulos de geração de Report em PDF (perfil individual e Scout Comparison) e o módulo de montagem de PDF compartilhado entre eles, que fica órfão depois dessa remoção; as seções correspondentes da página atual (leaderboard geral, perfil antigo, Scout Comparison); e os testes associados a todo esse código.
- Trabalho de UI/chart (layout do card, cores validadas em light/dark, escolha do avatar placeholder, estilo do radar) é responsabilidade do subagent `streamlit-dashboard-designer` na fase de implementação, conforme o CLAUDE.md deste repositório — esta spec define comportamento, não o visual exato.

## Testing Decisions

- Um bom teste aqui valida apenas comportamento externo (dado um input, o output esperado), sem depender de como a implementação é feita por dentro — mesmo critério já usado no restante do projeto.
- **Seam B — Analysis** (estendido): novos casos de teste cobrindo a nova função de classificação de Tercil (limites exatos das faixas — 0, 33, 67, 100 — e os três valores de retorno possíveis), no mesmo arquivo e estilo dos testes já existentes de `percentile()`. Nenhuma função nova é necessária pra Valor/Percentual da matriz — já cobertos pelos testes existentes da função de cálculo de Metric por tipo (raw/per_90/percentile).
- Os testes existentes de Scout Comparison e de geração de Insight são removidos junto com as funções que testam, não mantidos como código morto.
- Não há testes automatizados pra camada de I/O (renderização Streamlit, seleção de Player, card, matriz, radar, toggles) — verificação manual apenas, mesmo padrão já adotado no restante do projeto.

## Out of Scope

- Ingestão de idade, nacionalidade, pé preferido e foto real do Player — os campos existem no domínio, mas ficam vazios/"-" até uma spec futura de ingestão.
- Filtros de Team e League na População de Comparação desta página — fica só Position Group + Minutes Floor por enquanto; mais filtros podem ser pedidos numa spec futura.
- Exibição de Quartil nesta página — o termo já existe no glossário, reservado pra uma spec futura; esta spec usa Tercil.
- Reconstrução de Scout Comparison, Insight ou exportação de Reports em PDF em qualquer formato — ficam totalmente fora do produto até uma spec nova decidir trazê-los de volta (ver ADR 0003).
- Qualquer mudança na página Overview.
- Legenda textual explicando as cores do Tercil, escolha exata do avatar placeholder, detalhes de tooltip do radar — decisões de visual deixadas pra fase de implementação/design.

## Further Notes

- Vocabulário do domínio usado nesta spec: Player, Position, Position Group, Statistic, Metric, População de Comparação, Tercil, Minutes Floor — todos definidos em `CONTEXT.md`, atualizado na mesma sessão de grilling/domain-modeling que originou esta spec.
- Esta spec resulta de uma sessão de grill (design-tree interview) seguida de domain-modeling com o usuário; ver `docs/adr/0003-drop-scout-comparison-on-workspace-rebuild.md` pra contexto completo da decisão de remoção.
- `CONTEXT.md` também documenta `Quartil` como conceito reservado, distinto do `Tercil` usado aqui — não confundir os dois na implementação.
- A extensão do `Player` com campos biográficos opcionais é compatível com todas as fixtures/testes existentes, já que os novos campos ficam vazios por padrão — nenhuma fixture existente precisa mudar por causa disso.
