"""
Cria mais clientes no Render.
"""
import requests

BASE = "https://projeto-completo-1.onrender.com"

print("=== CRIANDO MAIS CLIENTES ===")
mais = [
    {"rs": "Sitio Sao Jose", "cnpj": "22.222.222/0001-22", "cpf": ""},
    {"rs": "Cooperativa Agropecuaria Uniao", "cnpj": "33.333.333/0001-33", "cpf": ""},
    {"rs": "Maria da Silva Santos", "cnpj": "44.444.444/0001-44", "cpf": "555.666.777-88"},
    {"rs": "Fazenda Santa Maria", "cnpj": "55.555.555/0001-55", "cpf": ""},
    {"rs": "Agropecuaria Modelo Ltda", "cnpj": "66.666.666/0001-66", "cpf": ""},
]
for c in mais:
    payload = {"razao_social": c["rs"], "fantasia": None, "cnpj": c["cnpj"], "cpf": c["cpf"]}
    r = requests.post(f"{BASE}/clientes", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  OK: {c['rs']} (ID {r.json()['id']})")
    else:
        print(f"  {r.status_code}: {c['rs']} - {r.text[:60]}")

print("\n=== VERIFICANDO ===")
r = requests.get(f"{BASE}/clientes?todos=true", timeout=15)
dados = r.json().get("data", [])
print(f"Total clientes: {len(dados)}")
for c in dados:
    print(f"  ID {c['id']}: {c['razao_social']}")