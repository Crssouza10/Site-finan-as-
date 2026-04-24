from flask_login import login_required
from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from database import db
from models import Categoria, Pagamento, MetaOrcamento

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/orcamento')
@login_required
def orcamento():
    """Página de controle de orçamento com comparativo Meta vs Realizado"""
    mes_ano = request.args.get('mes_ano', datetime.now().strftime('%m/%Y'))
    
    # Busca todas as categorias de despesa
    categorias = Categoria.query.filter_by(tipo='D').order_by(Categoria.nome).all()
    
    # Busca metas para o período
    metas = {m.categoria_id: m.valor_meta for m in MetaOrcamento.query.filter_by(mes_ano=mes_ano).all()}
    
    # Busca realizado para o período
    realizado_query = db.session.query(
        Pagamento.categoria_id,
        func.sum(Pagamento.valor_pagar).label('total')
    ).filter(
        Pagamento.mes_ano == mes_ano,
        Pagamento.receita_despesa == 'D'
    ).group_by(Pagamento.categoria_id).all()
    
    realizado = {r.categoria_id: float(r.total or 0) for r in realizado_query}
    
    dados_orcamento = []
    for cat in categorias:
        meta_val = metas.get(cat.id, 0.0)
        real_val = realizado.get(cat.id, 0.0)
        desvio = meta_val - real_val
        percentual = (real_val / meta_val * 100) if meta_val > 0 else 0
        
        dados_orcamento.append({
            'categoria_id': cat.id,
            'nome': cat.nome,
            'meta': meta_val,
            'realizado': real_val,
            'desvio': desvio,
            'percentual': min(percentual, 100),
            'percentual_real': percentual,
            'status': 'danger' if percentual > 100 else ('warning' if percentual > 80 else 'success')
        })
        
    return render_template('orcamento.html', 
        dados=dados_orcamento, 
        mes_ano_selecionado=mes_ano,
        total_meta=sum(metas.values()),
        total_realizado=sum(realizado.values())
    )

