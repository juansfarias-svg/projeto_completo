-- ============================================================
-- PROJETO ADMINISTRATIVO-FINANCEIRO
-- Banco de Dados PostgreSQL
-- UniRV - Universidade de Rio Verde
-- ============================================================

-- ============================================================
-- TABELA: FORNECEDOR
-- Regra: Não pode ser excluído, apenas INATIVADO/REATIVADO
-- ============================================================
CREATE TABLE IF NOT EXISTS fornecedor (
    id              SERIAL PRIMARY KEY,
    razao_social    VARCHAR(255)    NOT NULL,
    fantasia        VARCHAR(255),
    cnpj            VARCHAR(18)     NOT NULL UNIQUE,  -- Formato: XX.XXX.XXX/XXXX-XX
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  fornecedor              IS 'Cadastro de fornecedores. Registros nunca são excluídos, apenas inativados.';
COMMENT ON COLUMN fornecedor.cnpj         IS 'CNPJ no formato XX.XXX.XXX/XXXX-XX';
COMMENT ON COLUMN fornecedor.ativo        IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: CLIENTE
-- Regra: Não pode ser excluído, apenas INATIVADO/REATIVADO
-- ============================================================
CREATE TABLE IF NOT EXISTS cliente (
    id              SERIAL PRIMARY KEY,
    razao_social    VARCHAR(255)    NOT NULL,
    fantasia        VARCHAR(255),
    cnpj            VARCHAR(18)     UNIQUE,           -- Pessoa Jurídica
    cpf             VARCHAR(14)     UNIQUE,           -- Pessoa Física (formato: XXX.XXX.XXX-XX)
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP       NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_cliente_documento CHECK (cnpj IS NOT NULL OR cpf IS NOT NULL)
);

COMMENT ON TABLE  cliente                 IS 'Cadastro de clientes. Registros nunca são excluídos, apenas inativados.';
COMMENT ON COLUMN cliente.ativo           IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: FATURADO
-- Pessoa física responsável pela nota fiscal
-- Regra: Não pode ser excluído, apenas INATIVADO/REATIVADO
-- ============================================================
CREATE TABLE IF NOT EXISTS faturado (
    id              SERIAL PRIMARY KEY,
    nome_completo   VARCHAR(255)    NOT NULL,
    cpf             VARCHAR(14)     UNIQUE,           -- Opcional (NF nem sempre tem CPF legível)
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  faturado                IS 'Pessoa física faturada na nota fiscal. Registros nunca são excluídos, apenas inativados.';
COMMENT ON COLUMN faturado.cpf            IS 'CPF no formato XXX.XXX.XXX-XX. Pode ser NULL se não constar na NF.';
COMMENT ON COLUMN faturado.ativo          IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: TIPO_RECEITA
-- Regra: Não pode ser excluído, apenas INATIVADO/REATIVADO
-- ============================================================
CREATE TABLE IF NOT EXISTS tipo_receita (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(150)    NOT NULL UNIQUE,
    descricao       TEXT,
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  tipo_receita            IS 'Classificações de receita. Registros nunca são excluídos, apenas inativados.';
COMMENT ON COLUMN tipo_receita.ativo      IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: TIPO_DESPESA
-- Principais categorias conforme especificação do projeto
-- Regra: Não pode ser excluído, apenas INATIVADO/REATIVADO
-- ============================================================
CREATE TABLE IF NOT EXISTS tipo_despesa (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(150)    NOT NULL UNIQUE,
    descricao       TEXT,
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  tipo_despesa            IS 'Categorias de despesa interpretadas pela IA. Registros nunca são excluídos, apenas inativados.';
COMMENT ON COLUMN tipo_despesa.ativo      IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- Seed: Categorias de despesa conforme especificação
INSERT INTO tipo_despesa (nome, descricao) VALUES
    ('INSUMOS AGRÍCOLAS',           'Sementes, Fertilizantes, Defensivos Agrícolas, Corretivos'),
    ('MANUTENÇÃO E OPERAÇÃO',       'Combustíveis, Lubrificantes, Peças, Manutenção de Máquinas, Pneus, Filtros, Ferramentas'),
    ('RECURSOS HUMANOS',            'Mão de Obra Temporária, Salários e Encargos'),
    ('SERVIÇOS OPERACIONAIS',       'Frete, Colheita Terceirizada, Secagem, Armazenagem, Pulverização'),
    ('INFRAESTRUTURA E UTILIDADES', 'Energia Elétrica, Arrendamento de Terras, Construções, Materiais de Construção'),
    ('ADMINISTRATIVAS',             'Honorários Contábeis, Advocatícios, Agronômicos, Despesas Bancárias e Financeiras'),
    ('SEGUROS E PROTEÇÃO',          'Seguro Agrícola, Seguro de Ativos (Máquinas/Veículos), Seguro Prestamista'),
    ('IMPOSTOS E TAXAS',            'ITR, IPTU, IPVA, INCRA-CCIR'),
    ('INVESTIMENTOS',               'Aquisição de Máquinas, Implementos, Veículos, Imóveis, Infraestrutura Rural')
ON CONFLICT (nome) DO NOTHING;

-- ============================================================
-- TABELA: CONTAS_A_PAGAR
-- Registro principal de uma conta a pagar (nota fiscal)
-- ============================================================
CREATE TABLE IF NOT EXISTS contas_a_pagar (
    id                  SERIAL PRIMARY KEY,
    fornecedor_id       INT             NOT NULL REFERENCES fornecedor(id),
    faturado_id         INT             REFERENCES faturado(id),       -- NULL = NF sem pessoa física identificada
    numero_nota_fiscal  VARCHAR(50)     NOT NULL,
    serie_nota_fiscal   VARCHAR(10),                                   -- NULL = não informado pela NF
    data_emissao        DATE            NOT NULL,
    descricao_produtos  TEXT,           -- Descrição livre dos produtos da NF extraída pela IA
    valor_total         NUMERIC(15, 2)  NOT NULL,
    observacoes         TEXT,
    ativo               BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  contas_a_pagar                    IS 'Cabeçalho do registro de contas a pagar, vinculado a uma nota fiscal.';
COMMENT ON COLUMN contas_a_pagar.faturado_id        IS 'NULL quando a NF não identifica pessoa física faturada.';
COMMENT ON COLUMN contas_a_pagar.descricao_produtos IS 'Descrição dos itens da NF extraída pela IA. Sem entidade Produto separada.';
COMMENT ON COLUMN contas_a_pagar.ativo              IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: CONTAS_A_PAGAR_TIPO_DESPESA  (N:N)
-- Um registro de contas a pagar pode ter UMA OU MAIS despesas
-- ============================================================
CREATE TABLE IF NOT EXISTS contas_a_pagar_tipo_despesa (
    id                  SERIAL PRIMARY KEY,
    contas_a_pagar_id   INT     NOT NULL REFERENCES contas_a_pagar(id) ON DELETE CASCADE,
    tipo_despesa_id     INT     NOT NULL REFERENCES tipo_despesa(id),
    CONSTRAINT uq_cap_td UNIQUE (contas_a_pagar_id, tipo_despesa_id)
);

COMMENT ON TABLE contas_a_pagar_tipo_despesa IS 'Associação N:N entre contas a pagar e tipos de despesa (classificação da IA).';

-- ============================================================
-- TABELA: PARCELAS_PAGAR
-- Uma conta a pagar pode ter UMA OU MAIS parcelas
-- ============================================================
CREATE TABLE IF NOT EXISTS parcelas_pagar (
    id                  SERIAL PRIMARY KEY,
    contas_a_pagar_id   INT             NOT NULL REFERENCES contas_a_pagar(id) ON DELETE CASCADE,
    numero_parcela      SMALLINT        NOT NULL DEFAULT 1,
    data_vencimento     DATE            NOT NULL,
    valor_parcela       NUMERIC(15, 2)  NOT NULL,
    data_pagamento      DATE,                          -- NULL = ainda não pago
    valor_pago          NUMERIC(15, 2),
    observacoes         TEXT,
    criado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP       NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_parcela_pagar UNIQUE (contas_a_pagar_id, numero_parcela)
);

COMMENT ON TABLE  parcelas_pagar                    IS 'Parcelas de uma conta a pagar. Datas de vencimento distintas por parcela.';
COMMENT ON COLUMN parcelas_pagar.data_pagamento     IS 'Preenchido quando a parcela é quitada. NULL = em aberto.';
COMMENT ON COLUMN parcelas_pagar.numero_parcela     IS 'Número sequencial da parcela dentro da conta (1, 2, 3...).';

-- ============================================================
-- TABELA: CONTAS_A_RECEBER
-- ============================================================
CREATE TABLE IF NOT EXISTS contas_a_receber (
    id                  SERIAL PRIMARY KEY,
    cliente_id          INT             NOT NULL REFERENCES cliente(id),
    faturado_id         INT             REFERENCES faturado(id),
    numero_documento    VARCHAR(50),
    data_emissao        DATE            NOT NULL,
    descricao           TEXT,
    valor_total         NUMERIC(15, 2)  NOT NULL,
    observacoes         TEXT,
    ativo               BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  contas_a_receber       IS 'Cabeçalho do registro de contas a receber.';
COMMENT ON COLUMN contas_a_receber.ativo IS 'TRUE = ativo, FALSE = inativo. Nunca deletar o registro.';

-- ============================================================
-- TABELA: CONTAS_A_RECEBER_TIPO_RECEITA  (N:N)
-- ============================================================
CREATE TABLE IF NOT EXISTS contas_a_receber_tipo_receita (
    id                      SERIAL PRIMARY KEY,
    contas_a_receber_id     INT     NOT NULL REFERENCES contas_a_receber(id) ON DELETE CASCADE,
    tipo_receita_id         INT     NOT NULL REFERENCES tipo_receita(id),
    CONSTRAINT uq_car_tr UNIQUE (contas_a_receber_id, tipo_receita_id)
);

COMMENT ON TABLE contas_a_receber_tipo_receita IS 'Associação N:N entre contas a receber e tipos de receita.';

-- ============================================================
-- TABELA: PARCELAS_RECEBER
-- ============================================================
CREATE TABLE IF NOT EXISTS parcelas_receber (
    id                      SERIAL PRIMARY KEY,
    contas_a_receber_id     INT             NOT NULL REFERENCES contas_a_receber(id) ON DELETE CASCADE,
    numero_parcela          SMALLINT        NOT NULL DEFAULT 1,
    data_vencimento         DATE            NOT NULL,
    valor_parcela           NUMERIC(15, 2)  NOT NULL,
    data_recebimento        DATE,                      -- NULL = ainda não recebido
    valor_recebido          NUMERIC(15, 2),
    observacoes             TEXT,
    criado_em               TIMESTAMP       NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMP       NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_parcela_receber UNIQUE (contas_a_receber_id, numero_parcela)
);

COMMENT ON TABLE  parcelas_receber                      IS 'Parcelas de uma conta a receber.';
COMMENT ON COLUMN parcelas_receber.data_recebimento     IS 'Preenchido quando a parcela é recebida. NULL = em aberto.';

-- ============================================================
-- ÍNDICES para performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_fornecedor_cnpj        ON fornecedor           (cnpj);
CREATE INDEX IF NOT EXISTS idx_fornecedor_ativo        ON fornecedor           (ativo);
CREATE INDEX IF NOT EXISTS idx_cliente_cnpj            ON cliente              (cnpj);
CREATE INDEX IF NOT EXISTS idx_cliente_cpf             ON cliente              (cpf);
CREATE INDEX IF NOT EXISTS idx_cliente_ativo           ON cliente              (ativo);
CREATE INDEX IF NOT EXISTS idx_faturado_cpf            ON faturado             (cpf);
CREATE INDEX IF NOT EXISTS idx_faturado_ativo          ON faturado             (ativo);
CREATE INDEX IF NOT EXISTS idx_tipo_despesa_ativo      ON tipo_despesa         (ativo);
CREATE INDEX IF NOT EXISTS idx_tipo_receita_ativo      ON tipo_receita         (ativo);

CREATE INDEX IF NOT EXISTS idx_cap_fornecedor          ON contas_a_pagar       (fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_cap_faturado            ON contas_a_pagar       (faturado_id);
CREATE INDEX IF NOT EXISTS idx_cap_data_emissao        ON contas_a_pagar       (data_emissao);
CREATE INDEX IF NOT EXISTS idx_cap_ativo               ON contas_a_pagar       (ativo);
CREATE INDEX IF NOT EXISTS idx_cap_td_conta            ON contas_a_pagar_tipo_despesa (contas_a_pagar_id);

CREATE INDEX IF NOT EXISTS idx_pp_conta                ON parcelas_pagar       (contas_a_pagar_id);
CREATE INDEX IF NOT EXISTS idx_pp_vencimento           ON parcelas_pagar       (data_vencimento);
CREATE INDEX IF NOT EXISTS idx_pp_pagamento            ON parcelas_pagar       (data_pagamento);

CREATE INDEX IF NOT EXISTS idx_car_cliente             ON contas_a_receber     (cliente_id);
CREATE INDEX IF NOT EXISTS idx_car_faturado            ON contas_a_receber     (faturado_id);
CREATE INDEX IF NOT EXISTS idx_car_data_emissao        ON contas_a_receber     (data_emissao);
CREATE INDEX IF NOT EXISTS idx_car_ativo               ON contas_a_receber     (ativo);
CREATE INDEX IF NOT EXISTS idx_car_tr_conta            ON contas_a_receber_tipo_receita (contas_a_receber_id);

CREATE INDEX IF NOT EXISTS idx_pr_conta                ON parcelas_receber     (contas_a_receber_id);
CREATE INDEX IF NOT EXISTS idx_pr_vencimento           ON parcelas_receber     (data_vencimento);
CREATE INDEX IF NOT EXISTS idx_pr_recebimento          ON parcelas_receber     (data_recebimento);

-- ============================================================
-- TRIGGERS: atualizar campo atualizado_em automaticamente
-- ============================================================
CREATE OR REPLACE FUNCTION fn_atualiza_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_fornecedor_updated
    BEFORE UPDATE ON fornecedor
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_cliente_updated
    BEFORE UPDATE ON cliente
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_faturado_updated
    BEFORE UPDATE ON faturado
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_tipo_receita_updated
    BEFORE UPDATE ON tipo_receita
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_tipo_despesa_updated
    BEFORE UPDATE ON tipo_despesa
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_contas_a_pagar_updated
    BEFORE UPDATE ON contas_a_pagar
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_parcelas_pagar_updated
    BEFORE UPDATE ON parcelas_pagar
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_contas_a_receber_updated
    BEFORE UPDATE ON contas_a_receber
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

CREATE OR REPLACE TRIGGER trg_parcelas_receber_updated
    BEFORE UPDATE ON parcelas_receber
    FOR EACH ROW EXECUTE FUNCTION fn_atualiza_timestamp();

-- ============================================================
-- VIEWS ÚTEIS
-- ============================================================

CREATE OR REPLACE VIEW vw_contas_a_pagar_completo AS
SELECT
    cap.id,
    cap.numero_nota_fiscal,
    cap.serie_nota_fiscal,
    cap.data_emissao,
    cap.descricao_produtos,
    cap.valor_total,
    cap.ativo,
    cap.criado_em,
    f.razao_social              AS fornecedor_razao_social,
    f.fantasia                  AS fornecedor_fantasia,
    f.cnpj                      AS fornecedor_cnpj,
    fat.nome_completo           AS faturado_nome,
    fat.cpf                     AS faturado_cpf,
    COUNT(DISTINCT pp.id)       AS qtd_parcelas,
    MIN(pp.data_vencimento)     AS primeiro_vencimento,
    MAX(pp.data_vencimento)     AS ultimo_vencimento,
    SUM(pp.valor_parcela)       AS total_parcelas,
    STRING_AGG(DISTINCT td.nome, ', ' ORDER BY td.nome) AS categorias_despesa
FROM contas_a_pagar cap
JOIN fornecedor f            ON f.id   = cap.fornecedor_id
LEFT JOIN faturado fat       ON fat.id = cap.faturado_id
LEFT JOIN parcelas_pagar pp  ON pp.contas_a_pagar_id = cap.id
LEFT JOIN contas_a_pagar_tipo_despesa captd ON captd.contas_a_pagar_id = cap.id
LEFT JOIN tipo_despesa td    ON td.id  = captd.tipo_despesa_id
GROUP BY cap.id, f.id, fat.id;

CREATE OR REPLACE VIEW vw_parcelas_pagar_em_aberto AS
SELECT
    pp.id,
    pp.numero_parcela,
    pp.data_vencimento,
    pp.valor_parcela,
    CASE WHEN pp.data_vencimento < CURRENT_DATE THEN TRUE ELSE FALSE END AS vencida,
    cap.numero_nota_fiscal,
    f.razao_social AS fornecedor
FROM parcelas_pagar pp
JOIN contas_a_pagar cap ON cap.id = pp.contas_a_pagar_id
JOIN fornecedor f        ON f.id  = cap.fornecedor_id
WHERE pp.data_pagamento IS NULL
  AND cap.ativo = TRUE
ORDER BY pp.data_vencimento;

CREATE OR REPLACE VIEW vw_contas_a_receber_completo AS
SELECT
    car.id,
    car.numero_documento,
    car.data_emissao,
    car.descricao,
    car.valor_total,
    car.ativo,
    car.criado_em,
    c.razao_social              AS cliente_razao_social,
    c.fantasia                  AS cliente_fantasia,
    c.cnpj                      AS cliente_cnpj,
    c.cpf                       AS cliente_cpf,
    fat.nome_completo           AS faturado_nome,
    fat.cpf                     AS faturado_cpf,
    COUNT(DISTINCT pr.id)       AS qtd_parcelas,
    MIN(pr.data_vencimento)     AS primeiro_vencimento,
    MAX(pr.data_vencimento)     AS ultimo_vencimento,
    SUM(pr.valor_parcela)       AS total_parcelas,
    STRING_AGG(DISTINCT tr.nome, ', ' ORDER BY tr.nome) AS categorias_receita
FROM contas_a_receber car
JOIN cliente c               ON c.id   = car.cliente_id
LEFT JOIN faturado fat       ON fat.id = car.faturado_id
LEFT JOIN parcelas_receber pr ON pr.contas_a_receber_id = car.id
LEFT JOIN contas_a_receber_tipo_receita cartr ON cartr.contas_a_receber_id = car.id
LEFT JOIN tipo_receita tr    ON tr.id  = cartr.tipo_receita_id
GROUP BY car.id, c.id, fat.id;

CREATE OR REPLACE VIEW vw_parcelas_receber_em_aberto AS
SELECT
    pr.id,
    pr.numero_parcela,
    pr.data_vencimento,
    pr.valor_parcela,
    CASE WHEN pr.data_vencimento < CURRENT_DATE THEN TRUE ELSE FALSE END AS vencida,
    car.numero_documento,
    c.razao_social AS cliente
FROM parcelas_receber pr
JOIN contas_a_receber car ON car.id = pr.contas_a_receber_id
JOIN cliente c             ON c.id  = car.cliente_id
WHERE pr.data_recebimento IS NULL
  AND car.ativo = TRUE
ORDER BY pr.data_vencimento;

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
