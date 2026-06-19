# Guia de Deploy — Completo

## 1. Backend Python (FastAPI) no Render

### 1.1. Pré-requisitos
- Conta em https://render.com (GitHub login)
- Repositório GitHub: `https://github.com/juansfarias-svg/projeto_completo`

### 1.2. Criar banco PostgreSQL no Render
1. Acesse https://dashboard.render.com
2. Clique em **New +** → **PostgreSQL**
3. Nome: `extrator-nf-db`
4. Database: `financeiro`
5. User: `financeiro`
6. Plano: `Free`
7. Após criar, copie a **Connection String** (Internal ou External)

### 1.3. Criar Web Service (Docker)
1. Clique em **New +** → **Web Service**
2. Conecte o repositório `juansfarias-svg/projeto_completo`
3. **Name**: `projeto-completo`
4. **Runtime**: `Docker`
5. **Dockerfile Path**: `./Dockerfile`
6. **Plan**: `Free`
7. Adicione as Environment Variables:
   - `GROQ_API_KEY` = sua chave da API Groq
   - `DATABASE_URL` = connection string do PostgreSQL do Render (Internal)
   - `APP_USERNAME` = admin
   - `APP_PASSWORD` = senha forte (ex: Unirv@2026)
   - `SECRET_KEY` = valor aleatório longo
   - `ALLOWED_ORIGINS` = `https://projeto-completo-1.vercel.app` (URL do Vercel após deploy)
   - `EMBEDDINGS_CACHE_PATH` = `/app/data/embeddings_cache.pkl`
8. Crie também um **Disk** de 1GB montado em `/app/data`
9. Clique em **Create Web Service**

### 1.4. URL do backend
Após o deploy, o Render fornecerá uma URL como:
```
https://projeto-completo-1.onrender.com
```
Use essa URL no frontend.

---

## 2. Frontend React (Vite) no Vercel

### 2.1. Usando o plugin Vercel
```bash
# Já configurado no vercel.json
# Plugin: vercel/vercel-plugin
```

### 2.2. Deploy via GitHub
1. Acesse https://vercel.com
2. Clique em **Add New...** → **Project**
3. Importe o repositório `juansfarias-svg/projeto_completo`
4. **Framework Preset**: `Vite`
5. **Root Directory**: `./` (raiz do projeto)
6. **Build Command**: `npm run build`
7. **Output Directory**: `dist`
8. Adicione a variável de ambiente:
   - `VITE_API_URL` = `https://projeto-completo-1.onrender.com`
9. Clique em **Deploy**

### 2.3. URL do frontend
O Vercel fornecerá uma URL como:
```
https://projeto-completo-1.vercel.app
```

---

## 3. PythonAnywhere (Alternativo para backend Python)

### 3.1. Limitação
PythonAnywhere suporta WSGI nativamente. FastAPI é ASGI/uvicorn, então funciona apenas no plano **Hacker** ou superior com suporte a WebSockets/ASGI.

### 3.2. Configuração
1. Crie uma conta em https://pythonanywhere.com
2. Abra **Consoles** → **Bash**
3. Clone o repositório:
   ```bash
   git clone https://github.com/juansfarias-svg/projeto_completo.git
   ```
4. Crie virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. Configure as variáveis no **Web** → **Virtualenv**: apontar para `venv`
6. WSGI configuration file:
   ```python
   from main import app
   # Use uvicorn ou adaptar para ASGI
   ```
7. Ou use um manual start via **Always-on task**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---

## 4. Variáveis de Ambiente (Resumo)

### Backend (Render)
```ini
GROQ_API_KEY=gsk_seu_token_aqui
DATABASE_URL=postgresql://financeiro:senha@host:5432/financeiro
APP_USERNAME=admin
APP_PASSWORD=sua_senha_forte
SECRET_KEY=uma_chave_longa_e_secreta_1234567890
ALLOWED_ORIGINS=https://projeto-completo-1.vercel.app
EMBEDDINGS_CACHE_PATH=/app/data/embeddings_cache.pkl
```

### Frontend (Vercel)
```ini
VITE_API_URL=https://projeto-completo-1.onrender.com
```

---

## 5. Testes pós-deploy

### 5.1. Verificar backend
```bash
curl https://projeto-completo-1.onrender.com/health
```
Resposta esperada:
```json
{"status": "ok", "banco": true}
```

### 5.2. Verificar frontend
Acesse `https://projeto-completo-1.vercel.app`
- Login com `admin` e a senha definida
- Tela de Extração de NF deve carregar
- Histórico deve mostrar registros
- Assistente IA deve responder perguntas

### 5.3. Integração
O frontend no Vercel deve conseguir se comunicar com o backend no Render através da variável `VITE_API_URL`.