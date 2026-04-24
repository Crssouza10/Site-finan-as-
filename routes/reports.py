from flask_login import login_required
from flask import Blueprint, request, redirect, url_for, flash, Response, send_file
from fpdf import FPDF
from sqlalchemy import func, extract
from datetime import datetime
import io
import csv
from database import db
from models import Pagamento, Categoria

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/gerar_pdf')
@login_required
def gerar_pdf():
    """Gerar relatórios PDF - Mensal, Anual e Por Conta"""
    tipo = request.args.get('tipo', 'mensal')
    mes_ano = request.args.get('MesAno', '').strip()
    relatorio_ano = request.args.get('relatorio_ano', '').strip()
    relatorio_conta = request.args.get('relatorio_conta', '').strip()
    
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        
        if tipo == 'anual' and relatorio_ano:
            pdf.cell(0, 10, f"RELATÓRIO ANUAL DETALHADO - {relatorio_ano}", 0, 1, 'C')
            pdf.ln(5)
            resultados = db.session.query(
                Pagamento.conta, func.sum(Pagamento.valor_pagar).label('total_ano'), func.count(Pagamento.cod).label('qtd')
            ).filter(Pagamento.mes_ano.ilike(f"%/{relatorio_ano}")).group_by(Pagamento.conta).order_by(func.sum(Pagamento.valor_pagar).desc()).all()
            
            total_geral = sum(float(r.total_ano or 0) for r in resultados)
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(70, 130, 180)
            pdf.cell(90, 8, "CONTA", 1, 0, 'L', True)
            pdf.cell(50, 8, "TOTAL ANUAL (R$)", 1, 0, 'R', True)
            pdf.cell(40, 8, "QTD. REGISTROS", 1, 1, 'C', True)
            
            pdf.set_font("Arial", "", 9)
            for r in resultados:
                pdf.cell(90, 6, r.conta or "N/A", 1)
                pdf.cell(50, 6, f"R$ {float(r.total_ano or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R')
                pdf.cell(40, 6, str(r.qtd), 1, 1, 'C')
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(200, 220, 240)
            pdf.cell(90, 8, "TOTAL GERAL", 1, 0, 'R', True)
            pdf.cell(50, 8, f"R$ {total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R', True)
            pdf.cell(40, 8, f"{len(resultados)} contas", 1, 1, 'C', True)
            filename = f"relatorio_anual_{relatorio_ano}.pdf"
            
        elif tipo == 'conta' and relatorio_ano and relatorio_conta:
            pdf.cell(0, 10, f"RELATÓRIO POR CONTA: {relatorio_conta}", 0, 1, 'C')
            pdf.cell(0, 8, f"Ano: {relatorio_ano}", 0, 1, 'C')
            pdf.ln(5)
            pagamentos = Pagamento.query.filter(
                Pagamento.conta.ilike(f"%{relatorio_conta}%"), Pagamento.mes_ano.ilike(f"%/{relatorio_ano}")
            ).order_by(func.to_date(Pagamento.mes_ano, 'MM/YYYY').asc(), Pagamento.data_venc.asc()).all()
            
            total_ano = sum(float(p.valor_pagar or 0) for p in pagamentos)
            total_pago = sum(float(p.valor_pago or 0) for p in pagamentos)
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(70, 130, 180)
            pdf.cell(30, 7, "MÊS/ANO", 1, 0, 'C', True)
            pdf.cell(30, 7, "VENCIMENTO", 1, 0, 'C', True)
            pdf.cell(45, 7, "VALOR A PAGAR", 1, 0, 'R', True)
            pdf.cell(35, 7, "VALOR PAGO", 1, 0, 'R', True)
            pdf.cell(40, 7, "SITUAÇÃO", 1, 1, 'C', True)
            
            pdf.set_font("Arial", "", 8)
            for p in pagamentos:
                situacao = "PAGO" if (p.valor_pago and float(p.valor_pago) > 0) else "PENDENTE"
                pdf.cell(30, 6, p.mes_ano or "-", 1)
                pdf.cell(30, 6, p.data_venc or "-", 1)
                pdf.cell(45, 6, f"R$ {float(p.valor_pagar or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R')
                pdf.cell(35, 6, f"R$ {float(p.valor_pago or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R')
                pdf.cell(40, 6, situacao, 1, 1, 'C')
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(200, 220, 240)
            pdf.cell(60, 8, "TOTAL DO ANO:", 1, 0, 'R', True)
            pdf.cell(45, 8, f"R$ {total_ano:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R', True)
            pdf.cell(35, 8, f"R$ {total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 1, 0, 'R', True)
            pdf.cell(40, 8, f"{len(pagamentos)} registros", 1, 1, 'C', True)
            filename = f"relatorio_conta_{relatorio_conta}_{relatorio_ano}.pdf"
            
        else:
            titulo = f"RELATÓRIO MENSAL - {mes_ano}" if mes_ano else "RELATÓRIO MENSAL"
            pdf.cell(0, 10, titulo, 0, 1, 'C')
            pdf.ln(5)
            query = Pagamento.query.order_by(Pagamento.data_venc)
            if mes_ano: query = query.filter(Pagamento.mes_ano.ilike(f"%{mes_ano}%"))
            pagamentos = query.all()
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(70, 130, 180)
            pdf.cell(25, 7, "Vencimento", 1, 0, 'C', True)
            pdf.cell(50, 7, "Conta", 1, 0, 'L', True)
            pdf.cell(35, 7, "Categoria", 1, 0, 'L', True)
            pdf.cell(30, 7, "Valor", 1, 0, 'R', True)
            pdf.cell(30, 7, "Status", 1, 1, 'C', True)
            
            pdf.set_font("Arial", "", 8)
            for p in pagamentos:
                status = "Pago" if p.valor_pago and p.valor_pago > 0 else "Pendente"
                categoria = p.categoria_ref.nome if p.categoria_ref else "-"
                pdf.cell(25, 6, p.data_venc or "-", 1)
                pdf.cell(50, 6, p.conta or "-", 1)
                pdf.cell(35, 6, categoria, 1)
                pdf.cell(30, 6, f"R$ {p.valor_pagar or 0:.2f}", 1, 0, 'R')
                pdf.cell(30, 6, status, 1, 1, 'C')
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"TOTAL: R$ {sum(float(p.valor_pagar or 0) for p in pagamentos):.2f}", 0, 1, 'R')
            filename = f"relatorio_mensal_{mes_ano or 'geral'}.pdf"
        
        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf', headers={'Content-Disposition': f'inline; filename={filename}'})
    except Exception as e:
        flash(f"❌ Erro ao gerar PDF: {e}", "danger")
        return redirect(url_for('main.index'))

@reports_bp.route('/gerar_relatorio_anual')
@login_required
def gerar_relatorio_anual():
    """Gera relatório anual consolidado de Receitas vs Despesas"""
    ano = request.args.get('ano', datetime.now().year)
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 15, f"RELATÓRIO ANUAL - {ano}", 0, 1, 'C')
        pdf.cell(0, 8, "Receitas vs Despesas", 0, 1, 'C')
        pdf.ln(5)
        
        receitas_totais = db.session.query(func.sum(Pagamento.valor_pago)).filter(
            Pagamento.mes_ano.ilike(f"%/{ano}"), Pagamento.receita_despesa == 'R', Pagamento.valor_pago > 0
        ).scalar() or 0
        
        despesas_totais = db.session.query(func.sum(Pagamento.valor_pago)).filter(
            Pagamento.mes_ano.ilike(f"%/{ano}"), Pagamento.receita_despesa == 'D', Pagamento.valor_pago > 0
        ).scalar() or 0
        
        saldo_anual = float(receitas_totais) - float(despesas_totais)
        pct_despesas = (float(despesas_totais) / float(receitas_totais) * 100) if float(receitas_totais) > 0 else 0
        
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "RESUMO DO ANO", 1, 1, 'C', True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(95, 8, "Total Receitas:", 1); pdf.cell(95, 8, f"R$ {float(receitas_totais):,.2f}", 1, 1, 'R')
        pdf.cell(95, 8, "Total Despesas:", 1); pdf.cell(95, 8, f"R$ {float(despesas_totais):,.2f}", 1, 1, 'R')
        pdf.set_font("Arial", "B", 11)
        pdf.cell(95, 8, "Saldo Anual:", 1)
        pdf.set_fill_color(220, 240, 220) if saldo_anual >= 0 else pdf.set_fill_color(255, 230, 230)
        pdf.cell(95, 8, f"R$ {saldo_anual:,.2f}", 1, 1, 'R', True)
        
        pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "EVOLUÇÃO MENSAL", 1, 1, 'C')
        pdf.set_font("Arial", "B", 9); pdf.set_fill_color(70, 130, 180)
        pdf.cell(30, 7, "MÊS", 1, 0, 'C', True); pdf.cell(40, 7, "RECEITAS", 1, 0, 'R', True); pdf.cell(40, 7, "DESPESAS", 1, 0, 'R', True); pdf.cell(40, 7, "SALDO", 1, 0, 'R', True); pdf.cell(30, 7, "ACUMULADO", 1, 1, 'R', True)
        
        pdf.set_font("Arial", "", 8); saldo_acumulado = 0
        for mes_num in range(1, 13):
            mes_str = f"{mes_num:02d}/{ano}"
            rec = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.mes_ano == mes_str, Pagamento.receita_despesa == 'R', Pagamento.valor_pago > 0).scalar() or 0
            desp = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.mes_ano == mes_str, Pagamento.receita_despesa == 'D', Pagamento.valor_pago > 0).scalar() or 0
            saldo_mes = float(rec) - float(desp); saldo_acumulado += saldo_mes
            pdf.cell(30, 6, ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][mes_num-1], 1)
            pdf.cell(40, 6, f"R$ {float(rec):,.2f}", 1, 0, 'R'); pdf.cell(40, 6, f"R$ {float(desp):,.2f}", 1, 0, 'R'); pdf.cell(40, 6, f"R$ {saldo_mes:,.2f}", 1, 0, 'R'); pdf.cell(30, 6, f"R$ {saldo_acumulado:,.2f}", 1, 1, 'R')
            
        filename = f"relatorio_anual_{ano}.pdf"
        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        flash(f"❌ Erro ao gerar relatório anual: {e}", "danger")
        return redirect(url_for('main.index'))

