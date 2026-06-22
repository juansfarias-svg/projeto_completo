"""
Script para configurar DATABASE_URL no Web Service do Render.
1. Abre a página de Environment Variables
2. Mostra a Connection String para copiar
"""

import subprocess
import webbrowser
import sys

SERVICE_ID = "srv-d8q8p168bjmc738h6ogg"
BACKEND_URL = "https://projeto-completo-1.onrender.com"

# Connection String do banco PostgreSQL
CONN_STRING = "postgresql://extrator_nf_db_user:5Jq2aQ752MXvjZagnijrtBq0G3wYh7KJ@dpg-d8q85ubeo5us73emdla0-a/extrator_nf_db"

print("=" * 65)
print("  CONFIGURACAO DO BANCO POSTGRESQL NO RENDER")
print("=" * 65)
print()
print("Connection String:")
print(f"  {CONN_STRING}")
print()
print("=" * 65)
print("INSTRUCOES:")
print("=" * 65)
print()
print("Passo 1: Acesse a pagina de Environment Variables:")
print(f"  https://dashboard.render.com/web/{SERVICE_ID}/env")
print()
print("Passo 2: Clique em 'Add Environment Variable'")
print()
print("Passo 3: Preencha:")
print(f"  Key:   DATABASE_URL")
print(f"  Value: {CONN_STRING}")
print()
print("Passo 4: Clique em 'Save'")
print()
print("Passo 5: Va em Manual Deploy:")
print(f"  https://dashboard.render.com/web/{SERVICE_ID}/deploys")
print("  Clique em 'Manual Deploy' -> 'Deploy latest commit'")
print()
print("Passo 6: Apos deploy (3-5 min), teste:")
print(f"  {BACKEND_URL}/health")
print(f"  {BACKEND_URL}/db-status")
print()
print("Passo 7: Acesse o sistema:")
print("  https://projeto-completo-cyan.vercel.app")
print()

# Abrir a pagina de env vars automaticamente
try:
    webbrowser.open(f"https://dashboard.render.com/web/{SERVICE_ID}/env")
    print("✅ Pagina aberta no navegador!")
except:
    print("⚠️  Abra manualmente: https://dashboard.render.com/web/{SERVICE_ID}/env")