#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 INSPETOR DE BANCO DE DADOS POSTGRESQL
Projeto: Contas Pagamento / Contas Orçamento
"""

import psycopg
from psycopg import sql
from tabulate import tabulate
from datetime import datetime

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================
DB_URL_BASE = "postgresql://postgres:200466@localhost:5432/postgres"
NOVO_DB_NOME = "Orcamento"  # Altere para "ContasOrcamento" se necessário

def get_connection(db_name):
    """Retorna conexão com o banco especificado"""
    return psycopg.connect(
        conninfo=f"postgresql://postgres:200466@localhost:5432/{db_name}",
        autocommit=True
    )

# =============================================================================
# FUNÇÕES DE INSPEÇÃO
# =============================================================================

def listar_tabelas(cursor):
    """Lista todas as tabelas do banco"""
    cursor.execute("""
        SELECT 
            table_name,
            table_schema,
            (SELECT COUNT(*) FROM information_schema.columns 
             WHERE table_name = t.table_name AND table_schema = t.table_schema) as col_count
        FROM information_schema.tables t
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    return cursor.fetchall()

def detalhar_tabela(cursor, tabela):
    """Retorna detalhes completos de uma tabela"""
    detalhes = {}
    
    # 1. Colunas e tipos
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default,
            CASE WHEN pk.column_name IS NOT NULL THEN 'PK' ELSE '' END as key_type
        FROM information_schema.columns c
        LEFT JOIN (
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = %s 
            AND tc.constraint_type = 'PRIMARY KEY'
        ) pk ON c.column_name = pk.column_name
        WHERE c.table_name = %s 
        AND c.table_schema = 'public'
        ORDER BY c.ordinal_position;
    """, (tabela, tabela))
    detalhes['colunas'] = cursor.fetchall()
    
    # 2. Chaves Estrangeiras
    cursor.execute("""
        SELECT 
            kcu.column_name as coluna,
            ccu.table_name as tabela_ref,
            ccu.column_name as coluna_ref
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = %s 
        AND tc.constraint_type = 'FOREIGN KEY';
    """, (tabela,))
    detalhes['foreign_keys'] = cursor.fetchall()
    
    # 3. Índices
    cursor.execute("""
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = %s 
        AND schemaname = 'public';
    """, (tabela,))
    detalhes['indices'] = cursor.fetchall()
    
    # 4. Contagem de registros
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(tabela)))
    detalhes['count'] = cursor.fetchone()[0]
    
    # 5. Amostra de dados (até 5 registros)
    cursor.execute(sql.SQL("SELECT * FROM {} LIMIT 5").format(sql.Identifier(tabela)))
    detalhes['amostra'] = cursor.fetchall()
    detalhes['colunas_amostra'] = [desc[0] for desc in cursor.description]
    
    return detalhes

def imprimir_cabecalho(titulo):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 70)
    print(f"  {titulo}")
    print("=" * 70)

def formatar_valor(valor):
    """Formata valores para exibição"""
    if valor is None:
        return "NULL"
    if isinstance(valor, datetime):
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, bytes):
        return f"<BLOB {len(valor)} bytes>"
    return str(valor)

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def inspecionar_banco():
    """Executa a inspeção completa do banco"""
    
    imprimir_cabecalho("🔍 INSPETOR POSTGRESQL - Projeto Contas")
    print(f"📁 Banco: {NOVO_DB_NOME}")
    print(f"🔗 Servidor: localhost:5432")
    print(f"🕐 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    try:
        # Conectar ao banco
        print(f"\n🔗 Conectando ao banco '{NOVO_DB_NOME}'...")
        conn = get_connection(NOVO_DB_NOME)
        cursor = conn.cursor()
        print("✅ Conexão estabelecida!\n")
        
        # 1. Listar tabelas
        imprimir_cabecalho("📊 TABELAS DO BANCO")
        tabelas = listar_tabelas(cursor)
        
        if not tabelas:
            print("⚠️  Nenhuma tabela encontrada no banco.")
        else:
            dados_tabelas = []
            for t in tabelas:
                dados_tabelas.append([t[0], t[1], t[2]])
            
            print(tabulate(
                dados_tabelas,
                headers=["Tabela", "Schema", "Colunas"],
                tablefmt="grid"
            ))
        
        # 2. Detalhar cada tabela
        for tabela_info in tabelas:
            tabela = tabela_info[0]
            imprimir_cabecalho(f"📋 TABELA: {tabela.upper()}")
            
            detalhes = detalhar_tabela(cursor, tabela)
            
            # 2.1 Colunas
            print(f"\n🔹 COLUNAS ({len(detalhes['colunas'])}):")
            colunas_data = []
            for col in detalhes['colunas']:
                nome, tipo, max_len, prec, scale, nullable, default, key = col
                tipo_completo = tipo
                if max_len:
                    tipo_completo += f"({max_len})"
                elif prec and scale:
                    tipo_completo += f"({prec},{scale})"
                elif prec:
                    tipo_completo += f"({prec})"
                
                colunas_data.append([
                    f"{key} {nome}" if key else nome,
                    tipo_completo,
                    "NÃO" if nullable == 'NO' else "SIM",
                    default or "-"
                ])
            
            print(tabulate(
                colunas_data,
                headers=["Coluna", "Tipo", "Nulo?", "Padrão"],
                tablefmt="simple"
            ))
            
            # 2.2 Chaves Estrangeiras
            if detalhes['foreign_keys']:
                print(f"\n🔗 CHAVES ESTRANGEIRAS:")
                fk_data = []
                for fk in detalhes['foreign_keys']:
                    fk_data.append([fk[0], fk[1], fk[2]])
                print(tabulate(
                    fk_data,
                    headers=["Coluna", "Tabela Ref.", "Coluna Ref."],
                    tablefmt="simple"
                ))
            
            # 2.3 Índices
            if detalhes['indices']:
                print(f"\n📑 ÍNDICES:")
                for idx in detalhes['indices']:
                    print(f"   • {idx[0]}")
            
            # 2.4 Contagem
            print(f"\n📈 Registros: {detalhes['count']:,}")
            
            # 2.5 Amostra de dados
            if detalhes['amostra'] and detalhes['count'] > 0:
                print(f"\n🔎 AMOSTRA (até 5 registros):")
                amostra_data = []
                for row in detalhes['amostra']:
                    amostra_data.append([formatar_valor(v) for v in row])
                
                print(tabulate(
                    amostra_data,
                    headers=detalhes['colunas_amostra'],
                    tablefmt="simple",
                    maxcolwidths=[30] * len(detalhes['colunas_amostra'])
                ))
        
        # 3. Resumo Final
        imprimir_cabecalho("📊 RESUMO FINAL")
        total_tabelas = len(tabelas)
        total_registros = sum(detalhar_tabela(cursor, t[0])['count'] for t in tabelas)
        
        print(f"✅ Total de tabelas: {total_tabelas}")
        print(f"✅ Total de registros: {total_registros:,}")
        print(f"✅ Espaço estimado: Consulte pg_total_relation_size para detalhar")
        
        cursor.close()
        conn.close()
        print("\n🎉 Inspeção concluída com sucesso!")
        
    except psycopg.Error as e:
        print(f"\n❌ Erro de conexão/consulta: {e}")
        print("\n💡 Verifique:")
        print("   • PostgreSQL está rodando?")
        print("   • Banco 'contas_pagamento' foi criado?")
        print("   • Senha '200466' está correta?")
        print("   • Porta 5432 está liberada?")
        
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

# =============================================================================
# EXECUÇÃO
# =============================================================================

if __name__ == "__main__":
    inspecionar_banco()