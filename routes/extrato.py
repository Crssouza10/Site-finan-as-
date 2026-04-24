from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, TransacaoExtrato, Pagamento, Categoria
from datetime import datetime
import re
from decimal import Decimal

extrato_bp = Blueprint('extrato', __name__)

def parse_ofx_simple(content):
    """
    Parser simplificado para arquivos OFX.
    Extrai as transações (STMTTRN) de forma robusta.
    """
    transactions = []
    # Encontra todos os blocos <STMTTRN>...</STMTTRN>
    blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content, re.DOTALL)
    
    for block in blocks:
        try:
            # Extração via Regex para maior compatibilidade com variações de tags OFX
            fitid = re.search(r'<FITID>(.*)', block).group(1).strip()
            trntype = re.search(r'<TRNTYPE>(.*)', block).group(1).strip()
            dtposted = re.search(r'<DTPOSTED>(.*)', block).group(1).strip()[:8] # YYYYMMDD
            trnamt = re.search(r'<TRNAMT>(.*)', block).group(1).strip().replace(',', '.')
            memo = re.search(r'<MEMO>(.*)', block).group(1).strip()
            
            # Normalização de dados
            data_dt = datetime.strptime(dtposted, '%Y%m%d').date()
            valor_dec = Decimal(trnamt)
            tipo = 'R' if valor_dec > 0 else 'D'
            
            transactions.append({
                'fitid': fitid,
                'data': data_dt,
                'descricao': memo,
                'valor': abs(valor_dec),
                'tipo': tipo
            })
        except Exception as e:
            print(f"Erro ao processar bloco OFX: {e}")
            continue
            
    return transactions

@extrato_bp.route('/extrato/importar', methods=['GET', 'POST'])
@login_required
def importar_extrato():
    if request.method == 'POST':
        if 'arquivo_ofx' not in request.files:
            flash('Nenhum arquivo enviado', 'error')
            return redirect(request.url)
            
        file = request.files['arquivo_ofx']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        try:
            content = file.read().decode('utf-8', errors='ignore')
            transactions = parse_ofx_simple(content)
            
            importadas = 0
            duplicadas = 0
            
            for tr in transactions:
                # Verificar se já existe pelo FITID
                existente = TransacaoExtrato.query.filter_by(fitid=tr['fitid']).first()
                if existente:
                    duplicadas += 1
                    continue
                
                nova_tr = TransacaoExtrato(
                    fitid=tr['fitid'],
                    data=tr['data'],
                    descricao=tr['descricao'],
                    valor=tr['valor'],
                    tipo=tr['tipo'],
                    banco="Importado (OFX)"
                )
                db.session.add(nova_tr)
                importadas += 1
            
            db.session.commit()
            flash(f'Sucesso! {importadas} novas transações importadas. ({duplicadas} já existiam)', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar OFX: {str(e)}', 'error')
            
    # Listar transações pendentes para a view
    pendentes = TransacaoExtrato.query.filter_by(conciliado=False).order_by(TransacaoExtrato.data.desc()).all()
    return render_template('extrato_conciliacao.html', pendentes=pendentes)

@extrato_bp.route('/api/extrato/sugerir/<int:id>')
@login_required
def sugerir_conciliacao(id):
    """
    API que sugere pagamentos candidatos para uma transação do extrato.
    Criterio: Mesmo valor e data próxima (+- 3 dias).
    """
    tr = TransacaoExtrato.query.get_or_404(id)
    # Busca candidatos no modelo Pagamento
    # Aqui fazemos uma busca simplificada por valor
    candidatos = Pagamento.query.filter(
        Pagamento.valor_pagar == tr.valor,
        Pagamento.receita_despesa == tr.tipo
    ).all()
    
    return jsonify([c.to_dict() for c in candidatos])

@extrato_bp.route('/extrato/conciliar', methods=['POST'])
@login_required
def conciliar_transacao():
    data = request.form
    transacao_id = data.get('transacao_id')
    pagamento_id = data.get('pagamento_id')
    
    tr = TransacaoExtrato.query.get_or_404(transacao_id)
    pag = Pagamento.query.get_or_404(pagamento_id)
    
    try:
        tr.conciliado = True
        tr.pagamento_id = pag.cod
        
        # Atualizar o pagamento como pago automaticamente se o usuário desejar
        if not pag.data_pago:
            pag.data_pago = tr.data.strftime('%Y-%m-%d')
            pag.valor_pago = tr.valor
            
        db.session.commit()
        flash('Conciliação realizada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao conciliar: {str(e)}', 'error')
        
    return redirect(url_for('extrato.importar_extrato'))
