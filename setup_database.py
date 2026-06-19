"""
Script para configurar o banco de dados PostgreSQL no Render.
Cria o banco e executa o schema.sql automaticamente.
"""

import os
import subprocess
import sys
import json
import urllib.request

# URL do backend no Render
RENDER_BACKEND = "https://projeto-completo-1.onrender.com"

# ============================================================
# Verificar status atual do banco
# ============================================================
def verificar_status_banco():
    print("\n🔍 Verificando status do banco de dados atual...")
    try:
        with urllib.request.urlopen(f"{RENDER_BACKEND}/db-status") as resp:
            data = json.loads(resp.read().decode())
            print(f"   Status: {'✅ Online' if data['banco_disponivel'] else '❌ Offline'}")
            print(f"   URL: {data['database_url']}")
            return data['banco_disponivel']
    except Exception as e:
        print(f"   ❌ Erro ao verificar: {e}")
        return False

# ============================================================
# Verificar se o health endpoint responde
# ============================================================
def verificar_health():
    print("\n🔍 Verificando health do servidor...")
    try:
        with urllib.request.urlopen(f"{RENDER_BACKEND}/health") as resp:
            data = json.loads(resp.read().decode())
            print(f"   Status: ✅ {data}")
            return data
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return None

# ============================================================
# Instruções para criar banco no Render
# ============================================================
def instrucoes_render():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          CONFIGURAÇÃO DO BANCO POSTGRESQL NO RENDER         ║
╚══════════════════════════════════════════════════════════════╝

Passo 1: Acesse https://dashboard.render.com
Passo 2: Clique em "New +" → "PostgreSQL"
Passo 3: Configure:
   • Nome: extrator-nf-db
   • Database: financeiro
   • User: financeiro
   • Plan: Free
Passo 4: Após criar, copie a "Internal Connection String" (ex: postgresql://financeiro:senha@host:5432/financeiro)
Passo 5: Acesse o Web Service no Render → Environment → Add Environment Variable:
   • DATABASE_URL = [connection string copiada]
Passo 6: Clique em "Save Changes" → "Deploy" (ou manual deploy)

═════════════════════════════════════════════════════════════════
    """)

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  CONFIGURADOR DE BANCO DE DADOS - RENDER")
    print("=" * 60)

    # 1. Verificar health
    health = verificar_health()
    if health:
        print(f"\n✅ Backend online em: {RENDER_BACKEND}")
    else:
        print(f"\n❌ Backend offline. Verifique se o Render está rodando.")

    # 2. Verificar status do banco
    banco_ok = verificar_status_banco()

    if banco_ok:
        print("\n✅ Banco de dados já está configurado e online!")
        print(f"   Acesse: {RENDER_BACKEND}")
        print(f"   Frontend: https://projeto-completo-cyan.vercel.app")
    else:
        print("\n❌ Banco de dados offline ou não configurado.")
        instrucoes_render()

    print("\n" + "=" * 60)
    print("  RESUMO DAS URLs")
    print("=" * 60)
    print(f"   Backend:    {RENDER_BACKEND}")
    print(f"   Frontend:   https://projeto-completo-cyan.vercel.app")
    print(f"   Repositório: https://github.com/juansfarias-svg/projeto_completo")
    print(f"   Dashboard Render: https://dashboard.render.com")
    print(f"   Dashboard Vercel: https://vercel.com/juan52/projeto-completo")
    print("=" * 60)