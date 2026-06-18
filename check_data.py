import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://financeiro:financeiro123@localhost:5432/financeiro")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM contas_a_pagar")
total = cur.fetchone()[0]
print(f"Total de contas a pagar: {total}")

cur.execute("SELECT COUNT(*) FROM fornecedor")
forn = cur.fetchone()[0]
print(f"Total de fornecedores: {forn}")

cur.execute("SELECT COUNT(*) FROM parcelas_pagar")
parc = cur.fetchone()[0]
print(f"Total de parcelas: {parc}")

cur.execute("SELECT ROUND(SUM(valor_total)::numeric, 2) FROM contas_a_pagar")
total_valor = cur.fetchone()[0]
print(f"Valor total acumulado: R$ {total_valor:,.2f}")

cur.execute("""
    SELECT f.razao_social, COUNT(cap.id) as qtd, ROUND(SUM(cap.valor_total)::numeric, 2) as total
    FROM contas_a_pagar cap
    JOIN fornecedor f ON f.id = cap.fornecedor_id
    GROUP BY f.razao_social
    ORDER BY total DESC
    LIMIT 10
""")
print("\nTop 10 fornecedores por valor:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} notas - R$ {row[2]:,.2f}")

cur.execute("""
    SELECT td.nome, COUNT(captd.id) as qtd, ROUND(SUM(cap.valor_total)::numeric, 2) as total
    FROM contas_a_pagar_tipo_despesa captd
    JOIN contas_a_pagar cap ON cap.id = captd.contas_a_pagar_id
    JOIN tipo_despesa td ON td.id = captd.tipo_despesa_id
    GROUP BY td.nome
    ORDER BY total DESC
""")
print("\nGastos por categoria de despesa:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} ocorrencias - R$ {row[2]:,.2f}")

cur.close()
conn.close()