# 03: Shell multipage — Overview vazia + dashboard atual relocado

**What to build:** Reestruturar o dashboard em navegação multipage nativa do Streamlit, com a Overview (vazia por enquanto) como página inicial, e o dashboard atual relocado pra uma segunda página sem nenhuma mudança de comportamento.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] O app usa `st.navigation` com duas páginas.
- [ ] Overview é a página inicial/padrão e mostra apenas o estado vazio "Selecione uma métrica de desempenho" — sem filtros de resultado nem tabelas nesta etapa.
- [ ] A segunda página contém o conteúdo do `app.py` atual (filtros gerais, leaderboards com gráfico, Player Profile, Insights, Scout Comparison, downloads de PDF) movido sem nenhuma mudança funcional.
- [ ] Navegar entre as duas páginas funciona, e a segunda página se comporta exatamente como o dashboard atual se comporta hoje.
