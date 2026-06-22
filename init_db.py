"""
Script para executar o schema.sql no banco PostgreSQL do Render.
"""

import psycopg2
import os

# Connection string do banco (Internal - funciona dentro do Render)
DATABASE_URL = "postgresql://extrator_nf_db_user:5Jq2aQ752MXvjZagnijrtBq0G3wYh7KJ@dpg-d8q85ubeo5us73emdla0-a.oregon-postgres.render.com:5432/extrator_nf_db"

print("=" * 60)
print("  INICIALIZANDO BANCO DE DADOS")
print("=" * 60)

try:
    print("\nConectando ao PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)
    cur = conn.cursor()
    print("   Conectado!\n")

    # Ler o schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print("Executando schema.sql...")
    cur.execute(schema_sql)
    conn.commit()
    print("   Schema executado com sucesso!\n")

    # Listar tabelas criadas
    print("Tabelas no banco:")
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
    tables = cur.fetchall()
    for t in tables:
        print(f"   - {t[0]}")

    # Verificar dados inseridos (seed de tipo_despesa)
    print("\nVerificando dados seed...")
    cur.execute("SELECT COUNT(*) FROM tipo_despesa")
    count = cur.fetchone()[0]
    print(f"   {count} tipos de despesa cadastrados")

    cur.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("  BANCO DE DADOS INICIALIZADO COM SUCESSO!")
    print("=" * 60)

except Exception as e:
    print(f"\nERRO: {e}")