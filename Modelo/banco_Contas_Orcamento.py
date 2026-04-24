import psycopg
import sys
from psycopg.errors import DuplicateDatabase

# Configuração de conexão
DB_URL_BASE = "postgresql://postgres:200466@localhost:5432/postgres"
NOVO_DB_NOME = "ContasOrcamento"

def criar_banco_de_dados():
    """Conecta ao banco 'postgres' e cria o novo banco 'ContasOrcamento'."""
    conn = None
    try:
        print(f"🔗 Conectando ao servidor PostgreSQL...")
        conn = psycopg.connect(conninfo=DB_URL_BASE, autocommit=True)
        print("✅ Conexão estabelecida com sucesso.")
        
        with conn.cursor() as cur:
            print(f"📁 Criando banco de dados: {NOVO_DB_NOME}...")
            cur.execute(f'CREATE DATABASE "{NOVO_DB_NOME}";')
            print(f"✅ Banco de dados '{NOVO_DB_NOME}' criado com sucesso!")
            
    except DuplicateDatabase:
        print(f"⚠️  Aviso: O banco de dados '{NOVO_DB_NOME}' já existe.")
        
    except psycopg.Error as e:
        print(f"\n❌ Erro ao criar banco de dados:")
        print(e)
        sys.exit(1)
        
    finally:
        if conn:
            conn.close()
            print("🔌 Conexão fechada.")

if __name__ == '__main__':
    criar_banco_de_dados()


    -- Recriar tabela documentos_pagamento
CREATE TABLE IF NOT EXISTS documentos_pagamento (
    id SERIAL PRIMARY KEY,
    pagamento_id INTEGER REFERENCES pagamentos(cod) ON DELETE CASCADE,
    nome_arquivo VARCHAR(255) NOT NULL,
    tipo_mime VARCHAR(100) DEFAULT 'application/pdf',
    conteudo BYTEA,
    data_upload TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Criar índice para melhor performance
CREATE INDEX IF NOT EXISTS idx_documentos_pagamento_id 
ON documentos_pagamento(pagamento_id);

-- Mensagem de confirmação
SELECT '✅ Tabela documentos_pagamento criada com sucesso!' as status;