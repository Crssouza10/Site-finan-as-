import sys
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Adiciona raiz do projeto ao path para importar do app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import carregar_config_email

def enviar_alerta_vencimento(contas_vencendo):
    """Envia e-mail com contas próximas do vencimento"""
    try:
        # Carrega configuração
        config = carregar_config_email()
        email_destino = config.get('email_destino')
        
        if not config.get('alertas_ativos', True):
            print("🔕 Alertas desativados nas configurações")
            return False
        
        host = os.getenv('EMAIL_HOST')
        port = int(os.getenv('EMAIL_PORT', 587))
        user = os.getenv('EMAIL_USER')
        pwd = os.getenv('EMAIL_PASSWORD')
        
        if not all([host, port, user, pwd, email_destino]):
            print("⚠️ Configuração de e-mail incompleta")
            return False

        # ... (resto do código permanece igual)

        # Monta HTML do e-mail
        linhas = ""
        for c in contas_vencendo:
            dias_restantes = (datetime.strptime(c['data_venc'], '%d/%m/%Y') - datetime.now()).days
            cor = "#dc3545" if dias_restantes <= 2 else "#f39c12" if dias_restantes <= 5 else "#28a745"
            linhas += f"""
            <tr>
                <td>{c['mes_ano']}</td>
                <td>{c['conta']}</td>
                <td>{c['data_venc']}</td>
                <td style="color:{cor}; font-weight:bold;">R$ {float(c['valor_pagar']):,.2f}</td>
                <td>{dias_restantes} dias</td>
            </tr>"""

        html = f"""
        <html><body style="font-family:Arial,sans-serif;">
        <h2>🔔 Alerta de Contas Próximas do Vencimento</h2>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; width:100%;">
            <tr style="background:#1a252f; color:white;">
                <th>Mês/Ano</th><th>Conta</th><th>Vencimento</th><th>Valor</th><th>Dias Restantes</th>
            </tr>
            {linhas}
        </table>
        <p style="margin-top:20px; color:#666; font-size:12px;">Este é um alerta automático do Sistema de Gestão Financeira.</p>
        </body></html>"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔔 {len(contas_vencendo)} contas vencendo nos próximos 7 dias"
        msg['From'] = user
        msg['To'] = email_destino
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
        
        print(f"✅ E-mail enviado para {email_destino} com {len(contas_vencendo)} alertas")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")
        return False