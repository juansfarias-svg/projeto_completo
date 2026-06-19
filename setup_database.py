"""
Script para configurar o banco de dados PostgreSQL no Render via API.
Cria banco PostgreSQL e configura a variável DATABASE_URL no Web Service.
"""

import requests
import json
import sys
import time
import os

RENDER_BACKEND = "https://projeto-completo-1.onrender.com"
RENDER_API_URL = "https://api.render.com/v1"

# ============================================================
# Funções da API Render
# ============================================================

def criar_database_render(api_key: str) -> dict:
    """Cria um banco PostgreSQL no Render via API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "database": {
            "name": "extrator-nf-db",
            "databaseName": "financeiro",
            "user": "financeiro",
            "plan": "free",
            "version": "16",
            "ipAllowList": []
        }
    }
    
    print("📦 Criando banco PostgreSQL 'extrator-nf-db'...")
    resp = requests.post(f"{RENDER_API_URL}/databases", json=payload, headers=headers)
    
    if resp.status_code == 201:
        data = resp.json()
        print(f"   ✅ Banco criado! ID: {data['database']['id']}")
        return data['database']
    elif resp.status_code == 409:
        print("   ⚠️  Banco já existe. Buscando informações...")
        return buscar_database_render(api_key)
    else:
        print(f"   ❌ Erro {resp.status_code}: {resp.text}")
        return None

def buscar_database_render(api_key: str) -> dict:
    """Busca informações do banco PostgreSQL no Render."""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    resp = requests.get(f"{RENDER_API_URL}/databases", headers=headers)
    
    if resp.status_code == 200:
        databases = resp.json()
        for db in databases:
            if db['database']['name'] == 'extrator-nf-db':
                print(f"   ✅ Banco encontrado: {db['database']['connectionInfo']['internalConnectionString']}")
                return db['database']
    return None

def atualizar_env_var_webservice(api_key: str, service_id: str, key: str, value: str):
    """Atualiza uma variável de ambiente no Web Service do Render."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Primeiro verificar se já existe
    resp = requests.get(f"{RENDER_API_URL}/services/{service_id}/env-vars", headers=headers)
    
    if resp.status_code == 200:
        env_vars = resp.json()
        exists = any(ev.get('key') == key for ev in env_vars)
        
        if exists:
            print(f"   ⚠️  Variável {key} já existe. Atualizando...")
            method = "PUT"
        else:
            method = "POST"
        
        payload = {
            "envVar": {
                "key": key,
                "value": value
            }
        }
        
        if method == "PUT":
            resp = requests.put(f"{RENDER_API_URL}/services/{service_id}/env-vars/{key}", json=payload, headers=headers)
        else:
            resp = requests.post(f"{RENDER_API_URL}/services/{service_id}/env-vars", json=payload, headers=headers)
        
        if resp.status_code in [200, 201]:
            print(f"   ✅ Variável {key} configurada!")
            return True
    
    print(f"   ❌ Erro ao configurar {key}: {resp.status_code} {resp.text}")
    return False

