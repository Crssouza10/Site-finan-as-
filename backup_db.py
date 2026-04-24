# backup_db.py
import psycopg2
import datetime
import zipfile
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

def criar_backup():
    """Backup usando apenas psycopg2 - SEM subprocess, SEM pg_dump.exe"""
    
    # Configurações (Carregadas do .env)
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '200466'),
        'dbname': os.getenv('DB_NAME', 'ContasOrcamento')
    }
    
    # Pasta de backups
    backup_dir = Path(__file__).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_file = backup_dir / f"backup_{timestamp}.sql"
    
    conn = None
    try:
        print(f"🔄 Conectando ao banco '{DB_CONFIG['dbname']}'...")
        
        # Conecta ao banco
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        print(f"✅ Conexão OK. Exportando tabelas...")
        
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Backup: {DB_CONFIG['dbname']}\n")
            f.write(f"-- Data: {datetime.datetime.now()}\n\n")
            
            # Tabelas para backup (ajuste conforme seu schema real)
            tabelas = ['categorias', 'pagamentos', 'documentos_pagamento']
            
            for tabela in tabelas:
                print(f"  📋 {tabela}...")
                f.write(f"\n-- {tabela}\n")
                
                try:
                    # Exporta dados
                    cur.execute(f"SELECT * FROM {tabela}")
                    rows = cur.fetchall()
                    
                    if rows:
                        cols = [desc[0] for desc in cur.description]
                        for row in rows:
                            values = []
                            for val in row:
                                if val is None:
                                    values.append('NULL')
                                elif isinstance(val, str):
                                    # Escapa aspas para SQL
                                    values.append(f"'{val.replace(chr(39), chr(39)+chr(39))}'")
                                elif isinstance(val, (datetime.datetime, datetime.date)):
                                    values.append(f"'{val.isoformat()}'")
                                else:
                                    values.append(str(val))
                            f.write(f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({', '.join(values)});\n")
                except Exception as e:
                    f.write(f"-- ⚠️ Erro em {tabela}: {e}\n")
                    print(f"  ⚠️ {e}")
            
            cur.close()
        
        # Compacta em ZIP
        zip_file = backup_dir / f"backup_{timestamp}.zip"
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(sql_file, sql_file.name)
        sql_file.unlink()  # Remove SQL solto
        
        print(f"\n✅ BACKUP CRIADO: {zip_file.name}")
        print(f"📍 Local: {backup_dir.absolute()}")
        return str(zip_file)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        raise
    finally:
        if conn:
            conn.close()
            print("🔌 Conexão fechada.")

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BACKUP INICIADO")
    print("=" * 50)
    try:
        criar_backup()
        print("\n🎉 SUCESSO!")
    except Exception as e:
        print(f"\n❌ FALHA: {e}")