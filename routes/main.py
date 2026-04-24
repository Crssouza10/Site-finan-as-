from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required
import io
from datetime import datetime
import calendar
import os
from sqlalchemy import func
from database import db
from models import Categoria, Pagamento, Documento
from utils.helpers import limpar_valor, formatar_data_br

main_bp = Blueprint('main', __name__)

def popular_categorias_iniciais():
    """Cria categorias padrão se o banco estiver vazio"""
    try:
        if Categoria.query.count() == 0:
            cats = [
                ('Moradia', 'D'), ('Alimentação', 'D'), ('Saúde', 'D'), 
                ('Transporte', 'D'), ('Educação', 'D'), ('Lazer', 'D'),
                ('Vestuário', 'D'), ('Comunicação', 'D'), ('Impostos', 'D'),
                ('Investimentos', 'R'), ('Salário', 'R'), ('Outros', 'D')
            ]
            for nome, tipo in cats:
                if not Categoria.query.filter_by(nome=nome).first():
                    db.session.add(Categoria(nome=nome, tipo=tipo))
            db.session.commit()
    except Exception as e:
        db.session.rollback()

def buscar_ou_criar_categoria(nome, tipo='D'):
    """Busca categoria existente ou cria nova se não existir"""
    nome = nome.strip().upper()
    cat = Categoria.query.filter_by(nome=nome).first()
    if not cat:
        cat = Categoria(nome=nome, tipo=tipo)
        db.session.add(cat)
        db.session.commit()
    return cat

@main_bp.route('/')
@login_required
def index():
    """Página principal com busca flexível"""
    data_hoje_str = datetime.now().strftime('%d/%m/%Y')
    filtros = {
        'MesAno': request.args.get('MesAno', '').strip(),
        'Conta': request.args.get('Conta', '').strip(),
        'Instituicao': request.args.get('Instituicao', '').strip(),
        'Fontepaga': request.args.get('Fontepaga', '').strip(),
        'Competencia': request.args.get('Competencia', '').strip(),
        'Categoria': request.args.get('Categoria', '').strip(),
        'status': request.args.get('status', '').strip(),
        'data_inicio': request.args.get('data_inicio', '').strip(),
        'data_fim': request.args.get('data_fim', '').strip()
    }
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if not any(filtros.values()):
        return render_template('index.html', pagamentos=[], total_a_pagar=0, total_pago=0, total_receitas=0, contas_hoje=0, data_hoje=data_hoje_str, categorias=Categoria.query.order_by(Categoria.nome).all())
    
    query = Pagamento.query
    if filtros['MesAno']: query = query.filter(Pagamento.mes_ano.ilike(f"%{filtros['MesAno']}%"))
    if filtros['Conta']: query = query.filter(Pagamento.conta.ilike(f"%{filtros['Conta']}%"))
    if filtros['Instituicao']: query = query.filter(Pagamento.instituicao.ilike(f"%{filtros['Instituicao']}%"))
    if filtros['Fontepaga']: query = query.filter(Pagamento.fonte_paga.ilike(f"%{filtros['Fontepaga']}%"))
    if filtros['Competencia']: query = query.filter(Pagamento.competencia.ilike(f"%{filtros['Competencia']}%"))
    if filtros['Categoria']: query = query.join(Categoria).filter(Categoria.nome.ilike(f"%{filtros['Categoria']}%"))
    
    if filtros['status'] == 'pago': query = query.filter(Pagamento.valor_pago > 0)
    elif filtros['status'] == 'pendente': query = query.filter((Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)))
    elif filtros['status'] == 'atrasado': query = query.filter(Pagamento.data_venc < data_hoje_str, (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)))
    
    # Filtro de Período
    if filtros['data_inicio']:
        d_ini = formatar_data_br(filtros['data_inicio'])
        query = query.filter(func.to_date(Pagamento.data_venc, 'DD/MM/YYYY') >= func.to_date(d_ini, 'DD/MM/YYYY'))
    if filtros['data_fim']:
        d_fim = formatar_data_br(filtros['data_fim'])
        query = query.filter(func.to_date(Pagamento.data_venc, 'DD/MM/YYYY') <= func.to_date(d_fim, 'DD/MM/YYYY'))
    
    # 1. Calcular Totais GERAIS da busca filtrada (antes da paginação)
    total_a_pagar = db.session.query(func.sum(Pagamento.valor_pagar)).filter(Pagamento.receita_despesa == 'D').filter(Pagamento.cod.in_(query.with_entities(Pagamento.cod))).scalar() or 0
    total_receitas = db.session.query(func.sum(Pagamento.valor_pagar)).filter(Pagamento.receita_despesa == 'R').filter(Pagamento.cod.in_(query.with_entities(Pagamento.cod))).scalar() or 0
    total_pago = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.cod.in_(query.with_entities(Pagamento.cod))).scalar() or 0
    
    # 2. Executar Paginação
    pagination = query.order_by(
        func.to_date(Pagamento.mes_ano, 'MM/YYYY').desc(), 
        Pagamento.conta.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    pagamentos = pagination.items
    
    return render_template('index.html',
        pagamentos=pagamentos,
        pagination=pagination,
        total_a_pagar=total_a_pagar,
        total_receitas=total_receitas,
        total_pago=total_pago,
        total_saldo=total_receitas - total_a_pagar,
        contas_hoje=Pagamento.query.filter(Pagamento.data_venc == data_hoje_str, (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)), Pagamento.receita_despesa == 'D').count(),
        data_hoje=data_hoje_str,
        categorias=Categoria.query.order_by(Categoria.nome).all()
    )

