import { useState, useRef, useEffect, useCallback } from "react"
import "./App.css"

const API_URL = "http://localhost:8000"

// ────────────────────────────────────────────────────────────
// HELPERS DE FORMATAÇÃO
// ────────────────────────────────────────────────────────────
function formatCNPJ(v) {
    if (!v) return "—"
    const d = v.replace(/\D/g, "")
    if (d.length === 14) return d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5")
    return v
}

function formatCPF(v) {
    if (!v) return "—"
    const d = v.replace(/\D/g, "")
    if (d.length === 11) return d.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, "$1.$2.$3-$4")
    return v
}

function formatDate(v) {
    if (!v) return "—"
    const raw = String(v).trim()
    if (raw.includes("/")) return raw
    const [y, m, d] = raw.split("-")
    if (!y || !m || !d) return raw
    return `${d}/${m}/${y}`
}

function formatCurrency(v) {
    if (v == null) return "—"
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v)
}

// ────────────────────────────────────────────────────────────
// COMPONENTE: JSON VIEWER
// ────────────────────────────────────────────────────────────
function JsonViewer({ data }) {
    const [copied, setCopied] = useState(false)
    const json = JSON.stringify(data, null, 2)

    const handleCopy = () => {
        navigator.clipboard.writeText(json)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="json-viewer">
            <div className="json-header">
                <span className="json-title">
                    <span className="json-icon">&lt;/&gt;</span> Dados em JSON
                </span>
                <button className="copy-btn" onClick={handleCopy}>
                    {copied ? "✓ Copiado!" : "⧉ Copiar JSON"}
                </button>
            </div>
            <pre className="json-pre">{json}</pre>
        </div>
    )
}

