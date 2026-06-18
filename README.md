# Extrator de Nota Fiscal — N3 Etapa 3 (Agente Inteligente RAG)

Sistema para extração de dados de notas fiscais em PDF, persistência em PostgreSQL e
consulta inteligente via Agente RAG (Retrieval-Augmented Generation) híbrido.

## Estrutura do Projeto

```
projeto/
├── main.py              # Backend FastAPI (extração, persistência, RAG)
├── rag.py                # Módulo do Agente Inteligente (RAG Simples + Embeddings)
├── requirements.txt
├── .env.example
├── Dockerfile            # Build do backend
├── docker-compose.yml    # Postgres + Backend
├── database/
│   └── schema.sql
├── App.jsx               # Frontend React
├── App.css
├── main.jsx
├── index.html
├── package.json
└── vite.config.js
```

---

## Pré-requisitos

### 1. Python 3.10+
### 2. Node.js 18+
### 3. Docker Desktop com Compose
### 4. Conta da API Groq ou ambiente configurado para usar Groq

---

## Configuração e Execução

### Backend

```bash
cd "C:\Users\Juan4\OneDrive\Área de Trabalho\projeto"

# Ativar ambiente virtual
& ".\.venv\Scripts\Activate.ps1"

# Instalar dependências (se ainda não instalou)
python -m pip install -r requirements.txt
```

Copie o arquivo de exemplo e ajuste as variáveis de ambiente:

```bash
copy .env.example .env
```

Edite `.env` com a sua chave Groq e URL do banco:

```ini
GROQ_API_KEY=seu_token_groq_aqui
DATABASE_URL=postgresql://financeiro:financeiro123@localhost:5432/financeiro
```

### Banco de Dados

```bash
docker compose up -d
```

### Iniciar o backend