def trigger_deploy(api_key: str, service_id: str):
    """Dispara um novo deploy no Render."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("   🔄 Disparando novo deploy...")
    resp = requests.post(f"{RENDER_API_URL}/services/{service_id}/deploys", json={"deploy": {"clearCache": False}}, headers=headers)
    
    if resp.status_code == 201:
        print(f"   ✅ Deploy iniciado! Acompanhe em: https://dashboard.render.com/web/{service_id}")
        return True
    else:
        print(f"   ❌ Erro ao disparar deploy: {resp.status_code} {resp.text}")
        return False

def listar_services(api_key: str) -> list:
    """Lista todos os Web Services no Render."""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    resp = requests.get(f"{RENDER_API_URL}/services", headers=headers)
    
    if resp.status_code == 200:
        return resp.json()
    return []

# ============================================================
# Verificar backend
# ============================================================

def verificar_backend():
    print("🔍 Verificando backend...")
    try:
        resp = requests.get(f"{RENDER_BACKEND}/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Backend online: {data}")
            return True
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    return False

def verificar_db():
    print("🔍 Verificando status do banco...")
    try:
        resp = requests.get(f"{RENDER_BACKEND}/db-status", timeout=10)
        data = resp.json()
        print(f"   {'✅ Online' if data['banco_disponivel'] else '❌ Offline'}")
        return data['banco_disponivel']
    except:
        print("   ❌ Não foi possível verificar")
        return False

# ============================================================
# Main
# ============================================================

def main():
    print("=" * 65)
    print("  🚀 CONFIGURADOR DE BANCO DE DADOS - RENDER")
    print("  Cria PostgreSQL e configura integração com o backend")
    print("=" * 65)
    
    # 1. Verificar backend
    if not verificar_backend():
        print("\n❌ Backend offline! Execute o deploy no Render primeiro.")
        print("   https://dashboard.render.com")
        return
    
    # 2. Verificar banco
    if verificar_db():
        print("\n✅ Banco de dados já está configurado e online!")
        print(f"   Frontend: https://projeto-completo-cyan.vercel.app")
        print(f"   Backend:  {RENDER_BACKEND}")
        return
    
    print("\n⚠️  Banco PostgreSQL offline. Configure via uma das opções abaixo:\n")
    print("OPÇÃO 1: Dashboard Render (recomendado)")
    print("-" * 50)
    print("1. Acesse https://dashboard.render.com")
    print("2. Clique em 'New +' → 'PostgreSQL'")
    print("3. Nome: extrator-nf-db | Database: financeiro | User: financeiro")
    print("4. Plano: Free")
    print("5. Após criar, copie a 'Internal Connection String'")
    print("6. Vá no Web Service → Environment → Add Env Var:")
    print("   DATABASE_URL = [connection string copiada]")
    print("7. Clique em 'Save Changes' → 'Manual Deploy' → 'Deploy'")
    print()
    print("OPÇÃO 2: API Automática (precisa de API Key)")
    print("-" * 50)
    print("1. Acesse https://dashboard.render.com/api-keys")
    print("2. Crie uma API Key")
    print("3. Execute:")
    print("   python setup_database.py --api-key SUA_CHAVE")
    print("=" * 65)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--api-key" and len(sys.argv) > 2:
        api_key = sys.argv[2]
        
        print("=" * 65)
        print("  🚀 CONFIGURADOR AUTOMÁTICO - RENDER API")
        print("=" * 65)
        
        # Verificar serviços
        services = listar_services(api_key)
        if not services:
            print("❌ Nenhum Web Service encontrado. Crie primeiro no dashboard.")
            sys.exit(1)
        
        print(f"📋 Serviços encontrados:")
        for s in services:
            print(f"   - {s['service']['name']} (ID: {s['service']['id']})")
        
        # Criar banco
        db = criar_database_render(api_key)
        if not db:
            print("❌ Falha ao criar banco.")
            sys.exit(1)
        
        # Aguardar provisionamento
        print("⏳ Aguardando provisionamento do banco (30s)...")
        time.sleep(30)
        
        # Buscar connection string
        db_info = buscar_database_render(api_key)
        if not db_info:
            print("❌ Não foi possível obter connection string.")
            sys.exit(1)
        
        conn_string = db_info['connectionInfo']['internalConnectionString']
        
        # Configurar em cada serviço
        for s in services:
            service_id = s['service']['id']
            print(f"\n🔧 Configurando {s['service']['name']}...")
            
            atualizar_env_var_webservice(api_key, service_id, "DATABASE_URL", conn_string)
            trigger_deploy(api_key, service_id)
        
        print("\n✅ Configuração concluída!")
        print(f"   Backend:  {RENDER_BACKEND}")
        print(f"   Frontend: https://projeto-completo-cyan.vercel.app")
    else:
        main()