// ────────────────────────────────────────────────────────────
// COMPONENTE: FORMATTED VIEWER (resultado da extração)
// ────────────────────────────────────────────────────────────
function FormattedViewer({ data }) {
    const d = data
    return (
        <div className="formatted-viewer">
            <div className="info-grid">
                <div className="info-section">
                    <h3 className="section-title">
                        <span className="dot dot-green" /> Fornecedor
                    </h3>
                    <div className="info-row"><span>Razão Social</span><strong>{d.fornecedor?.razaoSocial || "—"}</strong></div>
                    <div className="info-row"><span>Fantasia</span><strong>{d.fornecedor?.fantasia || "—"}</strong></div>
                    <div className="info-row"><span>CNPJ</span><strong>{formatCNPJ(d.fornecedor?.cnpj)}</strong></div>
                </div>

                <div className="info-section">
                    <h3 className="section-title">
                        <span className="dot dot-blue" /> Faturado
                    </h3>
                    <div className="info-row"><span>Nome Completo</span><strong>{d.faturado?.nomeCompleto || "—"}</strong></div>
                    <div className="info-row"><span>CPF</span><strong>{formatCPF(d.faturado?.cpf)}</strong></div>
                </div>

                <div className="info-section">
                    <h3 className="section-title">
                        <span className="dot dot-amber" /> Nota Fiscal
                    </h3>
                    <div className="info-row"><span>Número</span><strong>{d.numeroNotaFiscal || "—"}</strong></div>
                    <div className="info-row"><span>Série</span><strong>{d.serieNotaFiscal || "—"}</strong></div>
                    <div className="info-row"><span>Emissão</span><strong>{formatDate(d.dataEmissao)}</strong></div>
                    <div className="info-row"><span>Valor Total</span><strong className="valor-total">{formatCurrency(d.valorTotal)}</strong></div>
                </div>

                <div className="info-section full-width">
                    <h3 className="section-title">
                        <span className="dot dot-purple" /> Produtos / Serviços
                    </h3>
                    <p className="descricao-text">{d.descricaoProdutos || "—"}</p>
                </div>

                <div className="info-section">
                    <h3 className="section-title">
                        <span className="dot dot-red" /> Parcelas
                    </h3>
                    {d.parcelas && d.parcelas.length > 0 ? (
                        <table className="parcelas-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Vencimento</th>
                                    <th>Valor</th>
                                </tr>
                            </thead>
                            <tbody>
                                {d.parcelas.map((p, i) => (
                                    <tr key={i}>
                                        <td>{p.numero}</td>
                                        <td>{formatDate(p.dataVencimento)}</td>
                                        <td>{formatCurrency(p.valor)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : <p>—</p>}
                </div>

                <div className="info-section">
                    <h3 className="section-title">
                        <span className="dot dot-teal" /> Classificação de Despesa
                    </h3>
                    <div className="tags-container">
                        {d.classificacoesDespesa && d.classificacoesDespesa.length > 0
                            ? d.classificacoesDespesa.map((c, i) => (
                                <span key={i} className="tag">{c}</span>
                            ))
                            : <span>—</span>
                        }
                    </div>
                </div>
            </div>
        </div>
    )
}

// ────────────────────────────────────────────────────────────
// COMPONENTE: HISTÓRICO DE CONTAS A PAGAR
// ────────────────────────────────────────────────────────────
function HistoricoView({ dbStatus }) {
    const [historico, setHistorico] = useState([])
    const [carregando, setCarregando] = useState(false)
    const [erro, setErro] = useState(null)
    const [total, setTotal] = useState(0)
    const [expandido, setExpandido] = useState(null)
    const [deletandoId, setDeletandoId] = useState(null)

    const buscarHistorico = useCallback(async () => {
        if (!dbStatus) return
        setCarregando(true)
        setErro(null)
        try {
            const res = await fetch(`${API_URL}/contas-a-pagar?limite=30&pagina=1`)
            const json = await res.json()
            if (!res.ok) throw new Error(json.detail || "Erro ao buscar histórico")
            setHistorico(json.registros || [])
            setTotal(json.total || 0)
        } catch (e) {
            setErro(e.message)
        } finally {
            setCarregando(false)
        }
    }, [dbStatus])

    const handleExcluirConta = async (contaId) => {
        if (!window.confirm("Deseja realmente inativar este registro do histórico? Ele será ocultado mas não removido permanentemente.")) {
            return
        }

        setDeletandoId(contaId)
        setErro(null)

        try {
            const res = await fetch(`${API_URL}/contas-a-pagar/${contaId}`, {
                method: "DELETE",
            })
            const json = await res.json()
            if (!res.ok || !json.success) {
                throw new Error(json.detail || json.error || "Erro ao inativar o registro.")
            }
            await buscarHistorico()
        } catch (e) {
            setErro(e.message || "Erro ao inativar o registro.")
        } finally {
            setDeletandoId(null)
        }
    }

    const handleLimparHistorico = async () => {
        if (!window.confirm("⚠️ ATENÇÃO: Esta ação irá remover PERMANENTEMENTE todos os registros do histórico (ativos e inativos). Esta operação não pode ser desfeita. Deseja continuar?")) {
            return
        }

        setCarregando(true)
        setErro(null)

        try {
            const res = await fetch(`${API_URL}/contas-a-pagar`, {
                method: "DELETE",
            })
            const json = await res.json()
            if (!res.ok || !json.success) {
                throw new Error(json.detail || json.error || "Erro ao limpar histórico.")
            }
            setHistorico([])
            setTotal(0)
            alert("Histórico limpo com sucesso!")
        } catch (e) {
            setErro(e.message || "Erro ao limpar histórico.")
        } finally {
            setCarregando(false)
        }
    }

    useEffect(() => { buscarHistorico() }, [buscarHistorico])

    if (!dbStatus) {
        return (
            <div className="historico-empty">
                <div className="historico-icon">🗄️</div>
                <p className="historico-msg">Banco de dados offline</p>
                <p className="historico-sub">Inicie o PostgreSQL com <code>docker-compose up -d</code></p>
            </div>
        )
    }

    if (carregando) {
        return (
            <div className="historico-empty">
                <span className="spinner" style={{ width: 24, height: 24 }} />
                <p className="historico-msg">Carregando registros...</p>
            </div>
        )
    }

    if (erro) {
        return (
            <div className="historico-empty">
                <p className="historico-msg" style={{ color: "var(--red)" }}>⚠ {erro}</p>
                <button className="reload-btn" onClick={buscarHistorico}>Tentar novamente</button>
            </div>
        )
    }

    if (historico.length === 0) {
        return (
            <div className="historico-empty">
                <div className="historico-icon">📂</div>
                <p className="historico-msg">Nenhuma conta registrada ainda</p>
                <p className="historico-sub">Extraia e salve uma NF para visualizar aqui</p>
            </div>
        )
    }

    return (
        <div className="historico-wrapper">            <div className="historico-header">
                <h2 className="section-title">
                    <span className="dot dot-blue" /> Histórico de Contas a Pagar
                    <span className="historico-count">({total} registros)</span>
                </h2>
                {historico.length > 0 && (
                    <button
                        className="btn-limpar-historico"
                        onClick={handleLimparHistorico}
                        disabled={carregando}
                    >
                        🗑️ Limpar Histórico
                    </button>
                )}
            </div>
            <div className="historico-header">
                <span className="historico-count">{total} registro{total !== 1 ? "s" : ""} no banco</span>
                <button className="reload-btn" onClick={buscarHistorico} title="Atualizar">↻ Atualizar</button>
            </div>
            <div className="historico-list">
                {historico.map((r) => (
                    <div
                        key={r.id}
                        className={`historico-item ${expandido === r.id ? "expanded" : ""} ${!r.ativo ? "inativo" : ""}`}
                        onClick={() => setExpandido(expandido === r.id ? null : r.id)}
                    >
                        <div className="historico-item-main">
                            <div className="historico-item-left">
                                <span className="hist-nf">NF {r.numero_nota_fiscal}</span>
                                <span className="hist-fornecedor">{r.fornecedor_razao_social}</span>
                            </div>
                            <div className="historico-item-right">
                                <span className="hist-valor">{formatCurrency(r.valor_total)}</span>
                                <span className="hist-data">{formatDate(r.data_emissao)}</span>
                                {!r.ativo && <span className="hist-status-inativo">INATIVO</span>}
                            </div>
                            <div className="historico-item-actions">
                                {r.ativo && (
                                    <button
                                        className="btn-excluir btn-excluir--small"
                                        onClick={(e) => { e.stopPropagation(); handleExcluirConta(r.id) }}
                                        disabled={deletandoId === r.id}
                                    >
                                        {deletandoId === r.id ? "Inativando..." : "Inativar"}
                                    </button>
                                )}
                                <span className="hist-chevron">{expandido === r.id ? "▲" : "▼"}</span>
                            </div>
                        </div>

                        {expandido === r.id && (
                            <div className="historico-detalhe">
                                <div className="hist-det-row"><span>CNPJ Fornecedor</span><strong>{formatCNPJ(r.fornecedor_cnpj)}</strong></div>
                                {r.faturado_nome && <div className="hist-det-row"><span>Faturado</span><strong>{r.faturado_nome}</strong></div>}
                                <div className="hist-det-row"><span>Parcelas</span><strong>{r.qtd_parcelas}</strong></div>
                                <div className="hist-det-row">
                                    <span>Vencimento</span>
                                    <strong>
                                        {r.qtd_parcelas > 1
                                            ? `${formatDate(r.primeiro_vencimento)} → ${formatDate(r.ultimo_vencimento)}`
                                            : formatDate(r.primeiro_vencimento)}
                                    </strong>
                                </div>
                                {r.categorias_despesa && (
                                    <div className="hist-det-row">
                                        <span>Categorias</span>
                                        <div className="tags-container" style={{ justifyContent: "flex-end" }}>
                                            {r.categorias_despesa.split(", ").map((c, i) => (
                                                <span key={i} className="tag">{c}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className="hist-det-row"><span>Registrado em</span><strong>{formatDate(r.criado_em?.split("T")[0])}</strong></div>
                                <div className="hist-det-row hist-det-actions">
                                    {r.ativo && (
                                        <button
                                            className="btn-excluir"
                                            onClick={(e) => { e.stopPropagation(); handleExcluirConta(r.id) }}
                                            disabled={deletandoId === r.id}
                                        >
                                            {deletandoId === r.id ? "Inativando..." : "Inativar"}
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    )
}

// ────────────────────────────────────────────────────────────
// COMPONENTE: ASSISTENTE IA (RAG - Etapa 3)
// ────────────────────────────────────────────────────────────
function AssistenteView({ dbStatus }) {
    const [pergunta, setPergunta] = useState("")
    const [modo, setModo] = useState("auto")
    const [historico, setHistorico] = useState([])
    const [carregando, setCarregando] = useState(false)
    const [erro, setErro] = useState(null)
    const [reindexando, setReindexando] = useState(false)
    const [reindexMsg, setReindexMsg] = useState(null)

    const exemplos = [
        "Qual fornecedor tem o maior valor total em contas a pagar?",
        "Quais parcelas estão vencidas?",
        "Quanto gastei com Manutenção e Operação?",
        "Liste as últimas 5 notas fiscais recebidas",
    ]

    const handlePerguntar = async (e) => {
        e.preventDefault()
        const texto = pergunta.trim()
        if (!texto || carregando) return

        setCarregando(true)
        setErro(null)

        // Adiciona a pergunta do usuário imediatamente
        setHistorico(prev => [...prev, { tipo: "pergunta", texto }])
        setPergunta("")

        try {
            const res = await fetch(`${API_URL}/perguntar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pergunta: texto, modo })
            })
            const json = await res.json()
            if (!res.ok || !json.success) {
                throw new Error(json.detail || json.error || "Erro ao consultar o agente.")
            }
            setHistorico(prev => [...prev, {
                tipo: "resposta",
                texto: json.resposta,
                meta: {
                    estrategia: json.tipo,
                    sql: json.sql_gerada,
                    totalRegistros: json.total_registros,
                    documentos: json.documentos_recuperados,
                    aviso: json.aviso,
                }
            }])
        } catch (e) {
            const msg = e.message || "Erro ao consultar o agente."
            setErro(msg)
            setHistorico(prev => [...prev, { tipo: "erro", texto: msg }])
        } finally {
            setCarregando(false)
        }
    }

    const handleReindexar = async () => {
        setReindexando(true)
        setReindexMsg(null)
        try {
            const res = await fetch(`${API_URL}/perguntar/reindexar`, { method: "POST" })
            const json = await res.json()
            if (!res.ok || !json.success) {
                throw new Error(json.detail || json.error || "Erro ao reindexar.")
            }
            setReindexMsg(`✓ ${json.total_documentos} registros indexados`)
        } catch (e) {
            setReindexMsg(`⚠ ${e.message}`)
        } finally {
            setReindexando(false)
            setTimeout(() => setReindexMsg(null), 5000)
        }
    }

    if (!dbStatus) {
        return (
            <div className="historico-empty">
                <div className="historico-icon">🤖</div>
                <p className="historico-msg">Banco de dados offline</p>
                <p className="historico-sub">Inicie o PostgreSQL com <code>docker-compose up -d</code></p>
            </div>
        )
    }

    return (
        <div className="assistente-wrapper">
            <div className="assistente-toolbar">
                <div className="assistente-modos">
                    <button
                        className={`modo-btn ${modo === "auto" ? "active" : ""}`}
                        onClick={() => setModo("auto")}
                        title="Tenta SQL e cai para busca semântica se necessário"
                    >
                        Híbrido
                    </button>
                    <button
                        className={`modo-btn ${modo === "sql" ? "active" : ""}`}
                        onClick={() => setModo("sql")}
                        title="RAG Simples: gera SQL e consulta o banco diretamente"
                    >
                        RAG SQL
                    </button>
                    <button
                        className={`modo-btn ${modo === "embeddings" ? "active" : ""}`}
                        onClick={() => setModo("embeddings")}
                        title="RAG Embeddings: busca semântica no histórico financeiro"
                    >
                        RAG Embeddings
                    </button>
                </div>
                <button
                    className={`btn-reindexar ${reindexando ? "loading" : ""}`}
                    onClick={handleReindexar}
                    disabled={reindexando}
                    title="Reconstrói o índice de embeddings a partir do banco atual"
                >
                    {reindexando ? <span className="spinner" /> : "↻"} Reindexar
                </button>
            </div>

            {reindexMsg && <div className="reindex-msg">{reindexMsg}</div>}

            <div className="assistente-chat">
                {historico.length === 0 && (
                    <div className="assistente-empty">
                        <div className="historico-icon">💬</div>
                        <p className="historico-msg">Faça uma pergunta sobre suas finanças</p>
                        <div className="exemplos-grid">
                            {exemplos.map((ex, i) => (
                                <button
                                    key={i}
                                    className="exemplo-chip"
                                    onClick={() => setPergunta(ex)}
                                >
                                    {ex}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {historico.map((item, i) => (
                    <div key={i} className={`chat-bubble chat-${item.tipo}`}>
                        {item.tipo === "pergunta" && <span className="chat-icon">🧑</span>}
                        {item.tipo === "resposta" && <span className="chat-icon">🤖</span>}
                        {item.tipo === "erro" && <span className="chat-icon">⚠</span>}
                        <div className="chat-content">
                            <p>{item.texto}</p>
                            {item.meta && (
                                <div className="chat-meta">
                                    <span className="meta-badge">
                                        {item.meta.estrategia === "rag_simples" ? "RAG SQL" : "RAG Embeddings"}
                                    </span>
                                    {item.meta.totalRegistros != null && (
                                        <span className="meta-badge">{item.meta.totalRegistros} registro(s)</span>
                                    )}
                                    {item.meta.sql && (
                                        <details className="meta-details">
                                            <summary>Ver SQL gerada</summary>
                                            <pre className="meta-sql">{item.meta.sql}</pre>
                                        </details>
                                    )}
                                    {item.meta.documentos && item.meta.documentos.length > 0 && (
                                        <details className="meta-details">
                                            <summary>Ver {item.meta.documentos.length} documento(s) recuperado(s)</summary>
                                            <ul className="meta-docs">
                                                {item.meta.documentos.map((d, j) => (
                                                    <li key={j}>
                                                        <strong>{d.origem} #{d.id}</strong> (score {d.score}): {d.texto}
                                                    </li>
                                                ))}
                                            </ul>
                                        </details>
                                    )}
                                    {item.meta.aviso && <p className="meta-aviso">{item.meta.aviso}</p>}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {carregando && (
                    <div className="chat-bubble chat-resposta">
                        <span className="chat-icon">🤖</span>
                        <div className="chat-content">
                            <span className="spinner" /> Pensando...
                        </div>
                    </div>
                )}
            </div>

            <form className="assistente-form" onSubmit={handlePerguntar}>
                <input
                    type="text"
                    className="assistente-input"
                    placeholder="Ex: Quais contas estão vencidas este mês?"
                    value={pergunta}
                    onChange={(e) => setPergunta(e.target.value)}
                    disabled={carregando}
                />
                <button type="submit" className="assistente-send" disabled={carregando || !pergunta.trim()}>
                    {carregando ? <span className="spinner" /> : "Enviar"}
                </button>
            </form>
        </div>
    )
}

// ────────────────────────────────────────────────────────────
// COMPONENTE PRINCIPAL
// ────────────────────────────────────────────────────────────
export default function App() {
    const [file, setFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const [tab, setTab] = useState("formatted")
    const [mainTab, setMainTab] = useState("extrator")
    const [dragOver, setDragOver] = useState(false)
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState(null) // null | "ok" | "error"
    const [saveMsg, setSaveMsg] = useState("")
    const [dbStatus, setDbStatus] = useState(null)
    const inputRef = useRef()

    // Checar status do banco ao carregar
    useEffect(() => {
        fetch(`${API_URL}/db-status`)
            .then(r => r.json())
            .then(j => setDbStatus(j.banco_disponivel))
            .catch(() => setDbStatus(false))
    }, [])

    const handleFile = (f) => {
        if (f && f.type === "application/pdf") {
            setFile(f)
            setError(null)
            setResult(null)
            setSaveStatus(null)
        } else {
            setError("Apenas arquivos PDF são aceitos.")
        }
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setDragOver(false)
        handleFile(e.dataTransfer.files[0])
    }

    const handleExtract = async () => {
        if (!file) return
        setLoading(true)
        setError(null)
        setResult(null)
        setSaveStatus(null)

        const formData = new FormData()
        formData.append("file", file)

        try {
            const res = await fetch(`${API_URL}/extrair`, { method: "POST", body: formData })
            const contentType = res.headers.get("content-type")
            if (!contentType?.includes("application/json")) {
                const text = await res.text()
                throw new Error(`Erro do servidor (${res.status}): ${text || res.statusText}`)
            }
            const json = await res.json()
            if (!res.ok) throw new Error(json.detail || json.error || "Erro ao processar arquivo")
            if (!json.data) throw new Error("Resposta inválida: dados não encontrados")
            setResult(json.data)
            setTab("formatted")
        } catch (err) {
            setError(err.message || "Erro desconhecido ao processar arquivo")
        } finally {
            setLoading(false)
        }
    }

    const handleSalvar = async () => {
        if (!result) return
        setSaving(true)
        setSaveStatus(null)
        setSaveMsg("")
        try {
            const res = await fetch(`${API_URL}/salvar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(result)
            })
            const json = await res.json()
            if (!res.ok) throw new Error(json.detail || "Erro ao salvar")
            const r = json.resultado
            setSaveStatus("ok")
            setSaveMsg(`Salvo! Conta #${r.contas_a_pagar_id} · ${r.parcelas_salvas} parcela(s)`)
        } catch (e) {
            setSaveStatus("error")
            setSaveMsg(e.message)
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="app">
            <div className="bg-grid" />

            <div className="container">
                {/* Header */}
                <header className="app-header">
                    <div className="header-badge">
                        IA · Groq/Llama
                        <span className={`db-dot ${dbStatus === true ? "db-on" : dbStatus === false ? "db-off" : "db-unk"}`} title={dbStatus === true ? "Banco online" : "Banco offline"} />
                    </div>
                    <h1 className="app-title">Extração de Dados de Nota Fiscal</h1>
                    <p className="app-subtitle">
                        Carregue um PDF de nota fiscal e extraia os dados automaticamente usando IA
                    </p>
                </header>

                {/* Main Tabs */}
                <div className="main-tabs">
                    <button
                        id="tab-extrator"
                        className={`main-tab-btn ${mainTab === "extrator" ? "active" : ""}`}
                        onClick={() => setMainTab("extrator")}
                    >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        Extrator de NF
                    </button>
                    <button
                        id="tab-historico"
                        className={`main-tab-btn ${mainTab === "historico" ? "active" : ""}`}
                        onClick={() => setMainTab("historico")}
                    >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                            <polyline points="9 22 9 12 15 12 15 22" />
                        </svg>
                        Histórico
                        {!dbStatus && <span className="tab-badge-off">offline</span>}
                    </button>
                    <button
                        id="tab-assistente"
                        className={`main-tab-btn ${mainTab === "assistente" ? "active" : ""}`}
                        onClick={() => setMainTab("assistente")}
                    >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="11" width="18" height="10" rx="2" />
                            <circle cx="12" cy="5" r="2" />
                            <path d="M12 7v4" />
                            <line x1="8" y1="16" x2="8" y2="16" />
                            <line x1="16" y1="16" x2="16" y2="16" />
                        </svg>
                        Assistente IA
                        {!dbStatus && <span className="tab-badge-off">offline</span>}
                    </button>
                </div>

                {/* ── EXTRATOR ── */}
                {mainTab === "extrator" && (
                    <>
                        {/* Upload Card */}
                        <div className="card upload-card">
                            <div className="card-label">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                    <polyline points="17 8 12 3 7 8" />
                                    <line x1="12" y1="3" x2="12" y2="15" />
                                </svg>
                                Upload do PDF
                            </div>

                            <p className="upload-label-text">Selecione o arquivo PDF da nota fiscal</p>

                            <div
                                className={`drop-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleDrop}
                                onClick={() => inputRef.current.click()}
                            >
                                <input
                                    ref={inputRef}
                                    type="file"
                                    accept=".pdf"
                                    style={{ display: "none" }}
                                    onChange={(e) => handleFile(e.target.files[0])}
                                />
                                {file ? (
                                    <div className="file-info">
                                        <span className="file-icon">📄</span>
                                        <div>
                                            <div className="file-name">{file.name}</div>
                                            <div className="file-size">{(file.size / 1024).toFixed(1)} KB</div>
                                        </div>
                                        <button className="remove-btn" onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); setSaveStatus(null) }}>✕</button>
                                    </div>
                                ) : (
                                    <div className="drop-placeholder">
                                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                            <polyline points="14 2 14 8 20 8" />
                                        </svg>
                                        <p>Arraste o PDF aqui ou <span>clique para selecionar</span></p>
                                    </div>
                                )}
                            </div>

                            {error && (
                                <div className="error-box">
                                    <span>⚠</span> {error}
                                </div>
                            )}

                            <button
                                id="btn-extrair"
                                className={`extract-btn ${loading ? "loading" : ""}`}
                                onClick={handleExtract}
                                disabled={!file || loading}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner" />
                                        Extraindo dados...
                                    </>
                                ) : (
                                    <>
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <circle cx="11" cy="11" r="8" />
                                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                                        </svg>
                                        Extrair Dados
                                    </>
                                )}
                            </button>
                        </div>

                        {/* Results */}
                        {result && (
                            <div className="card results-card">
                                <div className="results-header">
                                    <span className="results-label">Dados Extraídos</span>
                                    <span className="success-badge">✓ Extração concluída</span>
                                </div>

                                <div className="tabs">
                                    <button className={`tab-btn ${tab === "formatted" ? "active" : ""}`} onClick={() => setTab("formatted")}>
                                        Visualização Formatada
                                    </button>
                                    <button className={`tab-btn ${tab === "json" ? "active" : ""}`} onClick={() => setTab("json")}>
                                        JSON
                                    </button>
                                </div>

                                <div className="tab-content">
                                    {tab === "formatted" ? <FormattedViewer data={result} /> : <JsonViewer data={result} />}
                                </div>

                                {/* Save Section */}
                                <div className="save-section">
                                    {saveStatus === "ok" && (
                                        <div className="save-ok">
                                            <span>✓</span> {saveMsg}
                                        </div>
                                    )}
                                    {saveStatus === "error" && (
                                        <div className="save-err">
                                            <span>⚠</span> {saveMsg}
                                        </div>
                                    )}
                                    {saveStatus !== "ok" && (
                                        <button
                                            id="btn-salvar"
                                            className={`save-btn ${saving ? "loading" : ""} ${!dbStatus ? "db-offline" : ""}`}
                                            onClick={handleSalvar}
                                            disabled={saving || saveStatus === "ok"}
                                            title={!dbStatus ? "Banco offline — inicie com docker-compose up -d" : "Salvar no PostgreSQL"}
                                        >
                                            {saving ? (
                                                <><span className="spinner" style={{ borderTopColor: "#fff" }} />Salvando...</>
                                            ) : (
                                                <>
                                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                                                        <polyline points="17 21 17 13 7 13 7 21" />
                                                        <polyline points="7 3 7 8 15 8" />
                                                    </svg>
                                                    {dbStatus ? "Salvar no Banco" : "Banco Offline"}
                                                </>
                                            )}
                                        </button>
                                    )}
                                </div>

                                <p className="results-footer">
                                    Este JSON contém todos os dados extraídos da nota fiscal e pode ser usado para integração com outros sistemas.
                                </p>
                            </div>
                        )}
                    </>
                )}

                {/* ── HISTÓRICO ── */}
                {mainTab === "historico" && (
                    <div className="card">
                        <div className="card-label">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                            </svg>
                            Contas a Pagar — Histórico
                        </div>
                        <HistoricoView dbStatus={dbStatus} />
                    </div>
                )}

                {/* ── ASSISTENTE IA (RAG) ── */}
                {mainTab === "assistente" && (
                    <div className="card">
                        <div className="card-label">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="3" y="11" width="18" height="10" rx="2" />
                                <circle cx="12" cy="5" r="2" />
                                <path d="M12 7v4" />
                            </svg>
                            Assistente Financeiro Inteligente
                        </div>
                        <p className="upload-label-text">
                            Pergunte algo sobre suas contas, fornecedores, clientes ou despesas em linguagem natural.
                        </p>
                        <AssistenteView dbStatus={dbStatus} />
                    </div>
                )}
            </div>
        </div>
    )
}
