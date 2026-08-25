# Player Analytics MVP — Premier League 2025/26

Status: ready-for-agent

## Problem Statement

Não existe hoje uma forma prática de analisar e comparar jogadores de futebol usando dados estatísticos completos: quando é preciso avaliar um Player em detalhe, comparar candidatos parecidos entre si (por exemplo, para achar um substituto), ou preparar uma análise pra compartilhar com um treinador, os dados relevantes estão espalhados, sem estrutura de comparação, e não há como gerar um documento pronto pra entregar.

## Solution

Construir uma base de dados de Statistics de Players da Premier League (Season 2025/26), extraída do FotMob, com um dashboard que permite explorar, filtrar e comparar Players por Metrics escolhidas livremente, encontrar Players parecidos entre si (Scout Comparison) restrito por Position Group e Minutes Floor, ver Insights automáticos baseados em percentil, e exportar tudo isso como um Report em PDF pronto pra enviar a um treinador.

## User Stories

1. Como usuário do dashboard, quero que os dados de todos os Players da Premier League Season 2025/26 estejam disponíveis, pra poder analisar a temporada inteira sem lacunas.
2. Como usuário do dashboard, quero que sejam capturadas todas as categorias de Statistic disponíveis no perfil de cada Player no FotMob (incluindo o conjunto específico de goleiros), pra não ficar limitado a um subconjunto arbitrário de dados.
3. Como usuário do dashboard, quero que os dados sejam agregados por Season (não jogo-a-jogo), pra que a comparação entre Players reflita o desempenho da temporada inteira.
4. Como usuário do dashboard, quero ver o Team ao qual cada Player pertence, pra poder filtrar ou identificar jogadores por clube.
5. Como usuário do dashboard, quero ver a(s) Position(s) de cada Player, pra entender em que posições ele pode atuar.
6. Como usuário do dashboard, quero uma sidebar onde escolho livremente quais Metrics usar pra comparar Players e Teams, pra poder focar a análise no que importa pra cada avaliação.
7. Como usuário do dashboard, quero que a sidebar ofereça tanto Statistics brutas quanto Metrics derivadas (por-90, percentil), pra comparar jogadores de forma justa independente do tempo jogado.
8. Como usuário do dashboard, quero visualizar essas Metrics em gráficos modernos e interativos, pra identificar padrões rapidamente.
9. Como usuário do dashboard, quero filtrar Players por Position Group, pra comparar apenas jogadores que atuam em papéis semelhantes.
10. Como usuário do dashboard, quero aplicar um Minutes Floor ajustável, pra excluir Players com amostra pequena de minutos jogados das comparações e rankings.
11. Como usuário do dashboard, quero desligar o filtro de Position Group quando quiser, pra explorar comparações fora do padrão restrito.
12. Como usuário do dashboard, quero pedir uma Scout Comparison a partir de um Player de referência, pra encontrar outros Players parecidos nas Metrics que escolhi.
13. Como usuário do dashboard, quero que a Scout Comparison trate todas as Metrics selecionadas com peso igual, pra ter um resultado previsível e fácil de entender.
14. Como usuário do dashboard, quero que a Scout Comparison já venha restrita ao mesmo Position Group do Player de referência por padrão, pra que os resultados sejam realistas como opções de substituição.
15. Como usuário do dashboard, quero ver Insights automáticos baseados em percentil sobre um Player (ex: "top 10% da liga em finalizações"), pra identificar rapidamente pontos fortes e fracos sem precisar interpretar números crus.
16. Como usuário do dashboard, quero exportar um Report em PDF com o perfil de um único Player, pra enviar essa análise a um treinador.
17. Como usuário do dashboard, quero exportar um Report em PDF com uma Scout Comparison entre Players, pra apresentar candidatos a substituição de forma pronta pra decisão.
18. Como usuário do dashboard, quero que o Report em PDF inclua os gráficos exibidos no dashboard como imagens, pra que o documento seja visualmente equivalente à análise feita na tela.
19. Como usuário do dashboard, quero acessar a aplicação sem precisar de login, pra que o MVP fique simples de usar e compartilhar por link.
20. Como usuário do dashboard, quero que os dados fiquem armazenados com uma data de captura (Snapshot), pra que no futuro seja possível reprocessar a mesma Season sem perder o histórico.
21. Como mantenedor do projeto, quero que o processo de ingestão normalize a resposta bruta do FotMob em registros de domínio (Player, Statistic, Team, Position) antes de gravar no banco, pra que o resto do sistema nunca dependa do formato bruto da API externa.
22. Como mantenedor do projeto, quero que o cálculo de Metrics derivadas (por-90, percentil) e a lógica de Scout Comparison/Insight sejam funções puras separadas da camada de scraping e da camada de UI, pra que essa lógica seja testável sem rede, sem banco e sem Streamlit.

## Implementation Decisions

