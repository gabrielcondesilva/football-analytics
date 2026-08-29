# Liga atual do Team, independente da League de origem das Statistics

Status: ready-for-agent

## Problem Statement

Hoje a Liga exibida de um Player é inferida indiretamente de onde suas Statistics vieram (Snapshot → Season → League) — o Team em si não guarda League nenhuma. Isso quebra assim que um Player troca de clube entre Leagues que já ingerimos: seu elenco atual (FotMob) já reflete o Team novo, mas a ingestão só salva um Player quando acha, na League sendo ingerida, uma entrada de Statistics pra ele na Season configurada. Um Player recém-transferido não tem essa entrada ainda (suas Statistics da Season mais recente pertencem à League antiga), então ele é pulado inteiramente — não aparece nem pela League antiga (já saiu do elenco de lá) nem pela nova. Casos reais observados: Marc Cucurella (Chelsea → Real Madrid) e Axel Witsel (La Liga → Nice) sumiram da base por esse motivo, mesmo tendo dados completos disponíveis no FotMob.

## Solution

Desacoplar "Liga atual de um Player" (um fato do seu Team, sempre o elenco mais recente ingerido) de "League de onde vieram as Statistics exibidas" (um fato da Season em que elas foram produzidas). Ao ingerir uma League e encontrar, no elenco atual, um Player sem entrada de Statistics nessa League/Season, a ingestão procura entre as outras competições da mesma Season do Player (o payload do FotMob já lista o nome de cada uma) por alguma que bata com uma League que já rastreamos; se achar, salva essas Statistics na League/Season de onde elas realmente vieram, enquanto Team/Liga atual do Player sempre refletem a League sendo ingerida agora. Se não achar nenhuma correspondência conhecida, o Player ainda é salvo com Team/Liga atuais corretos, só sem Statistics por enquanto. Na leitura, a Liga usada para exibir/filtrar um Player passa a vir do seu Team (não mais das Statistics), e um aviso discreto sinaliza quando as Statistics mostradas vieram de uma League diferente da Liga atual. Um passe corretivo roda logo após a implementação para recuperar imediatamente Players já perdidos nas 3 Leagues ingeridas até aqui.

## User Stories

1. Como usuário do dashboard, quero que um Player que trocou de Team continue aparecendo na base com o Team e a Liga atuais, pra não perder o jogador de vista só porque ele foi transferido.
2. Como usuário do dashboard, quero que o filtro de Liga na Visão Geral reflita o Team atual do Player, não a League de onde vieram as Statistics exibidas, pra que "filtrar por La Liga" realmente signifique "jogadores que hoje jogam no La Liga".
3. Como usuário do dashboard, quero ver as Statistics mais recentes disponíveis de um Player mesmo que ele tenha acabado de trocar de Team/League, pra não perder o histórico dele só porque ainda não tem números na Liga nova.
4. Como usuário do dashboard, quero que essas Statistics "emprestadas" de outra League fiquem corretamente associadas, no banco, à Season/League de onde realmente vieram, pra que o dado nunca minta sobre sua própria origem.
5. Como usuário do dashboard, quero um aviso discreto quando as Statistics mostradas de um Player vieram de uma League diferente da sua Liga atual, pra não interpretar por engano um número de uma League como se fosse de outra.
6. Como usuário do dashboard, quero que esse aviso não atrapalhe a leitura do card/linha do Player no leaderboard quando não se aplica (Statistics já são da Liga atual), pra manter o visual limpo no caso comum.
7. Como usuário do dashboard, quero que um Player cuja League de origem não seja nenhuma das que já rastreamos ainda apareça com Team/Liga atuais corretos, mesmo sem nenhuma Statistic disponível, pra que ele não simplesmente desapareça da base.
8. Como usuário do dashboard, quero que um Player sem nenhuma Statistic disponível simplesmente não apareça em nenhum leaderboard/Top 10 por Metric (sem erro, sem linha vazia), pra manter os rankings limpos.
9. Como usuário do dashboard, quero que a Análise de Jogadores continue funcionando normalmente com esses Players, já que sua População de Comparação não filtra por Team/League, pra não introduzir nenhuma regressão nessa página.
10. Como usuário do dashboard, quero que, quando eu não filtrar por nenhuma Liga na Visão Geral, os Players com Statistics "emprestadas" continuem aparecendo normalmente nos leaderboards, pra não perder cobertura quando não estou filtrando por Liga.
11. Como usuário do dashboard, quero que os dados hoje perdidos por esse motivo (ex.: Cucurella, Witsel) sejam recuperados assim que essa correção existir, pra que a base fique completa sem eu precisar pedir de novo.
12. Como mantenedor do projeto, quero que a lógica de achar a entrada de Statistics de fallback seja uma função pura testável sem rede nem banco, reaproveitando o padrão de Seam A (normalização) já estabelecido, pra manter a cobertura de teste consistente com o resto do projeto.
13. Como mantenedor do projeto, quero que essa busca de fallback nunca tente descobrir/buscar uma League nova que ainda não rastreamos, pra não expandir o escopo de uma ingestão de uma League pra outra sem controle.
14. Como mantenedor do projeto, quero uma regra determinística de desempate para o caso raro de um Player ter entradas de mais de uma League conhecida na mesma Season (ex.: transferência no meio da temporada), pra que o comportamento seja previsível mesmo sem um filtro de Season ainda existir.
15. Como mantenedor do projeto, quero que a ingestão continue idempotente/reentrante mesmo com a lógica de fallback nova, pra manter a mesma garantia que a ingestão já tem hoje.
16. Como mantenedor do projeto, quero que a mudança de schema (League atual do Team) seja aditiva e não quebre nenhuma leitura existente enquanto o backfill não rodou, pra fazer o deploy sem downtime.
17. Como mantenedor do projeto, quero que Teams já existentes no banco (das 3 Leagues já ingeridas) recebam sua Liga atual retroativamente, pra que a mudança de schema não deixe dado antigo sem Liga.
18. Como mantenedor do projeto, quero rodar um passe corretivo nas 3 Leagues já ingeridas logo depois da mudança, pra capturar imediatamente os Players que hoje estão fora da base por causa desse gap.
19. Como mantenedor do projeto, quero que esse passe corretivo seja idempotente, pra poder repetir com segurança se algo falhar no meio.
20. Como mantenedor do projeto, quero que o modelo de dados continue compatível com um futuro filtro de Season por Player (múltiplas League/Season de Statistics simultâneas pro mesmo Player), pra não precisar redesenhar o schema quando essa feature futura for construída.

