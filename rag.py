"""
============================================================
MÓDULO RAG - Agente Inteligente de Consulta
N3 - Etapa 3
============================================================

Implementa duas estratégias de RAG (Retrieval-Augmented Generation):

1. RAG SIMPLES (Text-to-SQL):
   - O LLM (Groq/Llama) recebe a pergunta + o schema do banco
   - Gera uma consulta SQL (somente SELECT, com validação de segurança)
   - A query é executada no PostgreSQL
   - O LLM elabora uma resposta em linguagem natural com os dados retornados

2. RAG EMBEDDINGS:
   - Os registros de contas_a_pagar / contas_a_receber são transformados
     em texto descritivo e convertidos em vetores (embeddings) usando
     sentence-transformers (modelo local, sem custo de API)
   - Os vetores são armazenados em um arquivo .pkl (cache em memória/disco)
   - A pergunta do usuário também é vetorizada
   - Os registros mais similares (cosine similarity) são recuperados
   - O LLM elabora a resposta final com base nesse contexto

O endpoint /perguntar decide automaticamente qual estratégia usar,
ou tenta o RAG_SIMPLES primeiro e cai para EMBEDDINGS em caso de falha.
============================================================
"""

import os
import re
import pickle
import numpy as np
from datetime import date, datetime
from decimal import Decimal

import psycopg2
import psycopg2.extras

# ============================================================
# CONFIGURAÇÕES
# ============================================================
EMBEDDINGS_CACHE_PATH = os.getenv("EMBEDDINGS_CACHE_PATH", "embeddings_cache.pkl")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Schema resumido — descreve as tabelas para o LLM gerar SQL correto.
SCHEMA_DESCRICAO = """
TABELAS DISPONÍVEIS (PostgreSQL):

fornecedor(id, razao_social, fantasia, cnpj, ativo, criado_em)
faturado(id, nome_completo, cpf, ativo, criado_em)
cliente(id, razao_social, fantasia, cnpj, cpf, ativo, criado_em)
tipo_despesa(id, nome, descricao, ativo)
tipo_receita(id, nome, descricao, ativo)

contas_a_pagar(id, fornecedor_id, faturado_id, numero_nota_fiscal, serie_nota_fiscal,
                data_emissao, descricao_produtos, valor_total, ativo, criado_em)

contas_a_pagar_tipo_despesa(id, contas_a_pagar_id, tipo_despesa_id)

parcelas_pagar(id, contas_a_pagar_id, numero_parcela, data_vencimento,
               valor_parcela, data_pagamento, valor_pago)

contas_a_receber(id, cliente_id, faturado_id, numero_documento,
                  data_emissao, descricao, valor_total, ativo, criado_em)

contas_a_receber_tipo_receita(id, contas_a_receber_id, tipo_receita_id)

parcelas_receber(id, contas_a_receber_id, numero_parcela, data_vencimento,
                  valor_parcela, data_recebimento, valor_recebido)

VIEWS ÚTEIS (já fazem os JOINs):
vw_contas_a_pagar_completo(id, numero_nota_fiscal, serie_nota_fiscal, data_emissao,
    descricao_produtos, valor_total, ativo, criado_em, fornecedor_razao_social,
    fornecedor_fantasia, fornecedor_cnpj, faturado_nome, faturado_cpf, qtd_parcelas,
    primeiro_vencimento, ultimo_vencimento, total_parcelas, categorias_despesa)

vw_contas_a_receber_completo(id, numero_documento, data_emissao, descricao, valor_total,
    ativo, criado_em, cliente_razao_social, cliente_fantasia, cliente_cnpj, cliente_cpf,
    faturado_nome, faturado_cpf, qtd_parcelas, primeiro_vencimento, ultimo_vencimento,
    total_parcelas, categorias_receita)

vw_parcelas_pagar_em_aberto(id, numero_parcela, data_vencimento, valor_parcela,
    vencida, numero_nota_fiscal, fornecedor)

vw_parcelas_receber_em_aberto(id, numero_parcela, data_vencimento, valor_parcela,
    vencida, numero_documento, cliente)
"""

# ============================================================
# UTILITÁRIOS
# ============================================================

def _serializar(valor):
    """Converte tipos não-JSON (Decimal, date, datetime) para tipos serializáveis."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def _linha_para_dict(row, colnames):
    return {col: _serializar(row[i]) for i, col in enumerate(colnames)}


# ============================================================
# RAG SIMPLES — TEXT-TO-SQL
# ============================================================

PROMPT_TEXT_TO_SQL = """Você é um especialista em SQL PostgreSQL. Sua tarefa é converter uma pergunta em
linguagem natural sobre um sistema financeiro agrícola em UMA única consulta SQL.

