"""
Verifica integridade dos dados no banco do Render.
"""
import requests

BASE = "https://projeto-completo-1.onrender.com"

print("=" * 60)
print("  VERIFICACAO DE INTEGRIDADE DOS DADOS")
print("=" * 60)

# Fornecedores
r = requests.get(f"{BASE}/fornecedores?todos=true", timeout=15)
forn = r.json().get("data", [])
print(f"\nFornecedores no sistema: {len(forn)}")
for f in forn[:5]:
    print(f"  - {f['razao_social']} (CNPJ: {f['cnpj']})")

# Contas a pagar
r = requests.get(f"{BASE}/contas-a-pagar?limite=5&pagina=1", timeout=15)
dados = r.json()
print(f"\nContas a pagar: {dados['total']}")
print("Ultimas 5:")
for c in dados["registros"]:
    print(f"  NF {c['numero_nota_fiscal']} - {c['fornecedor_razao_social']} - R$ {c['valor_total']} - Parcelas: {c['qtd_parcelas']}")

# Total de parcelas
r = requests.get(f"{BASE}/contas-a-pagar?limite=500&pagina=1", timeout=30)
total_parcelas = sum(c["qtd_parcelas"] for c in r.json()["registros"])
print(f"\nTotal de parcelas: {total_parcelas}")

# Faturados
r = requests.get(f"{BASE}/faturados?todos=true", timeout=15)
print(f"Faturados: {len(r.json().get('data', []))}")

# Tipos de despesa
r = requests.get(f"{BASE}/tipos-despesa?todos=true", timeout=15)
print(f"Tipos de despesa: {len(r.json().get('data', []))}")

# DB Status
r = requests.get(f"{BASE}/db-status", timeout=15)
db = r.json()
print(f"\nBanco online: {db['banco_disponivel']}")

print("\n" + "=" * 60)
print("  VERIFICACAO CONCLUIDA")
print("=" * 60)