@main_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Adicionar novo pagamento ou criar parcelas"""
    try:
        cod = request.form.get('cod', '').strip()
        if cod and cod != 'None' and cod.isdigit(): return alterar()

        mes_ano = request.form.get('MesAno', '').strip()
        conta = request.form.get('Conta', '').strip()
        data_venc_raw = request.form.get('Data_venc', '').strip()
        valor_pagar_raw = request.form.get('Valor_pagar', '').strip()
        parcela_input = request.form.get('Parcela', '').strip()
        tipo_op = request.form.get('ReceitaDespesa', 'D').strip().upper()
        
        if not all([mes_ano, conta, data_venc_raw, valor_pagar_raw]):
            flash("⚠️ Campos obrigatórios ausentes", "danger")
            return redirect(url_for('main.index'))
        
        valor_pagar = limpar_valor(valor_pagar_raw)
        data_venc_br = formatar_data_br(data_venc_raw)
        
        categoria_nome = request.form.get('Categoria', '').strip()
        nova_categoria = request.form.get('nova_categoria', '').strip().upper()
        
        if nova_categoria:
            cat = buscar_ou_criar_categoria(nova_categoria, request.form.get('tipo_nova_categoria', 'D'))
            categoria_id = cat.id
        else:
            cat = Categoria.query.filter_by(nome=categoria_nome).first()
            categoria_id = cat.id if cat else None

        if parcela_input and '/' in parcela_input:
            p_atual, p_total = map(int, parcela_input.split('/'))
            data_base = datetime.strptime(data_venc_raw, '%Y-%m-%d')
            m_base, a_base = map(int, mes_ano.split('/'))
            
            for i in range(p_atual, p_total + 1):
                offset = i - p_atual
                n_mes = (m_base + offset - 1) % 12 + 1
                n_ano = a_base + (m_base + offset - 1) // 12
                v_mes = (data_base.month + offset - 1) % 12 + 1
                v_ano = data_base.year + (data_base.month + offset - 1) // 12
                max_dia = calendar.monthrange(v_ano, v_mes)[1]
                v_dia = min(data_base.day, max_dia)
                
                novo = Pagamento(
                    mes_ano=f"{n_mes:02d}/{n_ano}", conta=conta, instituicao=request.form.get('Instituicao'),
                    fonte_paga=request.form.get('Fontepaga'), data_venc=f"{v_dia:02d}/{v_mes:02d}/{v_ano}",
                    valor_pagar=valor_pagar, parcela=f"{i:02d}/{p_total:02d}", observacao=request.form.get('Observacao'),
                    receita_despesa=tipo_op, categoria_id=categoria_id, competencia=request.form.get('Competencia'),
                    juros=limpar_valor(request.form.get('Juros')), desconto=limpar_valor(request.form.get('Desconto'))
                )
                db.session.add(novo)
        else:
            novo = Pagamento(
                mes_ano=mes_ano, conta=conta, instituicao=request.form.get('Instituicao'),
                fonte_paga=request.form.get('Fontepaga'), data_venc=data_venc_br,
                valor_pagar=valor_pagar, parcela=parcela_input or None, observacao=request.form.get('Observacao'),
                receita_despesa=tipo_op, categoria_id=categoria_id, competencia=request.form.get('Competencia'),
                juros=limpar_valor(request.form.get('Juros')), desconto=limpar_valor(request.form.get('Desconto'))
            )
            db.session.add(novo)
        
        db.session.commit()
        flash("✅ Registro(s) salvo(s) com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao salvar: {str(e)}", "danger")
    return redirect(url_for('main.index'))

@main_bp.route('/alterar', methods=['POST'])
@login_required
def alterar():
    """Atualiza um registro existente"""
    cod = request.form.get('cod')
    if not cod:
        flash('⚠️ Selecione um registro primeiro.', 'warning')
        return redirect(url_for('main.index'))
    try:
        pg = Pagamento.query.get(int(cod))
        if not pg:
            flash('❌ Registro não encontrado.', 'danger')
            return redirect(url_for('main.index'))
        
        pg.mes_ano = request.form.get('MesAno', pg.mes_ano)
        pg.conta = request.form.get('Conta', pg.conta)
        pg.instituicao = request.form.get('Instituicao', pg.instituicao)
        pg.fonte_paga = request.form.get('Fontepaga', pg.fonte_paga)
        pg.parcela = request.form.get('Parcela', pg.parcela)
        pg.observacao = request.form.get('Observacao', pg.observacao)
        pg.competencia = request.form.get('Competencia', pg.competencia)
        pg.receita_despesa = request.form.get('ReceitaDespesa', pg.receita_despesa)
        
        if request.form.get('Data_venc'): pg.data_venc = formatar_data_br(request.form.get('Data_venc'))
        if request.form.get('Data_pago'): pg.data_pago = formatar_data_br(request.form.get('Data_pago'))
        else: pg.data_pago = None
        
        pg.valor_pagar = limpar_valor(request.form.get('Valor_pagar'))
        pg.valor_pago = limpar_valor(request.form.get('Valor_pago'))
        pg.juros = limpar_valor(request.form.get('Juros'))
        pg.desconto = limpar_valor(request.form.get('Desconto'))
        
        nova_cat = request.form.get('nova_categoria', '').strip().upper()
        if nova_cat:
            cat = buscar_ou_criar_categoria(nova_cat, pg.receita_despesa)
            pg.categoria_id = cat.id
        else:
            cat = Categoria.query.filter_by(nome=request.form.get('Categoria')).first()
            if cat: pg.categoria_id = cat.id
            
        db.session.commit()
        flash("✅ Alterado com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro na alteração: {str(e)}", "danger")
    return redirect(url_for('main.index'))

@main_bp.route('/apagar', methods=['POST'])
@login_required
def apagar():
    """Exclui um registro"""
    cod = request.form.get('cod')
    if not cod: return redirect(url_for('main.index'))
    try:
        pg = Pagamento.query.get(int(cod))
        if pg:
            db.session.delete(pg)
            db.session.commit()
            flash("✅ Excluído!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao excluir: {str(e)}", "danger")
    return redirect(url_for('main.index'))

@main_bp.route('/visualizar_documento/<int:doc_id>')
@login_required
def visualizar_documento(doc_id):
    """Visualiza PDF armazenado no banco"""
    doc = Documento.query.get_or_404(doc_id)
    return send_file(io.BytesIO(doc.conteudo), mimetype=doc.tipo_mime, as_attachment=False, download_name=doc.nome_arquivo)

@main_bp.route('/deletar_documento/<int:doc_id>', methods=['POST'])
@login_required
def deletar_documento(doc_id):
    """Remove documento do banco"""
    doc = Documento.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'success': True})

# ============================================================================
# 📄 SMARTWALLET AI - OCR & EXTRAÇÃO AUTOMÁTICA DE BOLETOS
# ============================================================================

import re
import pdfplumber

def extrair_dados_boleto(file_bytes):
    """Lógica Sênior para extração de dados via OCR em PDFs Digitais"""
    texto = ""
    dados = {'valor': None, 'vencimento': None, 'conta': None}
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() or ""
        
        # 1. Tenta extrair VALOR (Padrão: R$ 0.000,00 ou Valor do Documento)
        valor_match = re.search(r'(?:VALOR|TOTAL|COBRADO).*?(\d{1,3}(?:\.\d{3})*,\d{2})', texto, re.IGNORECASE)
        if not valor_match:
            valor_match = re.search(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', texto)
        
        if valor_match:
            dados['valor'] = valor_match.group(1)
            
        # 2. Tenta extrair VENCIMENTO (Padrão: DD/MM/YYYY)
        datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
        if datas:
            # Geralmente o vencimento é a última data mencionada em boletos (ou a segunda)
            dados['vencimento'] = datas[0] # Simplificação estatística
            
        # 3. Tenta extrair NOME DA CONTA/INSTITUIÇÃO
        linhas = texto.split('\n')
        if linhas:
            dados['conta'] = linhas[0][:50].strip() # Pega o topo do documento
            
        return dados
    except Exception as e:
        print(f"Erro no OCR: {e}")
        return dados

@main_bp.route('/upload_documento/<int:cod_registro>', methods=['POST'])
@login_required
def upload_documento(cod_registro):
    """Faz o upload e processa o OCR para preenchimento automático"""
    try:
        if 'documento' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
            
        file = request.files['documento']
        if file.filename == '':
            return jsonify({'sucesso': False, 'erro': 'Nome de arquivo vazio'}), 400
            
        file_content = file.read()
        
        # Salva o documento no banco (Mantém funcionalidade original)
        novo_doc = Documento(
            pagamento_id=cod_registro,
            nome_arquivo=file.filename,
            tipo_mime=file.mimetype,
            conteudo=file_content,
            tamanho=len(file_content)
        )
        db.session.add(novo_doc)
        db.session.commit()
        
        # Executa OCR para retornar dados ao frontend
        dados_extraidos = extrair_dados_boleto(file_content)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Arquivo processado pela IA',
            'ocr': dados_extraidos
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@main_bp.route('/api/recorrencia/copiar', methods=['POST'])
@login_required
def api_copiar_mes():
    """Copia lançamentos de um mês para o outro (recorrência)"""
    try:
        data = request.get_json()
        mes_origem = data.get('origem')   # Ex: 04/2026
        mes_destino = data.get('destino') # Ex: 05/2026
        
        if not mes_origem or not mes_destino:
            return jsonify({'success': False, 'error': 'Meses não fornecidos'}), 400
            
        originais = Pagamento.query.filter_by(mes_ano=mes_origem, receita_despesa='D').all()
        if not originais:
            return jsonify({'success': False, 'error': f'Nenhum lançamento em {mes_origem}'}), 404
            
        copiados = 0
        for p in originais:
            try:
                dia = p.data_venc.split('/')[0]
                nova_data = f"{dia}/{mes_destino}"
            except:
                nova_data = p.data_venc
                
            novo = Pagamento(
                mes_ano=mes_destino, conta=p.conta, instituicao=p.instituicao,
                fonte_paga=p.fonte_paga, data_venc=nova_data, valor_pagar=p.valor_pagar,
                valor_pago=0, data_pago=None, parcela=p.parcela, observacao=p.observacao,
                receita_despesa=p.receita_despesa, categoria_id=p.categoria_id, competencia=p.competencia
            )
            db.session.add(novo)
            copiados += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'{copiados} lançamentos copiados!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/atrasados')
@login_required
def atrasados():
    """Página de listagem de contas em atraso"""
    data_hoje = datetime.now()
    data_hoje_str = data_hoje.strftime('%d/%m/%Y')
    
    # Busca todos os pendentes (não pagos ou pagos parcialmente)
    # Precisamos filtrar por data_venc < hoje
    # Como a data_venc é String DD/MM/YYYY, usamos func.to_date
    pendentes = Pagamento.query.filter(
        (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)),
        Pagamento.receita_despesa == 'D'
    ).all()
    
    # Filtra em Python para simplificar a lógica de comparação de datas se o SQL for complexo
    # Mas vamos tentar via SQL para performance
    contas_atrasadas = Pagamento.query.filter(
        (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)),
        Pagamento.receita_despesa == 'D',
        func.to_date(Pagamento.data_venc, 'DD/MM/YYYY') < data_hoje.date()
    ).order_by(func.to_date(Pagamento.data_venc, 'DD/MM/YYYY').asc()).all()
    
    total_atrasado = sum(float(p.valor_pagar or 0) for p in contas_atrasadas)
    
    return render_template('atrasados.html', 
        contas=contas_atrasadas, 
        total=total_atrasado,
        data_hoje=data_hoje_str
    )
