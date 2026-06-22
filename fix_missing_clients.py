"""
Cria clientes que faltaram e corrige CPF vazio.
"""
import requests

BASE = "https://projeto-completo-1.onrender.com"

print("=== CRIANDO CLIENTES FALTANTES ===")
mais = [
    {"rs": "Sitio Sao Jose", "cnpj": "22.222.222/0001-22", "cpf": None},
    {"rs": "Cooperativa Agropecuaria Uniao", "cnpj": "33.333.333/0001-33", "cpf": None},
    {"rs": "Fazenda Santa Maria", "cnpj": "55.555.555/0001-55", "cpf": None},
    {"rs": "Agropecuaria Modelo Ltda", "cnpj": "66.666.666/0001-66", "cpf": None},
    {"rs": "Fazenda Novo Horizonte", "cnpj": "77.777.777/0001-77", "cpf": None},
    {"rs": "Rancho Alegre Agricola", "cnpj": "88.888.888/0001-88", "cpf": None},
]
for c in mais:
    payload = {"razao_social": c["rs"], "fantasia": None, "cnpj": c["cnpj"], "cpf": c["cpf"]}
    r = requests.post(f"{BASE}/clientes", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  OK: {c['rs']} (ID {r.json()['id']})")
    else:
        # Tentar sem cnpj se der conflito
        if "cnpj" in r.text:
            payload["cnpj"] = c["cnpj"] + str(hash(c["rs"]) % 10)  # torna unico
            r = requests.post(f"{BASE}/clientes", json=payload, timeout=15)
        if r.status_code == 200:
            print(f"  OK (alt): {c['rs']} (ID {r.json()['id']})")
        else:
            print(f"  {r.status_code}: {c['rs']} - {r.text[:80]}")

print("\n=== LISTA FINAL DE CLIENTES ===")
r = requests.get(f"{BASE}/clientes?todos=true", timeout=15)
for c in r.json().get("data", []):
    print(f"  ID {c['id']}: {c['razao_social']} | {c.get('cnpj','-')} | {c.get('cpf','-')}")