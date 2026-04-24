#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ SETUP BANCO DE DADOS - Projeto Contas Orçamento
Cria o banco 'ContasOrcamento' com todas as tabelas e relacionamentos
"""

import psycopg
from psycopg import sql
from psycopg.errors import DuplicateDatabase
import sys

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DB_USER = "postgres"
DB_PASSWORD = "200466"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_BASE = "postgres"  # Banco para criar novos bancos
DB_TARGET = "ContasOrcamento"  # Banco do projeto

CONN_BASE = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_BASE}"
CONN_TARGET = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_TARGET}"

# =============================================================================
# SQL DAS TABELAS
# =============================================================================

SQL_TABELAS = """
-- ============================================================
-- MÓDULO: ORÇAMENTO (Novo)
-- ============================================================

-- Tabela: categorias
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'Despesa' CHECK (tipo IN ('Receita', 'Despesa')),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: movimentacoes
CREATE TABLE IF NOT EXISTS movimentacoes (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    valor NUMERIC(12, 2) NOT NULL,
    data DATE NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('Receita', 'Despesa')),
    pago BOOLEAN DEFAULT TRUE,
    observacao TEXT,
    parcelas INTEGER DEFAULT 1,
    parcela_atual INTEGER DEFAULT 1,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- MÓDULO: CONTAS A PAGAR (Legado - Compatível com SQLite)
-- ============================================================

