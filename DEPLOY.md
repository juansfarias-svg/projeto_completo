# Guia de Deploy — Concluído ✅

## Status dos Serviços

| Serviço | Tecnologia | URL | Status |
|---------|-----------|-----|--------|
| **Backend** | Python (FastAPI) no Render | `https://projeto-completo-1.onrender.com` | ✅ **Online** |
| **Frontend** | React (Vite) no Vercel | `https://projeto-completo-cyan.vercel.app` | ✅ **Online** |
| **Banco** | PostgreSQL no Render | `dpg-d8q85ubeo5us73emdla0-a` | ✅ **Online** |
| **PythonAnywhere** | Alternativo (ASGI) | — | ✅ Documentado |

## URLs de Acesso

- **Frontend**: https://projeto-completo-cyan.vercel.app
- **Backend**: https://projeto-completo-1.onrender.com
- **Health Check**: https://projeto-completo-1.onrender.com/health
- **DB Status**: https://projeto-completo-1.onrender.com/db-status

## Variáveis de Ambiente Configuradas

### Backend (Render)
- `GROQ_API_KEY` — Chave da API Groq (configurada)
- `DATABASE_URL` — Conexão com PostgreSQL (configurada ✅)
- `ALLOWED_ORIGINS` — `https://projeto-completo-cyan.vercel.app`
- `EMBEDDINGS_CACHE_PATH` — `/app/data/embeddings_cache.pkl`

### Frontend (Vercel)
- `VITE_API_URL` — `https://projeto-completo-1.onrender.com` (configurada ✅)

## Como acessar o sistema

1. Acesse https://projeto-completo-cyan.vercel.app
2. Faça login com as credenciais definidas em `APP_USERNAME` e `APP_PASSWORD`
3. Use o **Extrator de NF** para processar notas fiscais
4. Veja o **Histórico** das contas registradas
5. Use o **Assistente IA** para perguntar sobre os dados
6. Gerencie **Fornecedores, Clientes, Faturados, Despesas e Receitas**

## Arquivos de Configuração

- `render.yaml` — Blueprint do Render (Docker + PostgreSQL)
- `vercel.json` — Configuração de build Vite
- `setup_database.py` — Script de setup do banco
- `config_db.py` — Script de configuração da connection string