- **Módulo de Ingestão (scraper + normalizador)**: chama as rotas JSON internas do FotMob para obter a lista de Players da League/Season configurada e, para cada Player, todas as categorias de Statistic do seu perfil (incluindo o conjunto específico de goleiros). Normaliza a resposta bruta em registros de domínio: Player, Team (referência mínima: nome, escudo), Position(s) do Player, e Statistics com seus valores brutos.
- **Persistência (Supabase/Postgres)**: cada execução de ingestão grava um novo Snapshot datado (`scraped_at`) associado à Season, em vez de sobrescrever valores existentes (ADR-0002). As Statistics de um Player em um dado Snapshot ficam associadas a esse Snapshot. Team é uma tabela mínima de referência (nome, escudo), sem Statistics próprias nesta fase.
- **Módulo de Análise**: conjunto de funções puras que recebem registros normalizados de um Snapshot e calculam: (a) Metrics derivadas — por-90 (usando a Statistic de minutos jogados) e percentil dentro do Position Group na Season; (b) aplicação do Minutes Floor e do filtro de Position Group; (c) Scout Comparison — ranking de Players por similaridade nas Metrics selecionadas pelo usuário, com peso igual entre elas; (d) Insight — flags baseadas em limiares de percentil sobre as Metrics de um Player, sem uso de LLM.
- **Dashboard (Streamlit)**: sidebar para selecionar Metrics (brutas ou derivadas), Position Group, Minutes Floor e Team; visualizações com Plotly (interativo no app); tela de perfil de Player, tela de comparação/Scout, e leaderboards da League/Season. Hospedado no Streamlit Community Cloud, não na Vercel (ADR-0001). Sem autenticação nesta fase — acesso aberto.
- **Módulo de Report**: gera PDF a partir de um perfil de Player ou de uma Scout Comparison, reaproveitando os mesmos componentes de dashboard; gráficos Plotly são exportados como imagem estática (via kaleido) para incorporar no PDF.
- **Escopo de dados desta spec**: apenas League = Premier League, Season = 2025/26 (temporada já encerrada — carga histórica, não ao vivo). O schema é desenhado para comportar múltiplas Leagues/Seasons e Snapshots futuros, mas nenhuma outra League/Season é ingerida nesta spec.

## Testing Decisions

- Um bom teste aqui valida apenas comportamento externo — dado um input, o output esperado — sem depender de como a normalização ou o cálculo são implementados por dentro.
- **Seam A — Normalização** (`raw FotMob JSON → registros de domínio normalizados`): testado com fixtures de respostas reais do FotMob salvas em disco (por categoria de Statistic, incluindo o formato específico de goleiro), sem chamadas de rede. Assert sobre os registros normalizados de Player, Team, Position e Statistic resultantes.
- **Seam B — Análise** (`registros de domínio + Metrics selecionadas + filtros → Scout Comparison / Insight`): testado com conjuntos construídos de Players e Statistics normalizadas (fixtures em código, não FotMob real). Assert sobre: cálculo de Metrics derivadas (por-90, percentil), exclusão correta de Players abaixo do Minutes Floor, restrição por Position Group, ordenação da Scout Comparison com peso igual entre Metrics, e geração correta dos Insights por limiar de percentil.
- Não há testes automatizados para a camada de I/O nesta fase (chamadas HTTP ao FotMob, upsert no Supabase, renderização Streamlit, geração de PDF) — verificação manual apenas.
- Não há prior art no repositório (projeto greenfield) — estes dois seams estabelecem o padrão de teste baseado em fixtures e funções puras a ser seguido pelas próximas specs.

## Out of Scope

- Estatísticas de Team (fica pra uma fase futura — Team nesta spec é só referência mínima do Player).
- Qualquer League ou Season além de Premier League 2025/26.
- Estatísticas jogo-a-jogo/log de partidas individuais (apenas agregados de Season).
- Re-scraping periódico/agendado automático (o schema com Snapshot suporta isso, mas o agendador não é construído nesta spec — a ingestão desta spec roda uma única vez, manualmente).
- Autenticação/login no dashboard.
- Insights gerados por LLM (apenas regras baseadas em percentil).
- Peso diferenciado entre Metrics na Scout Comparison (peso igual apenas, nesta spec).

## Further Notes

- O FotMob não tem API oficial documentada; as rotas JSON usadas pelo módulo de Ingestão são internas e não garantidas — o módulo deve ser construído de forma que mudanças de formato na resposta quebrem a normalização de forma visível (não silenciosa), facilitando manutenção futura.
- Respeitar ADR-0001 (hospedagem no Streamlit Community Cloud, não Vercel) e ADR-0002 (Statistics gravadas como Snapshots datados desde o início) ao implementar esta spec.
- Vocabulário do domínio usado nesta spec está definido em `CONTEXT.md`: League, Season, Team, Player, Position, Position Group, Statistic, Metric, Snapshot, Minutes Floor, Scout Comparison, Insight, Report.