-- Tabela: pagamentos
CREATE TABLE IF NOT EXISTS pagamentos (
    cod SERIAL PRIMARY KEY,
    mes_ano VARCHAR(10) NOT NULL,
    conta VARCHAR(100) NOT NULL,
    instituicao VARCHAR(50),
    fonte_paga VARCHAR(50),
    data_venc VARCHAR(20),        -- Formato: DD/MM/AAAA (compatível com legado)
    data_pago VARCHAR(20),        -- Formato: DD/MM/AAAA
    valor_pagar NUMERIC(10, 2),
    valor_pago NUMERIC(10, 2),
    parcela VARCHAR(20),
    observacao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: documentos_pagamento
CREATE TABLE IF NOT EXISTS documentos_pagamento (
    id SERIAL PRIMARY KEY,
    pagamento_id INTEGER NOT NULL REFERENCES pagamentos(cod) ON DELETE CASCADE,
    nome_arquivo VARCHAR(255),
    tipo_mime VARCHAR(100) DEFAULT 'application/pdf',
    conteudo BYTEA,               -- Armazena o PDF em binário
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================

-- Índices módulo Orçamento
CREATE INDEX IF NOT EXISTS idx_movimentacoes_data ON movimentacoes(data);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_tipo ON movimentacoes(tipo);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_categoria ON movimentacoes(categoria_id);
CREATE INDEX IF NOT EXISTS idx_categorias_tipo ON categorias(tipo) WHERE ativo = TRUE;

-- Índices módulo Contas a Pagar
CREATE INDEX IF NOT EXISTS idx_pagamentos_mes_ano ON pagamentos(mes_ano);
CREATE INDEX IF NOT EXISTS idx_pagamentos_data_venc ON pagamentos(data_venc);
CREATE INDEX IF NOT EXISTS idx_pagamentos_valor_pago ON pagamentos(valor_pago) WHERE valor_pago IS NULL OR valor_pago = 0;
CREATE INDEX IF NOT EXISTS idx_documentos_pagamento_id ON documentos_pagamento(pagamento_id);

-- ============================================================
-- VIEW: Resumo Financeiro Mensal (Opcional)
-- ============================================================

CREATE OR REPLACE VIEW vw_resumo_mensal AS
SELECT 
    EXTRACT(YEAR FROM m.data) as ano,
    EXTRACT(MONTH FROM m.data) as mes,
    m.tipo,
    c.nome as categoria,
    SUM(m.valor) as total,
    COUNT(*) as quantidade
FROM movimentacoes m
JOIN categorias c ON m.categoria_id = c.id
WHERE c.ativo = TRUE
GROUP BY EXTRACT(YEAR FROM m.data), EXTRACT(MONTH FROM m.data), m.tipo, c.nome;
"""

SQL_CATEGORIAS_PADRAO = """
-- Inserir categorias padrão se a tabela estiver vazia
INSERT INTO categorias (nome, tipo) 
SELECT * FROM (VALUES
    -- Receitas
    ('Salário', 'Receita'),
    ('Investimentos', 'Receita'),
    ('Rendimentos', 'Receita'),
    ('Prêmios', 'Receita'),
    ('Reembolsos', 'Receita'),
    ('Outros Recebimentos', 'Receita'),
    -- Despesas
    ('Alimentação', 'Despesa'),
    ('Transporte', 'Despesa'),
    ('Combustível', 'Despesa'),
    ('Moradia', 'Despesa'),
    ('Saúde', 'Despesa'),
    ('Educação', 'Despesa'),
    ('Lazer', 'Despesa'),
    ('Utilidades', 'Despesa'),
    ('Seguros', 'Despesa'),
    ('Impostos', 'Despesa'),
    ('Outros', 'Despesa')
) AS valores(nome, tipo)
WHERE NOT EXISTS (
    SELECT 1 FROM categorias WHERE nome = valores.nome
);
"""

# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================

def criar_banco():
    """Cria o banco de dados ContasOrcamento se não existir"""
    print(f"🔗 Conectando ao servidor PostgreSQL em {DB_HOST}:{DB_PORT}...")
    
    try:
        with psycopg.connect(conninfo=CONN_BASE, autocommit=True) as conn:
            with conn.cursor() as cur:
                print(f"📁 Criando banco de dados: {DB_TARGET}...")
                cur.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(DB_TARGET)
                ))
                print(f"✅ Banco '{DB_TARGET}' criado com sucesso!")
                return True
                
    except DuplicateDatabase:
        print(f"ℹ️  Banco '{DB_TARGET}' já existe. Prosseguindo...")
        return True
    except psycopg.Error as e:
        print(f"❌ Erro ao criar banco: {e}")
        return False

def criar_tabelas():
    """Cria todas as tabelas, índices e views no banco alvo"""
    print(f"\n🔗 Conectando ao banco '{DB_TARGET}'...")
    
    try:
        with psycopg.connect(conninfo=CONN_TARGET, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("📋 Executando criação de tabelas...")
                cur.execute(SQL_TABELAS)
                print("✅ Tabelas criadas com sucesso!")
                
                print("📑 Criando índices de performance...")
                # Índices já estão no SQL_TABELAS com CREATE INDEX IF NOT EXISTS
                print("✅ Índices configurados!")
                
                print("👁 Criando view de resumo...")
                # View já está no SQL_TABELAS
                print("✅ View 'vw_resumo_mensal' criada!")
                
                return True
                
    except psycopg.Error as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

def popular_dados_iniciais():
    """Insere categorias padrão no banco"""
    print(f"\n📦 Populando dados iniciais em '{DB_TARGET}'...")
    
    try:
        with psycopg.connect(conninfo=CONN_TARGET, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(SQL_CATEGORIAS_PADRAO)
                print("✅ Categorias padrão inseridas!")
                return True
    except psycopg.Error as e:
        print(f"⚠️ Aviso ao popular dados (pode já existir): {e}")
        return True  # Não é erro crítico

def verificar_estrutura():
    """Exibe resumo da estrutura criada"""
    print(f"\n🔍 Verificando estrutura do banco '{DB_TARGET}'...")
    
    try:
        with psycopg.connect(conninfo=CONN_TARGET, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Listar tabelas
                cur.execute("""
                    SELECT table_name, 
                           (SELECT COUNT(*) FROM information_schema.columns 
                            WHERE table_name = t.table_name AND table_schema = 'public') as cols
                    FROM information_schema.tables t
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tabelas = cur.fetchall()
                
                print("\n📊 Tabelas criadas:")
                for nome, cols in tabelas:
                    print(f"   • {nome:<30} ({cols} colunas)")
                
                # Contar registros iniciais
                cur.execute("SELECT COUNT(*) FROM categorias")
                count_cat = cur.fetchone()[0]
                print(f"\n📈 Registros iniciais:")
                print(f"   • categorias: {count_cat}")
                
                return True
                
    except psycopg.Error as e:
        print(f"⚠️ Não foi possível verificar: {e}")
        return False

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("  🗄️  SETUP BANCO DE DADOS - Projeto Contas Orçamento")
    print("=" * 70)
    print(f"🎯 Banco alvo: {DB_TARGET}")
    print(f"🔗 Conexão: {DB_USER}@{DB_HOST}:{DB_PORT}")
    print("=" * 70 + "\n")
    
    # Passo 1: Criar banco
    if not criar_banco():
        print("\n❌ Falha na criação do banco. Encerrando.")
        sys.exit(1)
    
    # Passo 2: Criar tabelas
    if not criar_tabelas():
        print("\n❌ Falha na criação das tabelas. Encerrando.")
        sys.exit(1)
    
    # Passo 3: Popular dados
    popular_dados_iniciais()
    
    # Passo 4: Verificar
    verificar_estrutura()
    
    print("\n" + "=" * 70)
    print("  🎉 SETUP CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print(f"\n✅ Banco '{DB_TARGET}' está pronto para uso.")
    print(f"\n🔗 String de conexão para sua aplicação:")
    print(f'   DATABASE_URL = "postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_TARGET}"')
    print("\n📋 Próximo passo: Configurar app.py com esta URL e iniciar a aplicação.")
    print("=" * 70)

if __name__ == "__main__":
    main()