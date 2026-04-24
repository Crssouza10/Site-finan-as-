import psycopg
import sys
from psycopg.errors import DuplicateDatabase

# Configuração de conexão para um banco padrão (geralmente 'postgres' ou 'template1')
# Usamos 'postgres' como destino inicial para poder criar 'contas_pagamento'
DB_URL_BASE = "postgresql://postgres:200466@localhost:5432/postgres" 
NOVO_DB_NOME = "contas_pagamento"

def criar_banco_de_dados():
    """Conecta ao banco 'postgres' e cria o novo banco 'contas_pagamento'."""
    conn = None
    try:
        # 1. Conecta ao banco de dados padrão 'postgres'
        print(f"Tentando conectar ao banco base: {DB_URL_BASE.split('@')[-1]}")
        conn = psycopg.connect(conninfo=DB_URL_BASE, autocommit=True)
        print("Conexão ao banco base estabelecida com sucesso.")
        
        # O cursor deve ser isolado (sem BEGIN/COMMIT) para comandos de CREATE DATABASE
        with conn.cursor() as cur:
            # 2. Executa o comando de criação
            print(f"Criando banco de dados: {NOVO_DB_NOME}...")
            cur.execute(f"CREATE DATABASE {NOVO_DB_NOME};")
            print(f"Banco de dados '{NOVO_DB_NOME}' criado com sucesso!")
            
    except DuplicateDatabase:
        print(f"Aviso: O banco de dados '{NOVO_DB_NOME}' já existe.")
        
    except psycopg.Error as e:
        print(f"\nOcorreu um erro ao conectar ou criar o banco de dados:")
        print(e)
        sys.exit(1)
        
    finally:
        if conn:
            conn.close()
            print("Conexão fechada.")

if __name__ == '__main__':
    criar_banco_de_dados()