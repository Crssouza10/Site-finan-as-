#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migração do banco de dados.
Adiciona colunas faltantes nas tabelas existentes.
Execute da RAIZ do projeto: python atualizar_banco.py
"""

import sys
import os

# ✅ ADICIONAR RAIZ DO PROJETO AO PYTHON PATH
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

print(f"📁 Raiz do projeto: {root_dir}")

from app import app, db, Pagamento, Categoria, Documento
from sqlalchemy import inspect, text, Column, DateTime, String
from datetime import datetime

def get_existing_columns(table_name):
    """Retorna lista de colunas existentes em uma tabela"""
    try:
        inspector = inspect(db.engine)
        return [c['name'] for c in inspector.get_columns(table_name)]
    except Exception as e:
        print(f"⚠️ Não foi possível inspecionar tabela '{table_name}': {e}")
        return []

def add_column_if_not_exists(table_name, column_name, column_type, default=None):
    """Adiciona coluna se não existir"""
    columns = get_existing_columns(table_name)
    
    if column_name not in columns:
        print(f"   ➕ Adicionando: {table_name}.{column_name} {column_type}")
        try:
            with db.engine.connect() as conn:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                if default is not None:
                    sql += f" DEFAULT {default}"
                conn.execute(text(sql))
                conn.commit()
            print(f"   ✅ Sucesso!")
            return True
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            return False
    else:
        print(f"   ✅ Já existe: {table_name}.{column_name}")
        return True

def migrate_categorias_table():
    """Migra tabela categorias com colunas faltantes"""
    print("\n🔄 Migrando tabela 'categorias'...")
    
    migrations = [
        ('data_criacao', 'TIMESTAMP', "NOW()"),
        # Adicione aqui outras colunas do modelo Categoria se necessário
    ]
    
    success = True
    for col_name, col_type, default in migrations:
        if not add_column_if_not_exists('categorias', col_name, col_type, default):
            success = False
    
    return success

def migrate_pagamentos_table():
    """Migra tabela pagamentos com colunas faltantes"""
    print("\n🔄 Migrando tabela 'pagamentos'...")
    
    migrations = [
        ('competencia', 'VARCHAR(10)', None),
        ('juros', 'NUMERIC(10,2)', '0'),
        ('desconto', 'NUMERIC(10,2)', '0'),
    ]
    
    success = True
    for col_name, col_type, default in migrations:
        if not add_column_if_not_exists('pagamentos', col_name, col_type, default):
            success = False
    
    return success

def migrate_documentos_table():
    """Migra tabela documentos_pagamento se necessário"""
    print("\n🔄 Migrando tabela 'documentos_pagamento'...")
    
    migrations = [
        ('data_upload', 'TIMESTAMP', "NOW()"),
        ('tamanho', 'INTEGER', None),
    ]
    
    success = True
    for col_name, col_type, default in migrations:
        if not add_column_if_not_exists('documentos_pagamento', col_name, col_type, default):
            success = False
    
    return success

def garantir_categoria_outros():
    """Garante que a categoria 'OUTROS' exista (usando raw SQL para evitar erro do modelo)"""
    print("\n🔄 Garantindo categoria 'OUTROS'...")
    
    try:
        # Usar SQL direto para evitar erro com colunas faltantes no modelo
        with db.engine.connect() as conn:
            # Verifica se já existe
            result = conn.execute(
                text("SELECT id FROM categorias WHERE nome = :nome"),
                {"nome": "OUTROS"}
            ).fetchone()
            
            if not result:
                # Insere sem especificar data_criacao (usará DEFAULT ou NULL)
                conn.execute(
                    text("INSERT INTO categorias (nome, tipo) VALUES (:nome, :tipo)"),
                    {"nome": "OUTROS", "tipo": "D"}
                )
                conn.commit()
                print("   ➕ Categoria 'OUTROS' criada!")
            else:
                print("   ✅ Categoria 'OUTROS' já existe!")
        return True
    except Exception as e:
        print(f"⚠️ Aviso ao criar categoria: {e}")
        return False  # Não é crítico falhar aqui

def listar_categorias_simples():
    """Lista categorias usando SQL direto (evita erro do modelo)"""
    print("\n📋 Categorias cadastradas:")
    try:
        with db.engine.connect() as conn:
            result = conn.execute(
                text("SELECT nome, tipo FROM categorias ORDER BY nome")
            ).fetchall()
            
            for nome, tipo in result:
                tipo_str = "🟢 Receita" if tipo == 'R' else "🔴 Despesa"
                print(f"   • {nome:20s} [{tipo_str}]")
            print(f"   Total: {len(result)} categoria(s)")
    except Exception as e:
        print(f"⚠️ Não foi possível listar categorias: {e}")

def main():
    print("=" * 70)
    print("🔧 MIGRAÇÃO DO BANCO DE DADOS - ContasOrcamento")
    print("=" * 70)
    
    with app.app_context():
        # 1. Migrar tabelas
        print("\n📊 Verificando estrutura das tabelas...")
        
        migrate_categorias_table()
        migrate_pagamentos_table()
        migrate_documentos_table()
        
        # 2. Garantir categoria OUTROS
        garantir_categoria_outros()
        
        # 3. Listar categorias (com fallback)
        listar_categorias_simples()
        
        print("\n" + "=" * 70)
        print("✅ Migração concluída!")
        print("🚀 Agora execute: python app.py")
        print("=" * 70)

if __name__ == '__main__':
    main()