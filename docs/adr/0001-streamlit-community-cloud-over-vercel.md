# Host the Streamlit dashboard on Streamlit Community Cloud, not Vercel

O plano inicial era hospedar tudo na Vercel, por ser a opção padrão para projetos pessoais. Mas Vercel hospeda funções serverless (stateless, de curta duração), enquanto o Streamlit exige um servidor Python de longa duração com WebSocket — os dois modelos são incompatíveis. Decidimos hospedar o dashboard no Streamlit Community Cloud (gratuito e feito sob medida para esse caso de uso) e remover a Vercel da arquitetura. O Supabase continua sendo o banco de dados independente de onde o dashboard roda.
