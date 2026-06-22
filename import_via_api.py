"""
Importa dados do banco local para o Render via API /salvar
"""
import psycopg2
import psycopg2.extras
import requests

LOCAL_DB = "postgresql://financeiro:financeiro123@localhost:5432/financeiro"
BACKEND_URL = "https://projeto-completo-1.onrender.com"

print("Conectando ao banco local...")
conn = psycopg2.connect(LOCAL_DB, connect_timeout=10)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Buscar fornecedores
cur.execute("SELECT * FROM fornecedor ORDER BY id")
fornecedores = {f["id"]: f for f in cur.fetchall()}
print(f"Fornecedores: {len(fornecedores)}")

# Buscar contas
cur.execute("SELECT * FROM contas_a_pagar WHERE ativo = TRUE ORDER BY id")
contas = cur.fetchall()
print(f"Contas a pagar: {len(contas)}")

total = len(contas)
sucesso = 0
erro = 0

for i, conta in enumerate(contas):
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

    # Fornecedor
    fornecedor = fornecedores.get(conta["fornecedor_id"], {})
    
    # Montar payload
    payload = {
        "fornecedor": {
            "razaoSocial": fornecedor.get("razao_social", "Nao identificado"),
            "cnpj": fornecedor.get("cnpj", "00.000.000/0001-00")
        },
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

    # Enviar
    try:
        r = requests.post(f"{BACKEND_URL}/salvar", json=payload, timeout=30)
        if r.status_code == 200:
            sucesso += 1
        elif r.status_code == 409:
            # Registro duplicado - ja existe
            erro += 1
        else:
            erro += 1
            data = r.json()
            print(f"  ERRO conta {conta['id']}: {r.status_code} - {data.get('detail', str(data))[:100]}")
    except Exception as e:
        erro += 1
        print(f"  ERRO conta {conta['id']}: {e}")

    if (i + 1) % 10 == 0:
        print(f"Progresso: {i+1}/{total} - OK: {sucesso} / ERRO: {erro}")

cur.close()
conn.close()
print(f"\nFinalizado! {total} processadas - OK: {sucesso} / ERRO: {erro}")