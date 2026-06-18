from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import pdfplumber
import psycopg2
import psycopg2.extras
import json
import os
import tempfile
import hashlib
from dotenv import load_dotenv
from datetime import date

import rag


class DuplicateRegistroError(Exception):
    """Erro interno para registro duplicado de contas a pagar."""
    pass

load_dotenv()

app = FastAPI(title="Extrator NF Inteligente - UniRV")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://financeiro:financeiro123@localhost:5432/financeiro")

if not GROQ_API_KEY:
    print("[ERRO] GROQ_API_KEY nao encontrada")
else:
    print("[OK] GROQ API OK")

client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# BANCO DE DADOS
# ============================================================
def get_conn():
    """Retorna uma conexão ao PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def db_disponivel() -> bool:
    """Verifica se o banco está acessível."""
    try:
        conn = get_conn()
        conn.close()
        return True
    except Exception:
        return False

# ============================================================
# PROMPT IA
# ============================================================
PROMPT = """
Extraia os dados da nota fiscal e retorne APENAS JSON válido, sem markdown, sem explicações:

{
  "fornecedor": {
    "razaoSocial": "",
    "fantasia": null,
    "cnpj": ""
  },
  "faturado": {
    "nomeCompleto": null,
    "cpf": null
  },
  "numeroNotaFiscal": "",
  "serieNotaFiscal": null,
  "dataEmissao": "YYYY-MM-DD",
  "descricaoProdutos": "",
  "parcelas": [
    {
      "numero": 1,
      "dataVencimento": "YYYY-MM-DD",
      "valor": 0.00
    }
  ],
  "valorTotal": 0.00,
  "classificacoesDespesa": ["CATEGORIA"]
}

Categorias válidas para classificacoesDespesa:
- INSUMOS AGRÍCOLAS
- MANUTENÇÃO E OPERAÇÃO
- RECURSOS HUMANOS
- SERVIÇOS OPERACIONAIS
- INFRAESTRUTURA E UTILIDADES
- ADMINISTRATIVAS
- SEGUROS E PROTEÇÃO
- IMPOSTOS E TAXAS
- INVESTIMENTOS