{schema}

REGRAS OBRIGATÓRIAS:
- Gere APENAS comandos SELECT (nunca INSERT, UPDATE, DELETE, DROP, ALTER).
- Use preferencialmente as VIEWS (vw_contas_a_pagar_completo, vw_contas_a_receber_completo,
  vw_parcelas_pagar_em_aberto, vw_parcelas_receber_em_aberto) quando possível.
- Sempre filtre por ativo = TRUE quando a tabela tiver essa coluna, a menos que o usuário
  peça explicitamente registros inativos.
- Use LIMIT 50 caso a pergunta não especifique quantidade.
- Retorne APENAS a query SQL, sem explicações, sem markdown, sem ponto e vírgula no final.

PERGUNTA: {pergunta}

SQL:"""


PROMPT_RESPOSTA_FINAL = """Você é um assistente financeiro de uma propriedade agrícola.
Com base nos dados retornados do banco de dados abaixo, responda à pergunta do usuário
de forma clara, objetiva e em português do Brasil. Use valores monetários no formato R$.
Se não houver dados, informe isso educadamente.

PERGUNTA DO USUÁRIO: {pergunta}

DADOS RETORNADOS (JSON):
{dados}

RESPOSTA:"""


# Palavras-chave proibidas para validação de segurança da query gerada pelo LLM
_PALAVRAS_PROIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|--|;)\b",
    re.IGNORECASE
)


def validar_sql_seguro(sql: str) -> str:
    """
    Valida que a SQL gerada pelo LLM é segura (somente leitura).
    Levanta ValueError se detectar algo suspeito.
    Retorna a SQL limpa.
    """
    sql_limpo = sql.strip()

    # Remove markdown se vier
    sql_limpo = sql_limpo.replace("```sql", "").replace("```", "").strip()

    if not sql_limpo:
        raise ValueError("O modelo não retornou nenhuma SQL.")

    if not sql_limpo.lower().startswith("select"):
        raise ValueError("Apenas consultas SELECT são permitidas.")

    if _PALAVRAS_PROIBIDAS.search(sql_limpo):
        raise ValueError("A consulta gerada contém comandos não permitidos.")

    # Garante LIMIT para evitar respostas gigantes
    if "limit" not in sql_limpo.lower():
        sql_limpo += " LIMIT 50"

    return sql_limpo


def rag_simples(pergunta: str, llm_chat_fn, get_conn_fn) -> dict:
    """
    Executa o RAG Simples (Text-to-SQL).

    Args:
        pergunta: pergunta do usuário em português
        llm_chat_fn: função(prompt: str) -> str que chama o LLM (Groq/Llama)
        get_conn_fn: função() -> conexão psycopg2

    Returns:
        dict com: tipo, sql_gerada, dados, resposta
    """
    # 1. Gerar SQL via LLM
    prompt_sql = PROMPT_TEXT_TO_SQL.format(schema=SCHEMA_DESCRICAO, pergunta=pergunta)
    sql_bruta = llm_chat_fn(prompt_sql)
    sql_validada = validar_sql_seguro(sql_bruta)

    # 2. Executar no banco
    conn = get_conn_fn()
    try:
        cur = conn.cursor()
        cur.execute(sql_validada)
        colnames = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall() if cur.description else []
        dados = [_linha_para_dict(r, colnames) for r in rows]
    finally:
        conn.close()

    # 3. Elaborar resposta final via LLM
    import json as _json
    dados_json = _json.dumps(dados, ensure_ascii=False, default=str)[:4000]
    prompt_resposta = PROMPT_RESPOSTA_FINAL.format(pergunta=pergunta, dados=dados_json)
    resposta = llm_chat_fn(prompt_resposta)

    return {
        "tipo": "rag_simples",
        "sql_gerada": sql_validada,
        "dados": dados,
        "total_registros": len(dados),
        "resposta": resposta.strip(),
    }


# ============================================================
# RAG EMBEDDINGS — BUSCA SEMÂNTICA
# ============================================================

_modelo_embeddings = None  # carregado de forma lazy


def _carregar_modelo_embeddings():
    """Carrega o modelo de embeddings local (sentence-transformers), sob demanda."""
    global _modelo_embeddings
    if _modelo_embeddings is None:
        from sentence_transformers import SentenceTransformer
        print(f"[RAG] Carregando modelo de embeddings: {EMBEDDING_MODEL_NAME} (pode levar um tempo na 1ª vez)")
        _modelo_embeddings = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _modelo_embeddings


def _texto_contas_a_pagar(row: dict) -> str:
    """Converte um registro de contas_a_pagar (view completa) em texto descritivo."""
    partes = [
        f"Conta a pagar NF {row.get('numero_nota_fiscal')}",
        f"fornecedor {row.get('fornecedor_razao_social')}",
    ]
    if row.get("fornecedor_cnpj"):
        partes.append(f"CNPJ {row.get('fornecedor_cnpj')}")
    if row.get("faturado_nome"):
        partes.append(f"faturado para {row.get('faturado_nome')}")
    if row.get("descricao_produtos"):
        partes.append(f"produtos: {row.get('descricao_produtos')}")
    if row.get("categorias_despesa"):
        partes.append(f"categoria de despesa: {row.get('categorias_despesa')}")
    partes.append(f"valor total R$ {row.get('valor_total')}")
    partes.append(f"emitida em {row.get('data_emissao')}")
    if row.get("primeiro_vencimento"):
        partes.append(f"vencimento {row.get('primeiro_vencimento')}")
    return ". ".join(str(p) for p in partes)


def _texto_contas_a_receber(row: dict) -> str:
    """Converte um registro de contas_a_receber (view completa) em texto descritivo."""
    partes = [
        f"Conta a receber documento {row.get('numero_documento')}",
        f"cliente {row.get('cliente_razao_social')}",
    ]
    if row.get("cliente_cnpj"):
        partes.append(f"CNPJ {row.get('cliente_cnpj')}")
    if row.get("faturado_nome"):
        partes.append(f"faturado para {row.get('faturado_nome')}")
    if row.get("descricao"):
        partes.append(f"descrição: {row.get('descricao')}")
    if row.get("categorias_receita"):
        partes.append(f"categoria de receita: {row.get('categorias_receita')}")
    partes.append(f"valor total R$ {row.get('valor_total')}")
    partes.append(f"emitida em {row.get('data_emissao')}")
    if row.get("primeiro_vencimento"):
        partes.append(f"vencimento {row.get('primeiro_vencimento')}")
    return ". ".join(str(p) for p in partes)


def construir_indice_embeddings(get_conn_fn, salvar_em_disco: bool = True) -> dict:
    """
    Lê contas_a_pagar e contas_a_receber do banco, gera embeddings de cada
    registro e mantém em cache (memória + arquivo .pkl).

    Returns:
        dict com 'documentos' (lista de dicts: texto + metadados) e 'vetores' (np.array)
    """
    modelo = _carregar_modelo_embeddings()

    conn = get_conn_fn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT * FROM vw_contas_a_pagar_completo WHERE ativo = TRUE")
        contas_pagar = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM vw_contas_a_receber_completo WHERE ativo = TRUE")
        contas_receber = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    documentos = []

    for row in contas_pagar:
        documentos.append({
            "texto": _texto_contas_a_pagar(row),
            "origem": "contas_a_pagar",
            "id": row.get("id"),
            "dados": {k: _serializar(v) for k, v in row.items()},
        })

    for row in contas_receber:
        documentos.append({
            "texto": _texto_contas_a_receber(row),
            "origem": "contas_a_receber",
            "id": row.get("id"),
            "dados": {k: _serializar(v) for k, v in row.items()},
        })

    if documentos:
        textos = [d["texto"] for d in documentos]
        vetores = modelo.encode(textos, convert_to_numpy=True, normalize_embeddings=True)
    else:
        vetores = np.zeros((0, 384), dtype=np.float32)

    indice = {"documentos": documentos, "vetores": vetores}

    if salvar_em_disco:
        try:
            with open(EMBEDDINGS_CACHE_PATH, "wb") as f:
                pickle.dump(indice, f)
            print(f"[RAG] Índice de embeddings salvo em {EMBEDDINGS_CACHE_PATH} ({len(documentos)} docs)")
        except Exception as e:
            print(f"[RAG] Aviso: não foi possível salvar cache de embeddings: {e}")

    return indice


def carregar_indice_embeddings(get_conn_fn, forcar_reconstrucao: bool = False) -> dict:
    """Carrega o índice de embeddings do disco, ou reconstrói se não existir."""
    if not forcar_reconstrucao and os.path.exists(EMBEDDINGS_CACHE_PATH):
        try:
            with open(EMBEDDINGS_CACHE_PATH, "rb") as f:
                indice = pickle.load(f)
            print(f"[RAG] Índice de embeddings carregado do cache ({len(indice['documentos'])} docs)")
            return indice
        except Exception as e:
            print(f"[RAG] Falha ao carregar cache, reconstruindo: {e}")

    return construir_indice_embeddings(get_conn_fn)


def buscar_documentos_similares(pergunta: str, indice: dict, top_k: int = 5) -> list:
    """Retorna os top_k documentos mais similares à pergunta (cosine similarity)."""
    if not indice["documentos"]:
        return []

    modelo = _carregar_modelo_embeddings()
    vetor_pergunta = modelo.encode([pergunta], convert_to_numpy=True, normalize_embeddings=True)[0]

    vetores = indice["vetores"]
    similaridades = vetores @ vetor_pergunta  # cosine similarity (já normalizados)

    top_indices = np.argsort(similaridades)[::-1][:top_k]

    resultados = []
    for i in top_indices:
        doc = indice["documentos"][int(i)]
        resultados.append({
            "score": float(similaridades[i]),
            "origem": doc["origem"],
            "id": doc["id"],
            "texto": doc["texto"],
            "dados": doc["dados"],
        })
    return resultados


PROMPT_RESPOSTA_EMBEDDINGS = """Você é um assistente financeiro de uma propriedade agrícola.
Abaixo estão os registros mais relevantes encontrados por busca semântica no histórico
financeiro, com base na pergunta do usuário. Use-os para responder de forma clara e
objetiva, em português do Brasil. Use valores monetários no formato R$.
Se os registros não parecerem relacionados à pergunta, informe que não encontrou
informações relevantes.