## Implementation Decisions

- **Team (domínio)**: o dataclass de Team em si permanece mínimo (fotmob_id, name) — League atual não vira campo do domínio, é uma responsabilidade de escrita/leitura da camada de persistência (ver abaixo), coerente com Team continuar "referência mínima" (CONTEXT.md).
- **Schema**: `teams` ganha uma coluna de referência à League atual (`league_id`, aditiva/nullable, idempotente como as demais colunas já adicionadas depois do MVP). Nenhuma mudança em `players`, `statistics`, `seasons` ou `snapshots` — o encadeamento Statistic → Snapshot → Season → League continua exatamente como está (ADR-0002); só o Team ganha esse fato novo.
- **Módulo de Normalização (Seam A, estendido)**: nova função pura irmã de `find_entry_id`, que recebe o payload de `playerData` de um Player, o `season_name` alvo, e o conjunto de `tournamentId`s das Leagues já cadastradas (obtido pela camada de persistência no início da ingestão); devolve qual League + entryId usar como fallback (a primeira competição da Season do Player, na ordem em que o próprio FotMob a lista, cujo `tournamentId` bate com uma League conhecida), ou nada se nenhuma bater. `find_entry_id` em si não muda — continua sendo o match exato pela League sendo ingerida.
- **Orquestração da ingestão**: para cada Player do elenco atual de uma League, tenta primeiro o match exato de hoje (`find_entry_id` contra a League sendo ingerida). Se não achar, tenta o fallback acima. Se o fallback achar uma League diferente, as Statistics resultantes são gravadas na Season/Snapshot dessa OUTRA League (reaproveitando o Snapshot mais recente já existente pra ela, sem criar um Snapshot novo só pra um Player) — nunca na Season da League sendo ingerida agora. Time e dados biográficos do Player são sempre atualizados para o elenco/League sendo ingerida agora, independente de onde as Statistics vieram. Se nem o match exato nem o fallback acharem nada, o Player ainda é salvo (Team/bio atualizados), só sem Statistics — deixa de ser pulado inteiramente como é hoje.
- **Persistência**: a escrita de Team passa a incluir sua League atual (a League sendo ingerida no momento, sempre). Uma nova capacidade de reaproveitar o Snapshot mais recente já existente de uma League/Season (em vez de sempre criar um novo) é usada apenas para o caso de fallback descrito acima — a League sendo ativamente ingerida neste run continua sempre ganhando um Snapshot novo, como hoje.
- **Leitura (camada usada pelo dashboard)**: a Liga exibida/filtrável de cada Player passa a vir da League atual do seu Team, não mais de qual Snapshot suas Statistics vieram. A seleção de quais Statistics mostrar continua vindo do Snapshot mais recente de cada League (já abrange todas as Leagues simultaneamente hoje), então uma entrada "emprestada" salva na Season/League de origem correta já é incluída sem mudança adicional nessa parte.
- **Dashboard (Visão Geral)**: quando a League de onde vieram as Statistics exibidas de um Player difere da Liga atual do seu Team, um aviso discreto aparece junto da linha desse Player no leaderboard. Redação exata, posicionamento e estilo ficam a cargo do subagent `streamlit-dashboard-designer` na fase de implementação (CLAUDE.md) — esta spec só define que o aviso deve existir e ser discreto (não deve competir visualmente com o conteúdo principal da linha).
- **Backfill (rodar uma vez, logo após a implementação)**: (a) preencher a League atual de todo Team já existente no banco, cruzando com as listas de elenco das 3 Leagues já ingeridas; (b) rodar de novo a ingestão das 3 Leagues já feitas, agora com a lógica de fallback, pra capturar os Players hoje perdidos (Cucurella, Witsel e qualquer outro caso igual).

