"""
Script para popular o banco com 200 notas fiscais fictícias.
Insere fornecedores, faturados, contas a pagar, parcelas e classificações de despesa.
"""

import psycopg2
import psycopg2.extras
from datetime import date, timedelta
from dotenv import load_dotenv
import os
import random
import hashlib

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://financeiro:financeiro123@localhost:5432/financeiro")

# ============================================================
# DADOS FICTÍCIOS PARA POPULAÇÃO
# ============================================================

FORNECEDORES = [
    {"razao_social": "CTVA PROTEÇÃO DE CULTIVOS LTDA.", "fantasia": "Corteva", "cnpj": "47.180.625/0058-81"},
    {"razao_social": "RIVEMA RIO VERDE MÁQUINAS AGRÍCOLAS E PEÇAS LTDA", "fantasia": "Rivema", "cnpj": "07.225.264/0001-70"},
    {"razao_social": "IGUAÇU MÁQUINAS AGRÍCOLAS LTDA", "fantasia": "Iguaçu", "cnpj": "33.656.729/0023-85"},
    {"razao_social": "BRF SEMENTES LTDA", "fantasia": "Brasil Fértil", "cnpj": "12.345.678/0001-90"},
    {"razao_social": "AGROSUL COMÉRCIO DE INSUMOS LTDA", "fantasia": "Agrosul", "cnpj": "23.456.789/0001-12"},
    {"razao_social": "FERTIMAX INDÚSTRIA E COMÉRCIO LTDA", "fantasia": "Fertimax", "cnpj": "34.567.890/0001-23"},
    {"razao_social": "DEFENSIVOS AGRÍCOLAS UNIÃO LTDA", "fantasia": "DAU", "cnpj": "45.678.901/0001-34"},
    {"razao_social": "MECANIZA AGRÍCOLA S/A", "fantasia": "Mecaniza", "cnpj": "56.789.012/0001-45"},
    {"razao_social": "COMBUSTÍVEIS DO CERRADO LTDA", "fantasia": "Cerrado Fuel", "cnpj": "67.890.123/0001-56"},
    {"razao_social": "SEMENTES GENÉTICAS DO BRASIL LTDA", "fantasia": "Genética Brasil", "cnpj": "78.901.234/0001-67"},
    {"razao_social": "ADUBOS VERDE LTDA", "fantasia": "Adubos Verde", "cnpj": "89.012.345/0001-78"},
    {"razao_social": "PEÇAS E SERVIÇOS RURAIS LTDA", "fantasia": "Peças Rural", "cnpj": "90.123.456/0001-89"},
    {"razao_social": "ENERGIA SOLAR DO CAMPO LTDA", "fantasia": "Solar Campo", "cnpj": "01.234.567/0001-90"},
    {"razao_social": "TRANSPORTADORA RODOESTE LTDA", "fantasia": "Rodoeste", "cnpj": "02.345.678/0001-01"},
    {"razao_social": "SEGURADORA AGRÍCOLA S/A", "fantasia": "SegAgro", "cnpj": "03.456.789/0001-12"},
]

FATURADOS = [
    {"nome_completo": "João Carlos da Silva", "cpf": "123.456.789-01"},
    {"nome_completo": "Maria Aparecida Oliveira", "cpf": "234.567.890-12"},
    {"nome_completo": "Pedro Henrique Santos", "cpf": "345.678.901-23"},
    {"nome_completo": "Ana Beatriz Costa", "cpf": "456.789.012-34"},
    {"nome_completo": "Lucas Almeida Pereira", "cpf": "567.890.123-45"},
    {"nome_completo": "Juliana Ferreira Souza", "cpf": "678.901.234-56"},
    {"nome_completo": "Rafael Augusto Lima", "cpf": "789.012.345-67"},
    {"nome_completo": "Camila Rodrigues Barbosa", "cpf": "890.123.456-78"},
]

CATEGORIAS_DESPESA = [
    "INSUMOS AGRÍCOLAS",
    "MANUTENÇÃO E OPERAÇÃO",
    "RECURSOS HUMANOS",
    "SERVIÇOS OPERACIONAIS",
    "INFRAESTRUTURA E UTILIDADES",
    "ADMINISTRATIVAS",
    "SEGUROS E PROTEÇÃO",
    "IMPOSTOS E TAXAS",
    "INVESTIMENTOS",
]

PRODUTOS = [
    "Sementes de soja RR", "Fertilizante NPK 20-10-10", "Defensivo agrícola glifosato",
    "Óleo diesel S-10", "Peças para trator", "Pneus agrícolas",
    "Mão de obra temporária", "Frete de cargas", "Energia elétrica rural",
    "Honorários contábeis", "Seguro agrícola safra", "ITR - Imposto Territorial Rural",
    "Aquisição de colheitadeira", "Sementes de milho", "Fertilizante ureia",
    "Defensivo agrícola fungicida", "Lubrificantes e filtros", "Manutenção de máquinas",
    "Arrendamento de terras", "Materiais de construção",
    "Serviços de pulverização aérea", "Secagem e armazenagem de grãos",
    "Consultoria agronômica", "Implementos agrícolas",
]

# ============================================================
# CONEXÃO
# ============================================================
def get_conn():
    return psycopg2.connect(DATABASE_URL)


def gerar_cnpj_unico(idx):
    """Gera um CNPJ fictício único baseado no índice."""
    base = f"{idx:03d}.{idx+1:03d}.{idx+2:03d}/{idx+3:04d}-{idx+4:02d}"
    return base[:18]


