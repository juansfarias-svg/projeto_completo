"""
Script para migrar dados do banco local (Docker) para o banco do Render.
Versao robusta com tratamento de erros.
"""

import psycopg2
import psycopg2.extras
import sys

LOCAL_DB = "postgresql://financeiro:financeiro123@localhost:5432/financeiro"
RENDER_DB = "postgresql://extrator_nf_db_user:5Jq2aQ752MXvjZagnijrtBq0G3wYh7KJ@dpg-d8q85ubeo5us73emdla0-a.oregon-postgres.render.com:5432/extrator_nf_db"

print("=" * 60)
print("  MIGRACAO DE DADOS - LOCAL -> RENDER")
print("=" * 60)

try:
    # Conectar ao banco local
    print("\nConectando ao banco LOCAL (Docker)...")
    conn_local = psycopg2.connect(LOCAL_DB, connect_timeout=10)
    cur_local = conn_local.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("   OK!\n")

    # Conectar ao banco do Render
    print("Conectando ao banco RENDER...")
    conn_render = psycopg2.connect(RENDER_DB, connect_timeout=30)
    cur_render = conn_render.cursor()
    print("   OK!\n")

    # Limpar dados existentes no Render
    print("Limpando dados existentes no Render...")
    cur_render.execute("DELETE FROM contas_a_pagar_tipo_despesa")
    cur_render.execute("DELETE FROM parcelas_pagar")
    cur_render.execute("DELETE FROM contas_a_pagar")
    cur_render.execute("DELETE FROM contas_a_receber_tipo_receita")
    cur_render.execute("DELETE FROM parcelas_receber")
    cur_render.execute("DELETE FROM contas_a_receber")
    cur_render.execute("DELETE FROM faturado")
    cur_render.execute("DELETE FROM fornecedor")
    cur_render.execute("DELETE FROM cliente")
    conn_render.commit()
    print("   OK!\n")

    # 1. Migrar fornecedores
    print("1/5 - Migrando fornecedores...")
    cur_local.execute("SELECT * FROM fornecedor ORDER BY id")
    fornecedores = cur_local.fetchall()
    for f in fornecedores:
        cur_render.execute(
            "INSERT INTO fornecedor (id, razao_social, fantasia, cnpj, ativo, criado_em, atualizado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (f["id"], f["razao_social"], f["fantasia"], f["cnpj"], f["ativo"], f["criado_em"], f.get("atualizado_em", f["criado_em"]))
        )
    conn_render.commit()
    print(f"   {len(fornecedores)} fornecedores migrados")

    # 2. Migrar faturados
    print("2/5 - Migrando faturados...")
    cur_local.execute("SELECT * FROM faturado ORDER BY id")
    faturados = cur_local.fetchall()
    for f in faturados:
        cur_render.execute(
            "INSERT INTO faturado (id, nome_completo, cpf, ativo, criado_em, atualizado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (f["id"], f["nome_completo"], f["cpf"], f["ativo"], f["criado_em"], f.get("atualizado_em", f["criado_em"]))
        )
    conn_render.commit()
    print(f"   {len(faturados)} faturados migrados")

    # Fix: Ajustar sequences para os IDs max
    cur_render.execute("SELECT setval('fornecedor_id_seq', (SELECT MAX(id) FROM fornecedor))")
    cur_render.execute("SELECT setval('faturado_id_seq', (SELECT MAX(id) FROM faturado))")
    conn_render.commit()

    # 3. Migrar contas_a_pagar
    print("3/5 - Migrando contas a pagar...")
    cur_local.execute("SELECT * FROM contas_a_pagar ORDER BY id")
    contas = cur_local.fetchall()
    for c in contas:
        cur_render.execute(
            "INSERT INTO contas_a_pagar (id, fornecedor_id, faturado_id, numero_nota_fiscal, serie_nota_fiscal, "
            "data_emissao, descricao_produtos, valor_total, ativo, criado_em, atualizado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (c["id"], c["fornecedor_id"], c["faturado_id"], c["numero_nota_fiscal"], c["serie_nota_fiscal"],
             c["data_emissao"], c["descricao_produtos"], c["valor_total"], c["ativo"], c["criado_em"],
             c.get("atualizado_em", c["criado_em"]))
        )
        conn_render.commit()
    cur_render.execute("SELECT setval('contas_a_pagar_id_seq', (SELECT MAX(id) FROM contas_a_pagar))")
    conn_render.commit()
    print(f"   {len(contas)} contas a pagar migradas")

    # 4. Migrar parcelas
    print("4/5 - Migrando parcelas...")
    cur_local.execute("SELECT * FROM parcelas_pagar ORDER BY id")
    parcelas = cur_local.fetchall()
    for p in parcelas:
        cur_render.execute(
            "INSERT INTO parcelas_pagar (id, contas_a_pagar_id, numero_parcela, data_vencimento, valor_parcela, "
            "data_pagamento, valor_pago, observacoes, criado_em, atualizado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (p["id"], p["contas_a_pagar_id"], p["numero_parcela"], p["data_vencimento"], p["valor_parcela"],
             p["data_pagamento"], p["valor_pago"], p.get("observacoes"), p["criado_em"],
             p.get("atualizado_em", p["criado_em"]))
        )
    conn_render.commit()
    cur_render.execute("SELECT setval('parcelas_pagar_id_seq', (SELECT MAX(id) FROM parcelas_pagar))")
    conn_render.commit()
    print(f"   {len(parcelas)} parcelas migradas")

    # 5. Migrar classificacoes
    print("5/5 - Migrando classificacoes de despesa...")
    cur_local.execute("SELECT * FROM contas_a_pagar_tipo_despesa ORDER BY id")
    classificacoes = cur_local.fetchall()
    for cl in classificacoes:
        cur_render.execute(
            "INSERT INTO contas_a_pagar_tipo_despesa (id, contas_a_pagar_id, tipo_despesa_id) "
            "VALUES (%s, %s, %s)",
            (cl["id"], cl["contas_a_pagar_id"], cl["tipo_despesa_id"])
        )
    conn_render.commit()
    print(f"   {len(classificacoes)} classificacoes migradas")

    # Fechar conexoes
    cur_local.close()
    conn_local.close()
    cur_render.close()
    conn_render.close()

    print("\n" + "=" * 60)
    print("  ✅ MIGRACAO CONCLUIDA COM SUCESSO!")
    print("=" * 60)
    print(f"  {len(fornecedores)} fornecedores")
    print(f"  {len(faturados)} faturados")
    print(f"  {len(contas)} contas a pagar")
    print(f"  {len(parcelas)} parcelas")
    print(f"  {len(classificacoes)} classificacoes")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERRO: {e}")
    conn_render.rollback()
    print("\nVerifique se o Docker esta rodando:")
    print("  docker-compose up -d")
    sys.exit(1)