```bash
& ".\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

O backend estará disponível em: http://127.0.0.1:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend estará disponível em: http://127.0.0.1:5173

---

## Como Usar

1. Abra http://127.0.0.1:5173 no navegador
2. Clique em **Escolher arquivo** e selecione uma nota fiscal em PDF
3. Clique em **EXTRAIR DADOS**
4. Clique em **Salvar no banco** para persistir a nota fiscal no PostgreSQL
5. Clique em **Ver contas salvas** para visualizar os registros já salvos

---

## Endpoints da API

| Método | Rota             | Descrição                                                                 |
|--------|------------------|---------------------------------------------------------------------------|
| POST   | /extrair         | Envia PDF e retorna JSON extraído                                          |
| POST   | /salvar          | Persiste os dados extraídos no banco de dados                             |
| GET    | /contas-a-pagar  | Lista as contas a pagar salvas no banco                                   |
| GET    | /db-status       | Verifica disponibilidade do banco de dados                               |
| GET    | /test            | Verifica a conexão com a API Groq e lista os modelos disponíveis          |
| GET    | /health          | Status do servidor e disponibilidade da IA                               |
| POST   | /perguntar       | Agente RAG: responde perguntas em linguagem natural sobre o banco        |
| POST   | /perguntar/reindexar | Reconstrói o índice de embeddings (RAG Embeddings)                   |

---

## Dados Extraídos (JSON)

```json
{
  "fornecedor": {
    "razaoSocial": "string",
    "fantasia": "string | null",
    "cnpj": "string"
  },
  "faturado": {
    "nomeCompleto": "string",
    "cpf": "string | null"
  },
  "numeroNotaFiscal": "string",
  "serieNotaFiscal": "string | null",
  "dataEmissao": "YYYY-MM-DD",
  "descricaoProdutos": "string",
  "parcelas": [
    { "numero": 1, "dataVencimento": "YYYY-MM-DD", "valor": 0.00 }
  ],
  "valorTotal": 0.00,
  "classificacoesDespesa": ["CATEGORIA"]
}
```

## Categorias de Despesa

- INSUMOS AGRÍCOLAS
- MANUTENÇÃO E OPERAÇÃO
- RECURSOS HUMANOS
- SERVIÇOS OPERACIONAIS
- INFRAESTRUTURA E UTILIDADES
- ADMINISTRATIVAS
- SEGUROS E PROTEÇÃO
- IMPOSTOS E TAXAS
- INVESTIMENTOS

---

## Etapa 3 — Agente Inteligente (RAG)

Foi adicionada uma tela **Assistente IA** onde o usuário digita perguntas em
linguagem natural sobre o banco de dados financeiro, e recebe uma resposta
elaborada por LLM (Groq/Llama).

O agente implementa duas estratégias de RAG (módulo `rag.py`):

### 1. RAG Simples (Text-to-SQL)
- O LLM recebe a pergunta + um resumo do schema do banco.
- Gera uma consulta SQL **somente leitura** (apenas `SELECT`, validada contra
  comandos perigosos como `INSERT`, `DROP`, `;`, etc.).
- A query é executada no PostgreSQL.
- O LLM recebe os dados retornados e elabora a resposta final em português.

### 2. RAG Embeddings (busca semântica)
- Os registros de `contas_a_pagar` e `contas_a_receber` são convertidos em
  texto descritivo e transformados em vetores usando **sentence-transformers**
  (modelo `all-MiniLM-L6-v2`, executa localmente, sem custo de API).
- Os vetores ficam em cache (`embeddings_cache.pkl`).
- A pergunta do usuário é vetorizada e comparada por similaridade de cosseno.
- Os registros mais relevantes são enviados ao LLM, que elabora a resposta.

### Modo "Híbrido" (padrão)
Tenta primeiro o RAG Simples (SQL). Se a geração ou execução da SQL falhar,
cai automaticamente para o RAG Embeddings.

### Novos Endpoints

| Método | Rota                   | Descrição                                              |
|--------|------------------------|---------------------------------------------------------|
| POST   | /perguntar             | `{ "pergunta": "...", "modo": "auto\|sql\|embeddings" }` |
| POST   | /perguntar/reindexar   | Reconstrói o índice de embeddings a partir do banco     |

### Reindexação
Após salvar novas notas fiscais, clique em **Reindexar** na tela do
Assistente para que o RAG Embeddings considere os novos registros. O RAG SQL
sempre consulta o banco em tempo real, não precisa de reindexação.

---

## Executando com Docker (recomendado)

O `docker-compose.yml` sobe o PostgreSQL **e** o backend FastAPI.

```bash
# 1. Configure sua chave Groq
cp .env.example .env
# edite o .env e preencha GROQ_API_KEY

# 2. Suba os containers
docker-compose up -d --build

# 3. Acompanhe os logs (1ª execução baixa o modelo de embeddings, pode levar ~1 min)
docker-compose logs -f backend
```

Backend: http://localhost:8000
Banco: localhost:5432

Em seguida, rode o frontend normalmente:

```bash
npm install
npm run dev
```

## Deploy

### Frontend (Vercel)

- Configure o projeto no Vercel apontando para este repositório.
- Defina a variável de ambiente `VITE_API_URL` para a URL do backend Render.
- Uses these settings:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### Backend (Render)

- Use o `Dockerfile` existente para o serviço Python.
- Defina as variáveis de ambiente necessárias: `GROQ_API_KEY`, `DATABASE_URL`, `APP_USERNAME`, `APP_PASSWORD`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `EMBEDDINGS_CACHE_PATH`.
- Configure o banco PostgreSQL no Render e use a URL gerada em `DATABASE_URL`.

### Backend alternativo (PythonAnywhere)

- PythonAnywhere pode ser usado apenas se suportar ASGI/uvicorn no plano ou em beta.
- A aplicação FastAPI está pronta para rodar como `uvicorn main:app --host 0.0.0.0 --port 8000`.
- Use `ALLOWED_ORIGINS` para permitir a URL do frontend.

Frontend: http://localhost:5173

---

## Exemplos de Perguntas para o Assistente

- "Qual fornecedor tem o maior valor total em contas a pagar?"
- "Quais parcelas estão vencidas?"
- "Quanto eu gastei com Manutenção e Operação este ano?"
- "Liste as últimas 5 notas fiscais recebidas"
- "Existe alguma conta a receber do cliente X?"