def seed():
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()
    hoje = date.today()

    try:
        # ── 1. Inserir fornecedores se não existirem ──
        fornecedores_ids = []
        for f in FORNECEDORES:
            cur.execute("SELECT id FROM fornecedor WHERE cnpj = %s", (f["cnpj"],))
            row = cur.fetchone()
            if row:
                fornecedores_ids.append(row[0])
                print(f"  Fornecedor {f['razao_social']} já existe (ID {row[0]})")
            else:
                cur.execute(
                    "INSERT INTO fornecedor (razao_social, fantasia, cnpj) VALUES (%s, %s, %s) RETURNING id",
                    (f["razao_social"], f["fantasia"], f["cnpj"])
                )
                fid = cur.fetchone()[0]
                fornecedores_ids.append(fid)
                print(f"  Fornecedor {f['razao_social']} criado (ID {fid})")

        # ── 2. Inserir faturados se não existirem ──
        faturados_ids = []
        for fat in FATURADOS:
            cur.execute("SELECT id FROM faturado WHERE cpf = %s", (fat["cpf"],))
            row = cur.fetchone()
            if row:
                faturados_ids.append(row[0])
            else:
                cur.execute(
                    "INSERT INTO faturado (nome_completo, cpf) VALUES (%s, %s) RETURNING id",
                    (fat["nome_completo"], fat["cpf"])
                )
                faturados_ids.append(cur.fetchone()[0])

        # ── 3. Verificar categorias de despesa (já devem existir do seed) ──
        despesas_ids = {}
        for cat in CATEGORIAS_DESPESA:
            cur.execute("SELECT id FROM tipo_despesa WHERE nome = %s", (cat,))
            row = cur.fetchone()
            if row:
                despesas_ids[cat] = row[0]
            else:
                cur.execute(
                    "INSERT INTO tipo_despesa (nome, descricao) VALUES (%s, %s) RETURNING id",
                    (cat, cat)
                )
                despesas_ids[cat] = cur.fetchone()[0]

        # ── 4. Gerar 200 notas fiscais ──
        contador = 0
        for i in range(200):
            fornecedor_id = random.choice(fornecedores_ids)
            faturado_id = random.choice(faturados_ids) if random.random() > 0.3 else None

            # Número da NF
            numero_nf = f"{random.randint(10000, 99999)}-{i+1}"
            serie = random.choice([None, "1", "2", "U", "S1", "S2"])

            # Data de emissão: entre 180 dias atrás e hoje
            dias_atras = random.randint(0, 180)
            data_emissao = hoje - timedelta(days=dias_atras)

            # Descrição: combina 1-3 produtos
            qtd_prod = random.randint(1, 3)
            produtos = random.sample(PRODUTOS, qtd_prod)
            descricao = "; ".join(produtos)

            # Valor total: entre R$ 500 e R$ 150.000
            valor_total = round(random.uniform(500, 150000), 2)

            # Parcelas: 1 a 6
            qtd_parcelas = random.randint(1, 6)
            valor_parcela = round(valor_total / qtd_parcelas, 2)
            # Ajuste para fechar o total
            ultima_parcela = round(valor_total - (valor_parcela * (qtd_parcelas - 1)), 2)

            # Verificar duplicidade da NF para o mesmo fornecedor
            cur.execute(
                "SELECT id FROM contas_a_pagar WHERE fornecedor_id = %s AND numero_nota_fiscal = %s AND COALESCE(serie_nota_fiscal, '') = COALESCE(%s, '')",
                (fornecedor_id, numero_nf, serie or "")
            )
            if cur.fetchone():
                # NF já existe, pular
                continue

            # Inserir conta a pagar
            cur.execute("""
                INSERT INTO contas_a_pagar
                    (fornecedor_id, faturado_id, numero_nota_fiscal, serie_nota_fiscal,
                     data_emissao, descricao_produtos, valor_total)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (fornecedor_id, faturado_id, numero_nf, serie,
                  data_emissao, descricao, valor_total))
            contas_a_pagar_id = cur.fetchone()[0]

            # Inserir parcelas
            for p in range(1, qtd_parcelas + 1):
                vencimento = data_emissao + timedelta(days=30 * p)
                v_parcela = valor_parcela if p < qtd_parcelas else ultima_parcela

                cur.execute("""
                    INSERT INTO parcelas_pagar
                        (contas_a_pagar_id, numero_parcela, data_vencimento, valor_parcela)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (contas_a_pagar_id, numero_parcela) DO NOTHING
                """, (contas_a_pagar_id, p, vencimento, v_parcela))

            # Inserir classificação de despesa (1 a 2 categorias)
            qtd_cat = random.randint(1, 2)
            cats = random.sample(list(despesas_ids.keys()), qtd_cat)
            for cat in cats:
                cur.execute("""
                    INSERT INTO contas_a_pagar_tipo_despesa (contas_a_pagar_id, tipo_despesa_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (contas_a_pagar_id, despesas_ids[cat]))

            contador += 1
            if contador % 20 == 0:
                print(f"  {contador}/200 notas inseridas...")

        conn.commit()
        print(f"\n✅ {contador} notas fiscais inseridas com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro durante a inserção: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("🚀 Populando banco com 200 notas fiscais...\n")
    seed()
    print("\n🎉 Finalizado!")