PERGUNTA DO USUÁRIO: {pergunta}

REGISTROS RELEVANTES ENCONTRADOS:
{contexto}

RESPOSTA:"""


def rag_embeddings(pergunta: str, llm_chat_fn, get_conn_fn, indice_cache: dict, top_k: int = 5) -> dict:
    """
    Executa o RAG por Embeddings (busca semântica).

    Args:
        pergunta: pergunta do usuário
        llm_chat_fn: função(prompt) -> str para chamar o LLM
        get_conn_fn: função para obter conexão psycopg2
        indice_cache: dict mutável usado como cache do índice (chave "indice")
        top_k: número de documentos a recuperar

    Returns:
        dict com tipo, documentos_recuperados, resposta
    """
    if indice_cache.get("indice") is None:
        indice_cache["indice"] = carregar_indice_embeddings(get_conn_fn)

    indice = indice_cache["indice"]
    resultados = buscar_documentos_similares(pergunta, indice, top_k=top_k)

    contexto = "\n".join(f"- {r['texto']} (similaridade: {r['score']:.2f})" for r in resultados) \
        or "Nenhum registro encontrado."

    prompt_resposta = PROMPT_RESPOSTA_EMBEDDINGS.format(pergunta=pergunta, contexto=contexto)
    resposta = llm_chat_fn(prompt_resposta)

    return {
        "tipo": "rag_embeddings",
        "documentos_recuperados": [
            {"origem": r["origem"], "id": r["id"], "texto": r["texto"], "score": round(r["score"], 4)}
            for r in resultados
        ],
        "resposta": resposta.strip(),
    }


# ============================================================
# ORQUESTRADOR HÍBRIDO
# ============================================================

def perguntar(pergunta: str, llm_chat_fn, get_conn_fn, indice_cache: dict, modo: str = "auto") -> dict:
    """
    Ponto de entrada principal do agente RAG híbrido.

    modo:
        - "sql": força RAG Simples (Text-to-SQL)
        - "embeddings": força RAG Embeddings (busca semântica)
        - "auto" (padrão): tenta SQL primeiro; se falhar, cai para embeddings
    """
    pergunta = (pergunta or "").strip()
    if not pergunta:
        raise ValueError("A pergunta não pode estar vazia.")

    if modo == "embeddings":
        return rag_embeddings(pergunta, llm_chat_fn, get_conn_fn, indice_cache)

    if modo == "sql":
        return rag_simples(pergunta, llm_chat_fn, get_conn_fn)

    # modo "auto": tenta SQL, cai para embeddings em caso de erro
    try:
        return rag_simples(pergunta, llm_chat_fn, get_conn_fn)
    except Exception as e:
        print(f"[RAG] RAG Simples falhou ({e}), usando RAG Embeddings como fallback...")
        resultado = rag_embeddings(pergunta, llm_chat_fn, get_conn_fn, indice_cache)
        resultado["aviso"] = f"RAG simples (SQL) falhou, resposta gerada via busca semântica. Detalhe: {e}"
        return resultado
