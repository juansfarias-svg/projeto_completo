# Guia de Deploy

## 1. Backend no Render

### 1.1. Preparar o repositório
- Confirme que `Dockerfile`, `requirements.txt`, `render.yaml` e `main.py` estão no repositório.
- Garanta que o backend roda localmente com: `python main.py`.

### 1.2. Criar banco PostgreSQL no Render
1. Acesse https://dashboard.render.com
2. Clique em **New +** → **PostgreSQL**
3. Nome: `extrator-nf-db`
4. Plano: `free`
5. Copie a **Connection String** gerada.

### 1.3. Criar serviço web no Render
1. Clique em **New +** → **Web Service**
2. Selecione o repositório do projeto
3. Runtime: `Docker`
4. Dockerfile path: `./Dockerfile`
5. Em Environment, adicione as variáveis:
   - `GROQ_API_KEY` = sua chave Groq
   - `DATABASE_URL` = conexão do PostgreSQL do Render
   - `APP_USERNAME` = admin
   - `APP_PASSWORD` = senha forte
   - `SECRET_KEY` = valor longo aleatório
   - `ALLOWED_ORIGINS` = URL do frontend Vercel (depois)
   - `EMBEDDINGS_CACHE_PATH` = `/app/data/embeddings_cache.pkl`
6. Crie o serviço.

### 1.4. Ajustes pós-deploy
- Atualize `ALLOWED_ORIGINS` com a URL do frontend Vercel.
- Se o backend usar `DATABASE_URL` do Render, o build irá conectar ao banco.

## 2. Frontend no Vercel

### 2.1. Criar projeto Vercel
1. Acesse https://vercel.com
2. Clique em **New Project**
3. Selecione o repositório do projeto
4. Framework Preset: `Vite`
5. Em Environment Variables, defina:
   - `VITE_API_URL` = `https://SEU-BACKEND.onrender.com`
6. Deploy.

### 2.2. Verificar deploy
- O frontend deve estar disponível em `https://seu-projeto.vercel.app`
- A aplicação deve carregar e fazer login usando o backend.

## 3. PythonAnywhere (opcional)

### 3.1. Limitação
- PythonAnywhere suporta WSGI nativamente.
- FastAPI é ASGI/uvicorn, então esse deploy só vale se o plano oferecer suporte ASGI.

### 3.2. Configuração sugerida
1. Crie um virtualenv Python 3.11.
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Use comando de inicialização semelhante a:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
4. Garanta variáveis de ambiente iguais ao Render.

## 4. Variáveis de Ambiente

No backend (`Render`, `PythonAnywhere`):
```ini
GROQ_API_KEY=seu_token_groq_aqui
DATABASE_URL=postgresql://usuario:senha@host:porta/banco
APP_USERNAME=admin
APP_PASSWORD=senha_forte
SECRET_KEY=uma_chave_longa_e_secreta
ALLOWED_ORIGINS=https://seu-frontend.vercel.app
EMBEDDINGS_CACHE_PATH=/app/data/embeddings_cache.pkl
```

No frontend (`Vercel`):
```ini
VITE_API_URL=https://SEU-BACKEND.onrender.com
```

## 5. Testes após deploy
- Acesse o frontend publicado.
- Faça login com `admin` / sua senha.
- Verifique se a aplicação de CRUD carrega corretamente.
- Verifique se o backend responde em: `https://SEU-BACKEND.onrender.com/health`
