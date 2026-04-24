import schedule
import time
import logging
from datetime import datetime
import sys
import os

# Adiciona raiz do projeto ao path
sys.path.append(os.path.dirname(__file__))

from app import app
from utils.email_utils import enviar_alerta_vencimento

# Configura logging
logging.basicConfig(
    filename='scheduler.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def job_backup():
    """Executa backup e limpa antigos"""
    try:
        from backup_db import criar_backup
        zip_path = criar_backup()
        logging.info(f"✅ Backup criado: {zip_path}")
        
        # (Opcional) Limpar backups > 7 dias
        # ... lógica de cleanup ...
    except Exception as e:
        logging.error(f"❌ Falha no backup: {e}")

def job_alertas():
    """Busca alertas e envia e-mail"""
    with app.app_context():
        try:
            response = app.test_client().get('/api/notificacoes/alertas_vencimento')
            data = response.get_json()
            if data['total'] > 0:
                enviar_alerta_vencimento(data['contas'])
                logging.info(f"📧 {data['total']} alertas enviados por e-mail")
            else:
                logging.info("🔕 Nenhuma conta próxima do vencimento")
        except Exception as e:
            logging.error(f"❌ Falha nos alertas: {e}")

if __name__ == '__main__':
    print("🚀 Agendador iniciado. Pressione Ctrl+C para sair.")
    
    # Agenda tarefas
    schedule.every().day.at("23:00").do(job_backup)
    schedule.every().day.at("08:00").do(job_alertas)
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verifica a cada minuto