Use null para campos ausentes na nota. Se não houver parcelas, coloque o valor total em uma única parcela com a data de emissão como vencimento.
"""

# ============================================================
# EXTRAÇÃO DE TEXTO DO PDF
# ============================================================
def extrair_texto(path):
    texto = ""
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            texto += p.extract_text() or ""
    return texto


# ============================================================
# IA: SELEÇÃO AUTOMÁTICA DO MODELO GROQ
# ============================================================
def obter_modelo_valido():
    try:
        modelos = client.models.list().data
        preferidos = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]
        candidatos = [
            m.id for m in modelos
            if "llama" in m.id.lower() and "prompt-guard" not in m.id.lower()
        ]
        print("[INFO] Modelos encontrados:", candidatos)
        if not candidatos:
            raise Exception("Nenhum modelo Llama disponível")
        for nome in preferidos:
            if nome in candidatos:
                return nome
        return candidatos[0]
    except Exception as e:
        raise Exception(f"Erro ao listar modelos: {e}")


def chamar_llama(texto_pdf):
    modelo = obter_modelo_valido()
    print(f"[INFO] Usando modelo: {modelo}")
    max_chars = 2500
    prompt = PROMPT + "\n\nNOTA:\n" + texto_pdf[:max_chars]
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"Erro IA: {str(e)}")


def limpar_json(texto):
    texto = texto.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        snippet = texto[:500]
        raise ValueError(f"JSON invalido: {e}. Trecho: {snippet}")


# ============================================================
# IA: CHAMADA GENÉRICA DE TEXTO (usada pelo Agente RAG)
# ============================================================
def chamar_llm_texto(prompt: str) -> str:
    """
    Envia um prompt de texto livre ao LLM (Groq/Llama) e retorna a resposta.
    Usada pelo módulo rag.py para Text-to-SQL e elaboração de respostas.
    """
    modelo = obter_modelo_valido()
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(500, f"Erro IA (RAG): {str(e)}")


# Cache em memória do índice de embeddings (carregado/reconstruído sob demanda)
_rag_indice_cache = {"indice": None}

# ============================================================
# LÓGICA DE PERSISTÊNCIA NO BANCO
# ============================================================
def salvar_no_banco(data: dict) -> dict:
    """
    Persiste os dados extraídos da NF no PostgreSQL.
    Faz verificação de existência de fornecedor, faturado e classificações de despesa.
    Retorna um dict com os IDs gerados e mensagens de consulta.
    """
    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        consulta = []

        # ── 1. FORNECEDOR (verifica por CNPJ) ─────────────────────────────
        fornecedor = data.get("fornecedor", {})
        cnpj = (fornecedor.get("cnpj") or "").strip()
        razao_social = (fornecedor.get("razaoSocial") or "Não identificado").strip()
        fantasia = (fornecedor.get("fantasia") or "").strip() or None

        if cnpj:
            cur.execute("SELECT id FROM fornecedor WHERE cnpj = %s", (cnpj,))
            row = cur.fetchone()
        else:
            cur.execute("SELECT id FROM fornecedor WHERE lower(razao_social) = lower(%s) LIMIT 1", (razao_social,))
            row = cur.fetchone()

        if row:
            fornecedor_id = row[0]
            fornecedor_status = f"EXISTE – ID: {fornecedor_id}"
        else:
            if not cnpj:
                placeholder = hashlib.sha1(razao_social.lower().encode()).hexdigest()[:12]
                cnpj = f"MISSING-{placeholder}"
            cur.execute("""
                INSERT INTO fornecedor (razao_social, fantasia, cnpj)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (razao_social, fantasia, cnpj))
            fornecedor_id = cur.fetchone()[0]
            fornecedor_status = f"CRIADO – ID: {fornecedor_id}"

        consulta.append("FORNECEDOR:")
        consulta.append(razao_social)
        consulta.append(f"CNPJ: {cnpj or 'NÃO INFORMADO'}")
        consulta.append(fornecedor_status)

        # ── 2. FATURADO (verifica por CPF ou nome) ─────────────────────────
        faturado_id = None
        faturado = data.get("faturado", {})
        nome_faturado = (faturado.get("nomeCompleto") or "").strip() or None
        cpf_faturado = (faturado.get("cpf") or "").strip() or None

        if nome_faturado:
            if cpf_faturado:
                cur.execute("SELECT id FROM faturado WHERE cpf = %s", (cpf_faturado,))
                row = cur.fetchone()
            else:
                cur.execute(
                    "SELECT id FROM faturado WHERE lower(nome_completo) = lower(%s) AND cpf IS NULL LIMIT 1",
                    (nome_faturado,)
                )
                row = cur.fetchone()

            if row:
                faturado_id = row[0]
                faturado_status = f"EXISTE – ID: {faturado_id}"
            else:
                cur.execute("""
                    INSERT INTO faturado (nome_completo, cpf)
                    VALUES (%s, %s)
                    RETURNING id
                """, (nome_faturado, cpf_faturado))
                faturado_id = cur.fetchone()[0]
                faturado_status = f"CRIADO – ID: {faturado_id}"
        else:
            faturado_status = "NÃO INFORMADO"

        consulta.append("FATURADO:")
        consulta.append(nome_faturado or "NÃO INFORMADO")
        consulta.append(f"CPF: {cpf_faturado or 'NÃO INFORMADO'}")
        consulta.append(faturado_status)

        # ── 3. CONTAS_A_PAGAR ─────────────────────────────────────────────
        numero_nf = (data.get("numeroNotaFiscal") or "S/N").strip()
        serie_nf = (data.get("serieNotaFiscal") or "").strip() or None
        data_emissao = data.get("dataEmissao") or str(date.today())
        descricao = (data.get("descricaoProdutos") or "").strip() or None
        valor_total = float(data.get("valorTotal") or 0)

        cur.execute(
            "SELECT id FROM contas_a_pagar WHERE fornecedor_id = %s AND numero_nota_fiscal = %s AND COALESCE(serie_nota_fiscal, '') = COALESCE(%s, '') AND ativo = TRUE",
            (fornecedor_id, numero_nf, serie_nf)
        )
        row = cur.fetchone()
        if row:
            raise DuplicateRegistroError(
                f"Conta a pagar já existente para NF {numero_nf} e fornecedor {razao_social}."
            )

        cur.execute("""
            INSERT INTO contas_a_pagar
                (fornecedor_id, faturado_id, numero_nota_fiscal, serie_nota_fiscal,
                 data_emissao, descricao_produtos, valor_total)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (fornecedor_id, faturado_id, numero_nf, serie_nf,
              data_emissao, descricao, valor_total))
        contas_a_pagar_id = cur.fetchone()[0]

        # ── 4. PARCELAS ───────────────────────────────────────────────────
        parcelas = data.get("parcelas") or []
        if not parcelas:
            parcelas = [{"numero": 1, "dataVencimento": data_emissao, "valor": valor_total}]

        for p in parcelas:
            cur.execute("""
                INSERT INTO parcelas_pagar
                    (contas_a_pagar_id, numero_parcela, data_vencimento, valor_parcela)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (contas_a_pagar_id, numero_parcela) DO NOTHING
            """, (
                contas_a_pagar_id,
                int(p.get("numero") or 1),
                p.get("dataVencimento") or data_emissao,
                float(p.get("valor") or 0)
            ))

        # ── 5. TIPOS DE DESPESA ───────────────────────────────────────────
        classificacoes = data.get("classificacoesDespesa") or []
        if not classificacoes:
            classificacoes = ["SEM CLASSIFICAÇÃO"]

        for cat in classificacoes:
            nome_despesa = cat.strip().upper()
            if not nome_despesa:
                continue

            cur.execute("SELECT id FROM tipo_despesa WHERE nome = %s", (nome_despesa,))
            row = cur.fetchone()
            if row:
                tipo_despesa_id = row[0]
                tipo_despesa_status = f"EXISTE – ID: {tipo_despesa_id}"
            else:
                cur.execute(
                    "INSERT INTO tipo_despesa (nome, descricao) VALUES (%s, %s) RETURNING id",
                    (nome_despesa, nome_despesa)
                )
                tipo_despesa_id = cur.fetchone()[0]
                tipo_despesa_status = f"CRIADO – ID: {tipo_despesa_id}"

            cur.execute("""
                INSERT INTO contas_a_pagar_tipo_despesa (contas_a_pagar_id, tipo_despesa_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (contas_a_pagar_id, tipo_despesa_id))

            consulta.append("DESPESA:")
            consulta.append(nome_despesa)
            consulta.append(tipo_despesa_status)

        conn.commit()
        return {
            "contas_a_pagar_id": contas_a_pagar_id,
            "fornecedor_id": fornecedor_id,
            "faturado_id": faturado_id,
            "parcelas_salvas": len(parcelas),
            "consulta": consulta,
            "mensagem": "Registro lançado com sucesso."
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# ============================================================
# ENDPOINTS
# ============================================================

@app.post("/extrair")
async def extrair(file: UploadFile = File(...)):
    """Extrai dados de uma NF em PDF usando IA (Groq/Llama)."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Envie um PDF")
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY não configurada")

    tmp_path = None
    try:
        print(f"[INFO] Recebido: {file.filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        texto = extrair_texto(tmp_path)
        if not texto.strip():
            raise Exception("PDF vazio ou ilegível")

        resposta = chamar_llama(texto)
        print("[INFO] Resposta IA:", resposta[:150])

        data = limpar_json(resposta)
        return {"success": True, "data": data}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao processar: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/salvar")
async def salvar(payload: dict):
    """Persiste os dados extraídos da NF no PostgreSQL."""
    if not db_disponivel():
        raise HTTPException(
            503,
            "Banco de dados indisponível. Verifique se o Docker está rodando: docker-compose up -d"
        )
    try:
        resultado = salvar_no_banco(payload)
        return {"success": True, "resultado": resultado}
    except DuplicateRegistroError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao salvar: {e}")


@app.get("/contas-a-pagar")
def listar_contas(limite: int = 50, pagina: int = 1):
    """Lista as contas a pagar salvas no banco (com paginação simples)."""
    if not db_disponivel():
        raise HTTPException(503, "Banco de dados indisponível.")
    try:
        offset = (pagina - 1) * limite
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Total de registros (incluindo inativos para histórico completo)
        cur.execute("SELECT COUNT(*) AS total FROM contas_a_pagar")
        total = cur.fetchone()["total"]

        # Registros paginados via view (incluindo inativos)
        cur.execute("""
            SELECT
                id,
                numero_nota_fiscal,
                serie_nota_fiscal,
                data_emissao,
                descricao_produtos,
                valor_total,
                criado_em,
                fornecedor_razao_social,
                fornecedor_cnpj,
                faturado_nome,
                qtd_parcelas,
                primeiro_vencimento,
                ultimo_vencimento,
                categorias_despesa,
                ativo
            FROM vw_contas_a_pagar_completo
            ORDER BY criado_em DESC
            LIMIT %s OFFSET %s
        """, (limite, offset))

        registros = cur.fetchall()
        cur.close()
        conn.close()

        # Serializar datas
        for r in registros:
            for k, v in r.items():
                if isinstance(v, date):
                    r[k] = v.isoformat()

        return {
            "total": total,
            "pagina": pagina,
            "limite": limite,
            "registros": [dict(r) for r in registros]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao listar: {e}")


@app.delete("/contas-a-pagar/{conta_id}")
def excluir_conta(conta_id: int):
    """Marca uma conta a pagar como inativa em vez de deletar registros do banco."""
    if not db_disponivel():
        raise HTTPException(
            503,
            "Banco de dados indisponível. Verifique se o Docker está rodando: docker-compose up -d"
        )
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE contas_a_pagar SET ativo = FALSE WHERE id = %s AND ativo = TRUE",
            (conta_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Registro não encontrado ou já excluído.")
        conn.commit()
        return {"success": True, "message": "Registro inativado com sucesso."}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Erro ao excluir: {e}")
    finally:
        cur.close()
        conn.close()


@app.delete("/contas-a-pagar")
def limpar_historico():
    """Remove permanentemente todos os registros do histórico (ativos e inativos)."""
    if not db_disponivel():
        raise HTTPException(
            503,
            "Banco de dados indisponível. Verifique se o Docker está rodando: docker-compose up -d"
        )
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM contas_a_pagar")
        registros_removidos = cur.rowcount
        conn.commit()
        return {"success": True, "message": f"Histórico limpo com sucesso. {registros_removidos} registros removidos."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Erro ao limpar histórico: {e}")
    finally:
        cur.close()
        conn.close()


@app.get("/db-status")
def db_status():
    """Verifica se o banco de dados está acessível."""
    ok = db_disponivel()
    return {
        "banco_disponivel": ok,
        "database_url": DATABASE_URL.split("@")[-1] if ok else "inacessível"
    }


@app.get("/test")
def test():
    try:
        modelos = client.models.list().data
        return {"modelos": [m.id for m in modelos]}
    except Exception as e:
        return {"erro": str(e)}


@app.get("/health")
def health():
    return {"status": "ok", "banco": db_disponivel()}


# ============================================================
# N3 - ETAPA 3: AGENTE INTELIGENTE (RAG)
# ============================================================

class PerguntaPayload(BaseModel):
    pergunta: str
    modo: str = "auto"  # "auto" | "sql" | "embeddings"


@app.post("/perguntar")
def perguntar(payload: PerguntaPayload):
    """
    Agente Inteligente de Consulta (RAG Híbrido).

    - modo "sql": RAG Simples -> o LLM gera SQL (somente SELECT) com base no
      schema do banco, executa a consulta e elabora a resposta.
    - modo "embeddings": RAG Embeddings -> busca semântica nos registros de
      contas a pagar/receber via embeddings locais (sentence-transformers),
      e o LLM elabora a resposta com o contexto recuperado.
    - modo "auto" (padrão): tenta SQL primeiro; se falhar, cai para embeddings.
    """
    if not db_disponivel():
        raise HTTPException(
            503,
            "Banco de dados indisponível. Verifique se o Docker está rodando: docker-compose up -d"
        )
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY não configurada")

    try:
        resultado = rag.perguntar(
            pergunta=payload.pergunta,
            llm_chat_fn=chamar_llm_texto,
            get_conn_fn=get_conn,
            indice_cache=_rag_indice_cache,
            modo=payload.modo,
        )
        return {"success": True, **resultado}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao processar pergunta: {e}")


@app.post("/perguntar/reindexar")
def reindexar_embeddings():
    """
    Força a reconstrução do índice de embeddings (RAG Embeddings) a partir
    do estado atual do banco de dados. Útil após salvar novas notas fiscais.
    """
    if not db_disponivel():
        raise HTTPException(
            503,
            "Banco de dados indisponível. Verifique se o Docker está rodando: docker-compose up -d"
        )
    try:
        indice = rag.construir_indice_embeddings(get_conn)
        _rag_indice_cache["indice"] = indice
        return {
            "success": True,
            "total_documentos": len(indice["documentos"]),
            "mensagem": "Índice de embeddings reconstruído com sucesso."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao reindexar: {e}")