@dashboard_bp.route('/api/orcamento/save', methods=['POST'])
@login_required
def api_save_orcamento():
    """Salva ou atualiza uma meta de orçamento"""
    try:
        data = request.get_json()
        cat_id = data.get('categoria_id')
        mes_ano = data.get('mes_ano')
        valor = float(data.get('valor', 0))
        
        meta = MetaOrcamento.query.filter_by(categoria_id=cat_id, mes_ano=mes_ano).first()
        if meta:
            meta.valor_meta = valor
        else:
            meta = MetaOrcamento(categoria_id=cat_id, mes_ano=mes_ano, valor_meta=valor)
            db.session.add(meta)
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/data')
@login_required
def api_dashboard_data():
    """Retorna dados para os gráficos do dashboard principal"""
    try:
        # 1. Despesas por Categoria (Top 10)
        despesas_cat = db.session.query(
            Categoria.nome,
            func.sum(Pagamento.valor_pagar).label('total')
        ).join(Pagamento).filter(
            Pagamento.receita_despesa == 'D'
        ).group_by(Categoria.nome).order_by(func.sum(Pagamento.valor_pagar).desc()).limit(10).all()
        
        # 2. Evolução Mensal (últimos 12 meses)
        hoje = datetime.now()
        meses, despesas_vals, receitas_vals = [], [], []
        
        for i in range(11, -1, -1):
            ref = hoje - timedelta(days=i*30)
            mes_ano = ref.strftime('%m/%Y')
            meses.append(mes_ano)
            
            desp = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
                Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'D'
            ).scalar() or 0
            rec = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
                Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'R'
            ).scalar() or 0
            
            despesas_vals.append(float(desp))
            receitas_vals.append(float(rec))
        
        # 3. Status Pagamentos
        pago = db.session.query(func.sum(Pagamento.valor_pago)).filter(
            Pagamento.valor_pago > 0
        ).scalar() or 0
        pendente = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
            (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)),
            Pagamento.receita_despesa == 'D'
        ).scalar() or 0
        
        return jsonify({
            'despesas_categoria': {
                'labels': [c.nome for c in despesas_cat],
                'values': [float(c.total or 0) for c in despesas_cat]
            },
            'evolucao_mensal': {
                'labels': meses,
                'despesas': despesas_vals,
                'receitas': receitas_vals
            },
            'status_pagamentos': {
                'pago': float(pago),
                'pendente': float(pendente)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/ranking_mensal')
@login_required
def api_dashboard_ranking():
    """Ranking de despesas por conta para um mês"""
    mes_ano = request.args.get('mes_ano', '').strip()
    if not mes_ano:
        return jsonify({'error': 'Parâmetro mes_ano obrigatório'}), 400
    
    try:
        resultados = db.session.query(
            Pagamento.conta,
            Categoria.nome.label('categoria'),
            func.sum(Pagamento.valor_pagar).label('total')
        ).join(Categoria).filter(
            Pagamento.mes_ano == mes_ano,
            Pagamento.receita_despesa == 'D'
        ).group_by(Pagamento.conta, Categoria.nome).order_by(
            func.sum(Pagamento.valor_pagar).desc()
        ).limit(10).all()
        
        return jsonify({
            'mes_ano': mes_ano,
            'ranking': [{
                'conta': r.conta,
                'categoria': r.categoria,
                'valor': float(r.total or 0)
            } for r in resultados]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/dashboard/tendencia_acumulada')
@login_required
def api_tendencia_acumulada():
    """Retorna dados acumulados mês a mês, respeitando filtros"""
    ano = request.args.get('ano', datetime.now().year, type=int)
    categoria_filtro = request.args.get('categoria', '').strip()
    conta_filtro = request.args.get('conta', '').strip()
    
    query_base = Pagamento.query.filter(Pagamento.valor_pago > 0)
    
    if categoria_filtro:
        query_base = query_base.join(Categoria).filter(func.upper(Categoria.nome) == categoria_filtro.upper())
    
    if conta_filtro:
        query_base = query_base.filter(Pagamento.conta.ilike(f"%{conta_filtro}%"))
    
    def calcular_acumulado(ano_ref):
        acumulado = []
        total = 0
        for mes in range(1, 13):
            mes_str = f"{mes:02d}/{ano_ref}"
            resultado = query_base.filter(Pagamento.mes_ano == mes_str).with_entities(func.sum(Pagamento.valor_pago).label('total')).first()
            total += float(resultado.total or 0)
            acumulado.append(total)
        return acumulado
    
    return jsonify({
        'ano': ano,
        'acumulado_total_vig': calcular_acumulado(ano),
        'acumulado_total_ant': calcular_acumulado(ano - 1),
        'filtros_aplicados': {'categoria': categoria_filtro or 'Todas', 'conta': conta_filtro or 'Todas'}
    })

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard profissional com análise de evolução por conta"""
    ano_selecionado = request.args.get('ano', datetime.now().year, type=int)
    categoria_filtro = request.args.get('categoria', '').strip()
    conta_filtro = request.args.get('conta', '').strip()
    tipo_filtro = request.args.get('tipo', '').strip()
    
    ano_vig = ano_selecionado
    ano_ant = ano_vig - 1
    ano_fut = ano_vig + 1
    
    # --- MOTOR DE INSIGHTS INTELIGENTES (AI ENGINE) ---
    insights = []
    mes_atual = datetime.now().strftime('%m/%Y')
    
    # 1. Insight de Saúde Mensal (Comparativo mês anterior)
    mes_ant_ref = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%m/%Y')
    gastos_mes_ant = db.session.query(func.sum(Pagamento.valor_pago)).filter(
        Pagamento.mes_ano == mes_ant_ref, Pagamento.receita_despesa == 'D'
    ).scalar() or 0
    gastos_mes_atual = db.session.query(func.sum(Pagamento.valor_pago)).filter(
        Pagamento.mes_ano == mes_atual, Pagamento.receita_despesa == 'D'
    ).scalar() or 0
    
    if gastos_mes_atual > gastos_mes_ant and gastos_mes_ant > 0:
        diff = ((float(gastos_mes_atual) - float(gastos_mes_ant)) / float(gastos_mes_ant)) * 100
        if diff > 10:
            insights.append({
                'tipo': 'warning', 'icon': 'bi-graph-up-arrow',
                'titulo': 'Alerta de Consumo',
                'texto': f'Seus gastos este mês estão {diff:.1f}% acima do mês passado. Atenção ao orçamento!'
            })
    
    # 2. Insight de Metas de Orçamento
    metas_estouradas = []
    todas_metas = MetaOrcamento.query.filter_by(mes_ano=mes_atual).all()
    for m in todas_metas:
        real_cat = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
            Pagamento.categoria_id == m.categoria_id, Pagamento.mes_ano == mes_atual
        ).scalar() or 0
        if float(real_cat) > float(m.valor_meta):
            metas_estouradas.append(m.categoria.nome)
            
    if metas_estouradas:
        insights.append({
            'tipo': 'danger', 'icon': 'bi-exclamation-triangle',
            'titulo': 'Orçamento Estourado',
            'texto': f'As categorias {", ".join(metas_estouradas)} ultrapassaram o limite planejado.'
        })

    # 3. Insight Positivo de Economia
    if saldo_liquido > (receitas_vig * 0.2) and receitas_vig > 0:
        insights.append({
            'tipo': 'success', 'icon': 'bi-piggy-bank',
            'titulo': 'Excelente Gestão!',
            'texto': 'Você poupou mais de 20% da sua receita este ano. Ótimo momento para investir!'
        })
        
    if not insights:
        insights.append({
            'tipo': 'info', 'icon': 'bi-robot',
            'titulo': 'Tudo sob controle',
            'texto': 'Seu comportamento financeiro está estável. Continue acompanhando suas metas.'
        })
    # --------------------------------------------------

    # Receitas (sem filtro de conta)
    query_receitas = Pagamento.query.filter(
        Pagamento.mes_ano.ilike(f"%/{ano_vig}"),
        Pagamento.receita_despesa == 'R',
        Pagamento.valor_pago > 0
    )
    receitas_vig = sum(float(p.valor_pago or 0) for p in query_receitas.all())
    
    # Despesas (com filtros)
    query_despesas = Pagamento.query.filter(
        Pagamento.mes_ano.ilike(f"%/{ano_vig}"),
        Pagamento.receita_despesa == 'D',
        Pagamento.valor_pago > 0
    )
    if categoria_filtro:
        query_despesas = query_despesas.join(Categoria).filter(func.upper(Categoria.nome) == categoria_filtro.upper())
    if conta_filtro:
        query_despesas = query_despesas.filter(Pagamento.conta.ilike(f"%{conta_filtro}%"))
    
    despesas_vig = sum(float(p.valor_pago or 0) for p in query_despesas.all())
    saldo_liquido = receitas_vig - despesas_vig
    total_vig = receitas_vig + despesas_vig
    
    pct_receitas = (receitas_vig / total_vig * 100) if total_vig > 0 else 0
    pct_despesas = (despesas_vig / total_vig * 100) if total_vig > 0 else 0
    
    # Categorias
    query_cat = db.session.query(
        Categoria.nome, func.sum(Pagamento.valor_pago).label('total'), Pagamento.receita_despesa
    ).join(Pagamento).filter(
        Pagamento.mes_ano.ilike(f"%/{ano_vig}"), Pagamento.valor_pago > 0
    )
    if conta_filtro: query_cat = query_cat.filter(Pagamento.conta.ilike(f"%{conta_filtro}%"))
    if categoria_filtro: query_cat = query_cat.filter(func.upper(Categoria.nome) == categoria_filtro.upper())
    
    resultados_cat = query_cat.group_by(Categoria.nome, Pagamento.receita_despesa).order_by(func.sum(Pagamento.valor_pago).desc()).limit(10).all()
    
    total_receitas_cat = sum(float(r.total or 0) for r in resultados_cat if r.receita_despesa == 'R')
    total_despesas_cat = sum(float(r.total or 0) for r in resultados_cat if r.receita_despesa == 'D')
    
    dados_categorias = []
    for r in resultados_cat:
        valor = float(r.total or 0)
        total_tipo = total_receitas_cat if r.receita_despesa == 'R' else total_despesas_cat
        pct = (valor / total_tipo * 100) if total_tipo > 0 else 0
        dados_categorias.append({
            'nome': r.nome or 'Sem Categoria', 'valor': valor, 'percentual': pct,
            'tipo': 'Receita' if r.receita_despesa == 'R' else 'Despesa', 'receita_despesa': r.receita_despesa
        })
    
    # Comparativos mensais
    def get_monthly_data(ano, conta_filter=None, tipo_filter=None):
        query = db.session.query(
            extract('month', func.to_date(Pagamento.data_venc, 'DD/MM/YYYY')).label('mes'),
            func.sum(Pagamento.valor_pagar).label('total')
        ).filter(Pagamento.mes_ano.ilike(f"%/{ano}"))
        if conta_filter: query = query.filter(Pagamento.conta.ilike(f"%{conta_filter}%"))
        if tipo_filter == 'R': query = query.filter(Pagamento.receita_despesa == 'R')
        elif tipo_filter == 'D': query = query.filter(Pagamento.receita_despesa == 'D')
        
        results = query.group_by('mes').all()
        dados = [0.0] * 12
        for r in results:
            if r.mes and 1 <= int(r.mes) <= 12:
                dados[int(r.mes) - 1] = float(r.total or 0)
        return dados
    
    ant = get_monthly_data(ano_ant, conta_filtro or None, tipo_filtro)
    vig = get_monthly_data(ano_vig, conta_filtro or None, tipo_filtro)
    fut = get_monthly_data(ano_fut, conta_filtro or None, tipo_filtro)
    
    variacao_vig = ((sum(vig) - sum(ant)) / sum(ant) * 100) if sum(ant) > 0 else (100.0 if sum(vig) > 0 else 0.0)
    
    # Top 10 Contas
    query_top = db.session.query(
        Pagamento.conta, Categoria.nome.label('categoria'), func.sum(Pagamento.valor_pagar).label('total')
    ).join(Categoria).filter(Pagamento.mes_ano.ilike(f"%/{ano_vig}"))
    if conta_filtro: query_top = query_top.filter(Pagamento.conta.ilike(f"%{conta_filtro}%"))
    if tipo_filtro: query_top = query_top.filter(Pagamento.receita_despesa == tipo_filtro)
    if categoria_filtro: query_top = query_top.filter(Categoria.nome == categoria_filtro)
    
    resultados_top = query_top.group_by(Pagamento.conta, Categoria.nome).order_by(func.sum(Pagamento.valor_pagar).desc()).limit(10).all()
    total_geral_top = sum(float(r.total or 0) for r in resultados_top)
    
    top_contas = [{
        'conta': r.conta or 'Sem Conta', 'categoria': r.categoria or 'Geral', 'valor': float(r.total or 0),
        'pct': (float(r.total or 0) / total_geral_top * 100) if total_geral_top > 0 else 0
    } for r in resultados_top]
    
    return render_template('dashboard.html',
        ano_selecionado=ano_selecionado, ano_vig=ano_vig, ano_ant=ano_ant, ano_fut=ano_fut,
        ant=ant, vig=vig, fut=fut, conta_filtro=conta_filtro, dados_categorias=dados_categorias,
        total_vig=total_vig, variacao_vig=variacao_vig, receitas_vig=receitas_vig, despesas_vig=despesas_vig,
        saldo_liquido=saldo_liquido, pct_receitas=pct_receitas, pct_despesas=pct_despesas,
        top_contas=top_contas, categorias=Categoria.query.order_by(Categoria.nome).all(),
        categoria_selecionada=categoria_filtro, tipo_selecionado=tipo_filtro,
        data_atualizacao=datetime.now().strftime('%d/%m/%Y %H:%M'),
        insights=insights
    )

@dashboard_bp.route('/dashboard_contas')
@login_required
def dashboard_contas():
    """Dashboard analisado por conta"""
    resultados = db.session.query(
        Pagamento.conta, func.sum(Pagamento.valor_pagar).label('total'), func.count(Pagamento.cod).label('quantidade')
    ).filter(Pagamento.receita_despesa == 'D').group_by(Pagamento.conta).order_by(func.sum(Pagamento.valor_pagar).desc()).limit(10).all()
    return render_template('dashboard_contas.html', dados=[{'conta': r.conta, 'total': float(r.total), 'quantidade': r.quantidade} for r in resultados])

@dashboard_bp.route('/dashboard_categorias')
@login_required
def dashboard_categorias():
    """Dashboard analisado por categoria"""
    resultados = db.session.query(
        Categoria.nome, Categoria.tipo, func.sum(Pagamento.valor_pagar).label('total'), func.count(Pagamento.id).label('quantidade')
    ).join(Pagamento).group_by(Categoria.id, Categoria.nome, Categoria.tipo).all()
    return render_template('dashboard_categorias.html', dados=[{
        'categoria': r.nome, 'tipo': r.tipo, 'total': float(r.total or 0), 'quantidade': r.quantidade
    } for r in resultados])

@dashboard_bp.route('/api/dashboard/projecoes')
@login_required
def api_projecoes_futuras():
    """Retorna projeção de fluxo de caixa para os próximos 6 meses"""
    try:
        hoje = datetime.now()
        meses_lista = []
        saldos_projetados = []
        
        # 1. Obter saldo atual (Receitas pagas - Despesas pagas de sempre)
        total_receitas = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.receita_despesa == 'R').scalar() or 0
        total_despesas = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.receita_despesa == 'D').scalar() or 0
        saldo_inicial = float(total_receitas) - float(total_despesas)
        
        # 2. Calcular média de gastos mensais (últimos 3 meses) para "preencher lacunas"
        media_gastos = db.session.query(func.avg(func.sum(Pagamento.valor_pagar))).from_statement(
            db.text("SELECT SUM(valor_pagar) FROM pagamentos WHERE receita_despesa = 'D' GROUP BY mes_ano LIMIT 3")
        ).scalar() or 2000 # fallback se não houver dados
        
        saldo_acumulado = saldo_inicial
        
        for i in range(0, 7): # Mês atual + 6 meses
            ref = hoje + timedelta(days=i*30)
            mes_ano = ref.strftime('%m/%Y')
            meses_lista.append(ref.strftime('%b/%y'))
            
            # Busca o que já está lançado (contas fixas/parcelas)
            rec_lancada = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
                Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'R'
            ).scalar() or 0
            desp_lancada = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
                Pagamento.mes_ano == mes_ano, Pagamento.receita_despesa == 'D'
            ).scalar() or 0
            
            # Se a despesa lançada for muito baixa, usamos a média (predição)
            desp_final = max(float(desp_lancada), float(media_gastos) * 0.8) # 80% da média como base de segurança
            
            saldo_mes = float(rec_lancada) - desp_final
            saldo_acumulado += saldo_mes
            saldos_projetados.append(round(saldo_acumulado, 2))
            
        return jsonify({
            'labels': meses_lista,
            'valores': saldos_projetados,
            'saldo_inicial': round(saldo_inicial, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
