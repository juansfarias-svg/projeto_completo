"""
Importa COMPLETO do banco local para o Render via API.
Inclui: fornecedores, faturados, clientes, contas, parcelas, classificacoes.
"""
import psycopg2
import psycopg2.extras
import requests

LOCAL_DB = "postgresql://financeiro:financeiro123@localhost:5432/financeiro"
BACKEND_URL = "https://projeto-completo-1.onrender.com"

print("Conectando ao banco local...")
conn = psycopg2.connect(LOCAL_DB, connect_timeout=10)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Buscar todos os dados locais
cur.execute("SELECT * FROM fornecedor ORDER BY id")
fornecedores = {f["id"]: f for f in cur.fetchall()}
print(f"Fornecedores: {len(fornecedores)}")

cur.execute("SELECT * FROM faturado ORDER BY id")
faturados = {f["id"]: f for f in cur.fetchall()}
print(f"Faturados: {len(faturados)}")

cur.execute("SELECT * FROM cliente ORDER BY id")
clientes = {c["id"]: c for c in cur.fetchall()}
print(f"Clientes: {len(clientes)}")

cur.execute("SELECT * FROM tipo_despesa ORDER BY id")
tipos_despesa = {t["id"]: t for t in cur.fetchall()}
print(f"Tipos despesa: {len(tipos_despesa)}")

cur.execute("SELECT * FROM tipo_receita ORDER BY id")
tipos_receita = {t["id"]: t for t in cur.fetchall()}
print(f"Tipos receita: {len(tipos_receita)}")

cur.execute("SELECT * FROM contas_a_pagar WHERE ativo = TRUE ORDER BY id")
contas = cur.fetchall()
print(f"Contas a pagar: {len(contas)}")

# 2. Criar clientes via API /clientes
print("\n--- CRIANDO CLIENTES ---")
for cid, cli in clientes.items():
    payload = {
        "razao_social": cli["razao_social"],
        "fantasia": cli.get("fantasia"),
        "cnpj": cli.get("cnpj") or "",
        "cpf": cli.get("cpf") or ""
    }
    r = requests.post(f"{BACKEND_URL}/clientes", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  Cliente {cli['razao_social']} criado!")
    else:
        print(f"  Erro cliente {cli['razao_social']}: {r.status_code}")

# 3. Criar tipos de receita (se houver)
print("\n--- CRIANDO TIPOS RECEITA ---")
for tid, tr in tipos_receita.items():
    payload = {"nome": tr["nome"], "descricao": tr.get("descricao") or tr["nome"]}
    r = requests.post(f"{BACKEND_URL}/tipos-receita", json=payload, timeout=15)
    if r.status_code == 200:
        print(f"  Tipo receita {tr['nome']} criado!")
    else:
        print(f"  Erro tipo receita {tr['nome']}: {r.status_code}")

# 4. Importar contas a pagar com dados completos
print(f"\n--- IMPORTANDO {len(contas)} CONTAS A PAGAR ---")
total = len(contas)
sucesso = 0
erro = 0
duplicado = 0

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

    # Faturado (se houver) - verificar se existe no dict
    faturado = None
    if conta.get("faturado_id"):
        f_id = conta["faturado_id"]
        if f_id in faturados:
            f = faturados[f_id]
            faturado = {
                "nomeCompleto": f["nome_completo"],
                "cpf": f.get("cpf")
            }

    # Montar payload - garantir que faturado seja dict, nunca None
    if faturado is None:
        faturado = {}
    
    payload = {
        "fornecedor": {
            "razaoSocial": fornecedor.get("razao_social", "Nao identificado"),
            "fantasia": fornecedor.get("fantasia"),
            "cnpj": fornecedor.get("cnpj", "00.000.000/0001-00")
        },
        "faturado": faturado,
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
            duplicado += 1
        else:
            erro += 1
            data = r.json()
            print(f"  ERRO NF {conta['numero_nota_fiscal']}: {r.status_code} - {data.get('detail', str(data))[:100]}")
    except Exception as e:
        erro += 1
        print(f"  ERRO NF {conta['numero_nota_fiscal']}: {e}")

    if (i + 1) % 20 == 0:
        print(f"Progresso: {i+1}/{total} - OK: {sucesso} / DUP: {duplicado} / ERRO: {erro}")

cur.close()
conn.close()
print(f"\n--- FINALIZADO ---")
print(f"Total: {total} - OK: {sucesso} / Duplicado: {duplicado} / Erro: {erro}")