## Testing Decisions

- Um bom teste aqui valida apenas comportamento externo (dado um payload, o resultado esperado), sem depender de como a busca é implementada por dentro — mesmo critério já usado no resto do projeto.
- **Seam A — Normalização** (estendido): a nova função de fallback é testada com fixtures no mesmo estilo de `find_entry_id` (payload de `playerData` real salvo em disco). Casos: (1) encontra a entrada certa quando o Player tem múltiplas competições na Season e uma delas bate com uma League conhecida; (2) não encontra nada quando só existem competições que não são Leagues conhecidas (ex.: só Copas); (3) mesmo comportamento nulo-seguro já estabelecido pra payload/Season ausente; (4) desempate determinístico quando mais de uma competição da mesma Season bate com uma League conhecida (usa a ordem em que o FotMob lista as competições).
- `find_entry_id` não muda — nenhum teste existente dele é alterado.
- Persistência, orquestração da ingestão e o aviso no dashboard não têm teste automatizado — camada de I/O, mesmo padrão já adotado no resto do projeto (verificação manual, incluindo rodar o passe corretivo de verdade contra o FotMob/Supabase e conferir os casos conhecidos).

## Out of Scope

- Qualquer UI de seleção de Season pelo usuário — reconhecido como o próximo passo natural desta mudança, mas não faz parte desta spec.
- Buscar/ingerir automaticamente uma League nunca rastreada só porque um Player veio de lá — fica descoberto (Team/Liga atuais corretos, sem Statistics) até uma spec futura decidir trazer essa League.
- Qualquer refinamento do desempate entre duas Leagues conhecidas na mesma Season além da regra determinística simples descrita (ordem de listagem do FotMob) — tratamento mais rico fica pra quando o filtro de Season existir.
- Estatísticas de Team (fora de escopo desde a spec original do MVP).
- Qualquer mudança de comportamento na Análise de Jogadores além de continuar funcionando sem regressão.
- Migração de dado histórico além do backfill de League atual do Team e do passe corretivo pontual nas 3 Leagues já ingeridas.

## Further Notes

- Vocabulário do domínio usado nesta spec: League, Season, Team, Player, Statistic, Snapshot — todos em `CONTEXT.md`, atualizado na mesma sessão de grilling/domain-modeling que originou esta spec (Team ganhou a definição de Liga atual; Statistic passou a esclarecer que sua League pode divergir da Liga atual do Team do Player).
- Ver `docs/adr/0004-team-carries-its-own-current-league.md` para o registro da decisão de desacoplar Liga atual (Team) de League de origem das Statistics (Season) — ler antes de implementar.
- Esta spec nasceu de um caso real observado em produção: Marc Cucurella (Chelsea → Real Madrid) e Axel Witsel (La Liga → Nice) ficaram fora da base inteira porque a janela de transferência coincidiu com as datas de ingestão de cada League — os dois casos reais servem de critério informal de "funcionou" para o passe corretivo.
- O payload de `playerData` do FotMob já inclui o nome de cada competição por Season, o que deixa aberta (sem fazer parte desta spec) uma melhoria futura de mostrar o nome da competição de origem no aviso visual, não só a League.
