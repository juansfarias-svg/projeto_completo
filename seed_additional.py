"""
Cria dados adicionais (clientes, tipos de receita) no Render para demonstracao.
"""
import requests

BASE = "https://projeto-completo-1.onrender.com"

print("=== CRIANDO CLIENTES ADICIONAIS ===")
clientes = [
    {"razao_social": "Fazenda Boa Esperanca", "fantasia": "Boa Esperanca", "cnpj": "11.111.111/0001-11", "cpf": ""},
    {"razao_social": "Sitio Sao Jose", "fantasia": "Sao Jose", "cnpj": "22.222.222/0001-22", "cpf": ""},
    {"razao_social": "Cooperativa Agropecuaria Uniao", "fantasia": "Coop Uniao", "cnpj": "33.333.333/0001-33", "cpf": ""},
    {"razao_social": "Joao Batista Oliveira", "fantasia": "", "cnpj": "", "cpf": "111.222.333-44"},
    {"razao_social": "Maria da Silva Santos", "fantasia": "", "cnpj": "", "cpf": "555.666.777-88"},
]

for cli in clientes:
    payload = {
        "razao_social": cli["razao_social"],
        "fantasia": cli["fantasia"] or None,
        "cnpj": cli["cnpj"],
        "cpf": cli["cpf"]
    }
    r = requests.post(f"{BASE}/clientes", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  OK: {cli['razao_social']} (ID {r.json()['id']})")
    else:
        print(f"  {r.status_code}: {cli['razao_social']} - {r.text[:80]}")

print("\n=== CRIANDO TIPOS DE RECEITA ===")
receitas = [
    {"nome": "VENDA DE GRÃOS", "descricao": "Soja, Milho, Trigo e outros graos"},
    {"nome": "VENDA DE PRODUTOS", "descricao": "Produtos agricolas beneficiados"},
    {"nome": "PRESTACAO DE SERVICOS", "descricao": "Servicos de pulverizacao, colheita, etc"},
    {"nome": "ARRENDAMENTO", "descricao": "Arrendamento de terras e maquinas"},
    {"nome": "SUBSIDIOS", "descricao": "Subsidios governamentais e programas"},
    {"nome": "OUTRAS RECEITAS", "descricao": "Outras fontes de receita"},
]

for rec in receitas:
    payload = {"nome": rec["nome"], "descricao": rec["descricao"]}
    r = requests.post(f"{BASE}/tipos-receita", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  OK: {rec['nome']} (ID {r.json()['id']})")
    else:
        print(f"  {r.status_code}: {rec['nome']} - {r.text[:80]}")

print("\n=== VERIFICACAO FINAL ===")
r = requests.get(f"{BASE}/clientes?todos=true", timeout=15)
print(f"Total clientes: {len(r.json().get('data', []))}")

r = requests.get(f"{BASE}/tipos-receita?todos=true", timeout=15)
print(f"Total tipos receita: {len(r.json().get('data', []))}")

r = requests.get(f"{BASE}/fornecedores?todos=true", timeout=15)
print(f"Total fornecedores: {len(r.json().get('data', []))}")

r = requests.get(f"{BASE}/faturados?todos=true", timeout=15)
print(f"Total faturados: {len(r.json().get('data', []))}")

r = requests.get(f"{BASE}/contas-a-pagar?limite=1&pagina=1", timeout=15)
print(f"Total contas a pagar: {r.json()['total']}")