"""
Corrige a vinculacao de faturados e reimporta as contas faltantes.
"""
import psycopg2
import psycopg2.extras
import requests

LOCAL = "postgresql://financeiro:financeiro123@localhost:5432/financeiro"
BASE = "https://projeto-completo-1.onrender.com"

print("Conectando ao banco local...")
conn = psycopg2.connect(LOCAL, connect_timeout=10)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Buscar dados locais
cur.execute("SELECT * FROM faturado")
faturados_local = cur.fetchall()
print(f"Faturados no LOCAL: {len(faturados_local)}")

cur.execute("SELECT * FROM fornecedor")
fornecedores = {f["id"]: f for f in cur.fetchall()}

cur.execute("SELECT * FROM contas_a_pagar WHERE ativo = TRUE ORDER BY id")
contas = cur.fetchall()
print(f"Contas no LOCAL: {len(contas)}")

# 2. Criar faturados no Render
print("\n--- CRIANDO FATURADOS ---")
faturados_map = {}  # local_id -> render_id
for f in faturados_local:
    payload = {"nome_completo": f["nome_completo"], "cpf": f.get("cpf") or ""}
    r = requests.post(f"{BASE}/faturados", json=payload, timeout=15)
    if r.status_code == 200:
        render_id = r.json()["id"]
        faturados_map[f["id"]] = render_id
        print(f"  OK: {f['nome_completo']} (ID {f['id']} -> {render_id})")
    else:
        print(f"  Erro: {f['nome_completo']} - {r.text[:80]}")

# 3. Importar contas que tem faturado (e nao existem no render)
print(f"\n--- IMPORTANDO CONTAS COM FATURADO ---")
print(f"Faturados mapeados: {faturados_map}")

sucesso = 0
erro = 0
puladas = 0

for conta in contas:
    # Verificar se ja existe no Render (pular)
    r = requests.get(f"{BASE}/contas-a-pagar?limite=1&pagina=1", timeout=15)
    # Pular se ja temos 202+ (ja foram importadas sem faturado)
    if r.json()["total"] >= 202:
        puladas += 1
        continue

    fat_id_local = conta.get("faturado_id")
    faturado_payload = {}
    
    if fat_id_local and fat_id_local in faturados_map:
        f = faturados_local[[i for i, fl in enumerate(faturados_local) if fl["id"] == fat_id_local][0]]
        faturado_payload = {
            "nomeCompleto": f["nome_completo"],
            "cpf": f.get("cpf") or ""
        }

    fornecedor = fornecedores.get(conta["fornecedor_id"], {})

    # Buscar parcelas
    cur.execute("SELECT * FROM parcelas_pagar WHERE contas_a_pagar_id = %s ORDER BY numero_parcela", (conta["id"],))
    parcelas_rows = cur.fetchall()

    # Buscar classificacoes
    cur.execute("""
        SELECT td.nome FROM contas_a_pagar_tipo_despesa captd
        JOIN tipo_despesa td ON td.id = captd.tipo_despesa_id
        WHERE captd.contas_a_pagar_id = %s
    """, (conta["id"],))
    classificacoes = [r["nome"] for r in cur.fetchall()]

    payload = {
        "fornecedor": {
            "razaoSocial": fornecedor.get("razao_social", "Nao identificado"),
            "fantasia": fornecedor.get("fantasia"),
            "cnpj": fornecedor.get("cnpj", "00.000.000/0001-00")
        },
        "faturado": faturado_payload,
        "numeroNotaFiscal": conta["numero_nota_fiscal"],
        "serieNotaFiscal": conta.get("serie_nota_fiscal"),
        "dataEmissao": str(conta["data_emissao"]),
        "descricaoProdutos": conta.get("descricao_produtos") or "",
        "valorTotal": float(conta["valor_total"]),
        "parcelas": [
            {
                "numero": p["numero_parcela"],
                "dataVencimento": str(p["data_vencimento"]),
                "valor": float(p["valor_parcela"])
            }
            for p in parcelas_rows
        ],
        "classificacoesDespesa": classificacoes if classificacoes else ["SEM CLASSIFICACAO"]
    }

    try:
        r = requests.post(f"{BASE}/salvar", json=payload, timeout=30)
        if r.status_code == 200:
            sucesso += 1
        elif r.status_code == 409:
            puladas += 1
        else:
            erro += 1
            print(f"  ERRO NF {conta['numero_nota_fiscal']}: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        erro += 1
        print(f"  ERRO NF {conta['numero_nota_fiscal']}: {e}")

cur.close()
conn.close()
print(f"\n--- RESULTADO ---")
print(f"Sucesso: {sucesso} | Puladas (ja existem): {puladas} | Erro: {erro}")