import sqlite3
from pathlib import Path

# Caminho do seu banco de dados
DB_PATH = r""postgresql://postgres:200466@localhost:5432/Orcamento"

def inspecionar_banco():
    try:
        # Verifica se o arquivo existe
        if not Path(DB_PATH).exists():
            print(f"❌ Arquivo não encontrado: {DB_PATH}")
            return
        
        print(f"✅ Banco encontrado: {DB_PATH}\n")
        
        # Conecta ao banco
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Lista todas as tabelas
        print("=" * 60)
        print("📁 TABELAS DO BANCO")
        print("=" * 60)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = cursor.fetchall()
        
        for tabela in tabelas:
            nome_tabela = tabela[0]
            print(f"\n📊 Tabela: {nome_tabela}")
            print("-" * 60)
            
            # 2. Lista colunas e propriedades de cada tabela
            cursor.execute(f"PRAGMA table_info({nome_tabela});")
            colunas = cursor.fetchall()
            
            print(f"{'Coluna':<25} {'Tipo':<15} {'Nulo':<10} {'Padrão':<20} {'PK':<5}")
            print("-" * 60)
            
            for col in colunas:
                cid, nome, tipo, notnull, default, pk = col
                print(f"{nome:<25} {tipo:<15} {'NÃO' if notnull else 'SIM':<10} {str(default):<20} {'✓' if pk else ''}")
            
            # 3. Conta registros
            cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela};")
            count = cursor.fetchone()[0]
            print(f"\n📈 Total de registros: {count}")
        
        # 4. Lista índices
        print("\n" + "=" * 60)
        print("📑 ÍNDICES")
        print("=" * 60)
        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index';")
        indices = cursor.fetchall()
        for idx in indices:
            print(f"Índice: {idx[0]} na tabela {idx[1]}")
        
        conn.close()
        print("\n✅ Inspeção concluída!")
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao acessar banco: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    inspecionar_banco()