@reports_bp.route('/exportar_csv')
@login_required
def exportar_csv():
    """Exportar dados para CSV"""
    mes_ano = request.args.get('MesAno', '').strip()
    status = request.args.get('status', '').strip()
    query = Pagamento.query.order_by(Pagamento.data_venc)
    if mes_ano: query = query.filter(Pagamento.mes_ano.ilike(f"%{mes_ano}%"))
    if status == 'pago': query = query.filter(Pagamento.valor_pago > 0)
    elif status == 'pendente': query = query.filter((Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)))
    
    pagamentos = query.all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Cód', 'Mês/Ano', 'Conta', 'Categoria', 'Tipo', 'Vencimento', 'Valor Pagar', 'Data Pago', 'Valor Pago'])
    for p in pagamentos:
        writer.writerow([
            p.cod, p.mes_ano or '', p.conta or '', p.categoria_ref.nome if p.categoria_ref else '',
            'Receita' if p.receita_despesa == 'R' else 'Despesa', p.data_venc or '',
            f"{float(p.valor_pagar or 0):.2f}".replace('.', ','), p.data_pago or '', f"{float(p.valor_pago or 0):.2f}".replace('.', ',')
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name=f'pagamentos_{datetime.now().strftime("%Y%m%d")}.csv')
@reports_bp.route('/gerar_relatorio_ia')
@login_required
def gerar_relatorio_ia():
    """Gera o Relatório de Saúde Financeira Preditiva via IA"""
    mes_ano = request.args.get('mes_ano', datetime.now().strftime('%m/%Y'))
    try:
        # 1. Coleta de Dados para a IA
        # (Lógica similar ao motor de insights do dashboard)
        mes_ant_ref = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%m/%Y') if mes_ano == datetime.now().strftime('%m/%Y') else ""
        
        receitas = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'R').scalar() or 0
        despesas = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'D').scalar() or 0
        saldo = float(receitas) - float(despesas)
        taxa_poupanca = (saldo / float(receitas) * 100) if float(receitas) > 0 else 0

        # 2. Construção do PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho SmartWallet AI
        pdf.set_fill_color(2, 6, 23) # Navy Dark
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 20)
        pdf.image('https://cdn-icons-png.flaticon.com/512/4712/4712109.png', 10, 10, 20) # Robot icon fallback
        pdf.set_xy(35, 15)
        pdf.cell(0, 10, "SmartWallet AI | Financial Health Report", 0, 1, 'L')
        
        # Conteúdo do Relatório
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(10, 50)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Periodo de Analise: {mes_ano}", 0, 1)
        pdf.line(10, 60, 200, 60)
        
        # KPIs Principais
        pdf.ln(10)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(245, 247, 250)
        pdf.cell(60, 20, "Receitas Totais", 1, 0, 'C', True)
        pdf.cell(60, 20, "Despesas Totais", 1, 0, 'C', True)
        pdf.cell(70, 20, "Saldo Liquido", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 12)
        pdf.cell(60, 15, f"R$ {float(receitas):,.2f}", 1, 0, 'C')
        pdf.cell(60, 15, f"R$ {float(despesas):,.2f}", 1, 0, 'C')
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 15, f"R$ {saldo:,.2f}", 1, 1, 'C')

        # Seção de Insights da IA
        pdf.ln(15)
        pdf.set_fill_color(59, 130, 246)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, " PARECER DA INTELIGENCIA ARTIFICIAL", 0, 1, 'L', True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        pdf.set_font("Arial", "", 11)
        
        intro = f"Com base na analise dos seus dados de {mes_ano}, identificamos que sua saude financeira esta em um patamar "
        intro += "positivo." if saldo > 0 else "de alerta."
        pdf.multi_cell(0, 7, intro)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, "Principais Observacoes:", 0, 1)
        pdf.set_font("Arial", "", 10)
        
        insights_text = [
            f"- Taxa de Poupanca: Voce reservou {taxa_poupanca:.1f}% da sua receita.",
            "- Padrao de Gastos: Seus gastos estao concentrados em categorias essenciais." if taxa_poupanca > 10 else "- Alerta: Seus gastos fixos estao consumindo grande parte da sua renda.",
            "- Projecao: Mantendo este ritmo, voce atingira suas metas anuais com tranquilidade." if saldo > 0 else "- Recomendacao: Revise seus gastos variaveis para evitar endividamento futuro."
        ]
        
        for text in insights_text:
            pdf.multi_cell(0, 7, text)

        # Footer
        pdf.set_y(-30)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} por SmartWallet AI - Educacao Financeira Preditiva", 0, 0, 'C')

        filename = f"saude_financeira_{mes_ano.replace('/', '_')}.pdf"
        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename={filename}'})
        
    except Exception as e:
        flash(f"Erro ao gerar relatorio IA: {str(e)}", "error")
        return redirect(url_for('dashboard.dashboard'))

from datetime import timedelta # Garantir importacao
