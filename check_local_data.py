"""
Verifica dados faltantes no banco local.
"""
import psycopg2
import psycopg2.extras

LOCAL_DB = "postgresql://financeiro:financeiro123@localhost:5432/financeiro"

conn = psycopg2.connect(LOCAL_DB, connect_timeout=10)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== DADOS NO BANCO LOCAL ===")
cur.execute("SELECT COUNT(*) FROM cliente")
print(f"Clientes: {cur.fetchone()['count']}")

cur.execute("SELECT COUNT(*) FROM faturado")
print(f"Faturados: {cur.fetchone()['count']}")

cur.execute("SELECT COUNT(*) FROM contas_a_receber")
print(f"Contas a receber: {cur.fetchone()['count']}")

cur.execute("SELECT COUNT(*) FROM tipo_receita")
print(f"Tipos receita: {cur.fetchone()['count']}")

cur.execute("SELECT COUNT(*) FROM parcelas_receber")
print(f"Parcelas receber: {cur.fetchone()['count']}")

cur.execute("SELECT COUNT(*) FROM contas_a_receber_tipo_receita")
print(f"Classificacoes receita: {cur.fetchone()['count']}")

print("\n=== CLIENTES ===")
cur.execute("SELECT * FROM cliente")
for c in cur.fetchall():
    print(f"  ID {c['id']}: {c['razao_social']} | CNPJ: {c.get('cnpj','-')} | CPF: {c.get('cpf','-')} | Ativo: {c['ativo']}")

print("\n=== FATURADOS ===")
cur.execute("SELECT * FROM faturado")
for f in cur.fetchall():
    print(f"  ID {f['id']}: {f['nome_completo']} | CPF: {f.get('cpf','-')} | Ativo: {f['ativo']}")

print("\n=== CONTAS A RECEBER (primeiras 5) ===")
cur.execute("SELECT * FROM contas_a_receber LIMIT 5")
for r in cur.fetchall():
    print(f"  ID {r['id']}: Documento {r['numero_documento']} | R$ {r['valor_total']} | Cliente ID: {r['cliente_id']} | Faturado ID: {r['faturado_id']}")

print("\n=== TIPOS RECEITA ===")
cur.execute("SELECT * FROM tipo_receita")
for t in cur.fetchall():
    print(f"  ID {t['id']}: {t['nome']}")

print("\n=== CONTAS A PAGAR COM FATURADO ===")
cur.execute("SELECT COUNT(*) FROM contas_a_pagar WHERE faturado_id IS NOT NULL")
count = cur.fetchone()['count']
print(f"Total com faturado: {count}")
if count > 0:
    cur.execute("SELECT cap.id, cap.numero_nota_fiscal, fat.nome_completo FROM contas_a_pagar cap JOIN faturado fat ON fat.id = cap.faturado_id LIMIT 5")
    for c in cur.fetchall():
        print(f"  NF {c['numero_nota_fiscal']} -> Faturado: {c['nome_completo']}")

cur.close()
conn.close()