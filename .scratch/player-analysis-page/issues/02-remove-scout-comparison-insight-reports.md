# 02: Remover Scout Comparison, leaderboard geral, Insight e Reports em PDF

**What to build:** Scout Comparison, o leaderboard geral por Metric, os Insights automáticos por regra e a exportação de Reports em PDF (perfil individual e comparação) deixam de existir no app — código, testes e módulos órfãos removidos por completo, conforme ADR 0003.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Nenhuma seção de Scout Comparison, leaderboard geral ou Insight aparece mais em nenhuma tela do app.
- [x] Nenhum botão de download de PDF relacionado a essas duas features continua presente.
- [x] Funções de análise (Scout Comparison, geração de Insight, incluindo o tipo `Insight`) e os módulos de report associados (incluindo o módulo de montagem de PDF compartilhado, que fica órfão) são removidos do código.
- [x] Testes que cobriam esse código são removidos junto; a suíte de testes passa sem eles.
