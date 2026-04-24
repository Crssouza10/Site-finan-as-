from flask_login import login_required
from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
from database import db
from models import Categoria

api_bp = Blueprint('api', __name__)

CONFIG_FILE = 'config_notificacoes.json'

def carregar_config_email():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'email_destino': os.getenv('EMAIL_RECEIVER', ''), 'alertas_ativos': True, 'backup_ativo': True}

def salvar_config_email(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except: return False

@api_bp.route('/api/config/email', methods=['GET'])
@login_required
def get_config_email():
    return jsonify({'sucesso': True, 'config': carregar_config_email()})

@api_bp.route('/api/config/email', methods=['POST'])
@login_required
def set_config_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        if not email or '@' not in email: return jsonify({'sucesso': False, 'erro': 'E-mail inválido'}), 400
        config = {
            'email_destino': email, 'alertas_ativos': data.get('alertas_ativos', True),
            'backup_ativos': data.get('backup_ativos', True), 'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        if salvar_config_email(config): return jsonify({'sucesso': True, 'mensagem': 'Salvo!'})
        return jsonify({'sucesso': False, 'erro': 'Erro ao salvar'}), 500
    except Exception as e: return jsonify({'sucesso': False, 'erro': str(e)}), 500

@api_bp.route('/api/categorias')
@login_required
def api_categorias():
    tipo = request.args.get('tipo')
    query = Categoria.query.order_by(Categoria.nome)
    if tipo in ['R', 'D']: query = query.filter_by(tipo=tipo)
    return jsonify([c.to_dict() for c in query.all()])

@api_bp.route('/api/categorias', methods=['POST'])
@login_required
def api_adicionar_categoria():
    try:
        data = request.get_json() or request.form
        nome = data.get('nome', '').strip().upper()
        if not nome or len(nome) < 3: return jsonify({'erro': 'Nome muito curto'}), 400
        if Categoria.query.filter_by(nome=nome).first(): return jsonify({'erro': 'Já existe'}), 409
        nova = Categoria(nome=nome, tipo=data.get('tipo', 'D'), instituicao=data.get('instituicao'), fonte_paga=data.get('fonte_paga'))
        db.session.add(nova)
        db.session.commit()
        return jsonify({'sucesso': True, 'categoria': nova.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@api_bp.route('/api/categorias/<int:cat_id>', methods=['DELETE'])
@login_required
def api_remover_categoria(cat_id):
    try:
        cat = Categoria.query.get_or_404(cat_id)
        if cat.pagamentos: return jsonify({'erro': 'Categoria em uso'}), 400
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'sucesso': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# ============================================================================
# 🧠 SMARTWALLET AI - LÓGICA ESTATÍSTICA PREDITIVA
# ============================================================================

@api_bp.route('/api/dashboard/ia-projections')
@login_required
def get_ia_projections():
    try:
        from models import Pagamento
        from sqlalchemy import func
        
        # 1. Obter média de gastos/receitas dos últimos 4 meses
        # (Lógica estatística baseada em padrões históricos)
        hoje = datetime.now()
        historico = Pagamento.query.all()
        
        # Agrupar por tipo (R/D)
        receitas_total = sum(float(p.valor_pagar) for p in historico if p.receita_despesa == 'R')
        despesas_total = sum(float(p.valor_pagar) for p in historico if p.receita_despesa == 'D')
        
        # Calcular meses únicos com dados
        meses_unicos = len(set(p.mes_ano for p in historico)) or 1
        
        media_receita = receitas_total / meses_unicos
        media_despesa = despesas_total / meses_unicos
        
        # 2. Identificar "Custos Fixos" (contas recorrentes)
        contas_recorrentes = db.session.query(
            Pagamento.conta, func.count(Pagamento.cod)
        ).group_by(Pagamento.conta).having(func.count(Pagamento.cod) > 1).all()
        
        custo_fixo_estimado = 0
        for nome_conta, qtd in contas_recorrentes:
            exemplo = Pagamento.query.filter_by(conta=nome_conta).first()
            if exemplo and exemplo.receita_despesa == 'D':
                custo_fixo_estimado += float(exemplo.valor_pagar)
        
        # 3. Projeção para os próximos 3 meses
        projecoes = []
        saldo_projetado = media_receita - media_despesa # Saldo líquido mensal médio
        
        for i in range(1, 4):
            mes_idx = (hoje.month + i - 1) % 12 + 1
            ano_idx = hoje.year + (hoje.month + i - 1) // 12
            mes_nome = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][mes_idx-1]
            
            projecoes.append({
                'mes': f"{mes_nome}/{ano_idx}",
                'receita': round(media_receita * (1 + (i*0.01)), 2), # Simula leve crescimento
                'despesa': round(media_despesa, 2),
                'saldo_acumulado': round(saldo_projetado * i, 2)
            })
            
        # 4. Insights Educativos do Coach (Lógica Comportamental)
        insights = []
        poupanca_mensal = media_receita - media_despesa
        
        # Critério 1: Regra 50/30/20 (Educação Financeira)
        if media_receita > 0:
            if custo_fixo_estimado > (media_receita * 0.5):
                insights.append({
                    'tipo': 'danger', 'icon': 'bi-lightning-charge',
                    'texto': 'Seus custos fixos estão acima de 50% da renda. Isso reduz sua margem de manobra para imprevistos.'
                })
            else:
                insights.append({
                    'tipo': 'success', 'icon': 'bi-shield-check',
                    'texto': 'Boa! Seus custos fixos estão equilibrados, permitindo focar em investimentos e lazer.'
                })

        # Critério 2: Poupança Preditiva
        if poupanca_mensal > 0:
            objetivo_6_meses = poupanca_mensal * 6
            insights.append({
                'tipo': 'info', 'icon': 'bi-calendar-check',
                'texto': f'Mantendo este ritmo, você terá R$ {objetivo_6_meses:,.2f} em 6 meses. Já pensou na sua reserva de emergência?'
            })
        else:
            insights.append({
                'tipo': 'danger', 'icon': 'bi-graph-down-arrow',
                'texto': 'O Coach avisa: Você está consumindo sua reserva. Precisamos cortar R$ ' + f'{abs(poupanca_mensal):,.2f}' + ' em gastos variáveis agora.'
            })

        # Critério 3: Dica Comportamental (Nudge)
        if len(contas_recorrentes) > 10:
            insights.append({
                'tipo': 'warning', 'icon': 'bi-credit-card-2-front',
                'texto': 'Identifiquei muitas assinaturas ou pagamentos recorrentes. Revise o que você não usa há mais de 30 dias.'
            })

        return jsonify({
            'sucesso': True,
            'media_mensal': {'receita': media_receita, 'despesa': media_despesa},
            'projecoes': projecoes,
            'insights': insights,
            'custo_fixo_percentual': round((custo_fixo_estimado / media_receita * 100) if media_receita > 0 else 0, 1)
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
# ============================================================================
# 🛡️ RESERVA DE EMERGÊNCIA - GESTÃO DE SEGURANÇA
# ============================================================================

@api_bp.route('/api/reserva', methods=['GET'])
@login_required
def get_reserva():
    try:
        from models import ReservaEmergencia, Pagamento
        reserva = ReservaEmergencia.query.filter_by(user_id=current_user.id).first()
        
        if not reserva:
            reserva = ReservaEmergencia(user_id=current_user.id, objetivo_meses=6, valor_manual=0)
            db.session.add(reserva)
            db.session.commit()
            
        # Cálculo de Cobertura Real
        # 1. Gasto médio mensal (últimos 3 meses)
        despesas_historicas = db.session.query(func.sum(Pagamento.valor_pagar)).filter(
            Pagamento.receita_despesa == 'D'
        ).group_by(Pagamento.mes_ano).order_by(Pagamento.mes_ano.desc()).limit(3).all()
        
        media_gastos = sum(float(d[0]) for d in despesas_historicas) / len(despesas_historicas) if despesas_historicas else 2000
        
        # 2. Saldo atual estimado (Receitas Pagas - Despesas Pagas)
        total_rec = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.receita_despesa == 'R').scalar() or 0
        total_desp = db.session.query(func.sum(Pagamento.valor_pago)).filter(Pagamento.receita_despesa == 'D').scalar() or 0
        saldo_sistema = float(total_rec) - float(total_desp)
        
        # 3. Simulação de Otimização (Cruzamento com Assinaturas)
        # Identifica a assinatura mais cara ou com maior aumento para sugerir economia
        assinaturas_fadiga = db.session.query(Pagamento.conta, func.max(Pagamento.valor_pagar)).filter(
            Pagamento.receita_despesa == 'D'
        ).group_by(Pagamento.conta).having(func.count(Pagamento.cod) >= 3).order_by(func.max(Pagamento.valor_pagar).desc()).first()
        
        otimizacao = None
        if assinaturas_fadiga and meses_cobertura < reserva.objetivo_meses:
            valor_economia = float(assinaturas_fadiga[1])
            nova_poupanca = (total_reserva / (media_gastos - valor_economia)) if (media_gastos - valor_economia) > 0 else meses_cobertura
            dias_antecipados = round((nova_poupanca - meses_cobertura) * 30)
            
            if dias_antecipados > 0:
                otimizacao = {
                    'conta_sugerida': assinaturas_fadiga[0],
                    'valor_economia': valor_economia,
                    'dias_ganhos': dias_antecipados,
                    'mensagem': f"Dica de Ouro: Cancelar '{assinaturas_fadiga[0]}' antecipa sua meta de segurança em aprox. {dias_antecipados} dias."
                }
        
        return jsonify({
            'sucesso': True,
            'config': reserva.to_dict(),
            'analise': {
                'media_gastos': round(media_gastos, 2),
                'saldo_sistema': round(saldo_sistema, 2),
                'total_disponivel': round(total_reserva, 2),
                'meses_cobertura': round(meses_cobertura, 1),
                'percentual_objetivo': round(min((meses_cobertura / reserva.objetivo_meses) * 100, 100), 1) if reserva.objetivo_meses > 0 else 0,
                'otimizacao': otimizacao
            }
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@api_bp.route('/api/reserva', methods=['POST'])
@login_required
def set_reserva():
    try:
        from models import ReservaEmergencia
        data = request.get_json()
        reserva = ReservaEmergencia.query.filter_by(user_id=current_user.id).first()
        
        if not reserva:
            reserva = ReservaEmergencia(user_id=current_user.id)
            db.session.add(reserva)
            
        reserva.objetivo_meses = int(data.get('objetivo_meses', 6))
        reserva.valor_manual = float(data.get('valor_manual', 0))
        
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Meta de reserva atualizada!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ============================================================================
# 🔍 ANÁLISE DE FADIGA DE ASSINATURAS
# ============================================================================

@api_bp.route('/api/analise/assinaturas')
@login_required
def api_analise_assinaturas():
    try:
        from models import Pagamento
        from sqlalchemy import func
        
        # 1. Identificar contas que aparecem em pelo menos 3 meses diferentes
        contas_recorrentes = db.session.query(
            Pagamento.conta, 
            func.count(Pagamento.cod).label('total_meses'),
            func.avg(Pagamento.valor_pagar).label('media_valor')
        ).filter(Pagamento.receita_despesa == 'D').group_by(Pagamento.conta).having(func.count(Pagamento.cod) >= 3).all()
        
        analise = []
        for c in contas_recorrentes:
            # Buscar histórico dessa conta específica
            historico = Pagamento.query.filter_by(conta=c.conta).order_by(Pagamento.mes_ano.desc()).limit(6).all()
            
            # Verificar se houve aumento recente
            valor_mais_recente = float(historico[0].valor_pagar)
            valor_anterior = float(historico[1].valor_pagar) if len(historico) > 1 else valor_mais_recente
            
            variacao = ((valor_mais_recente - valor_anterior) / valor_anterior * 100) if valor_anterior > 0 else 0
            custo_anual = valor_mais_recente * 12
            
            analise.append({
                'conta': c.conta,
                'media_mensal': round(float(c.media_valor), 2),
                'valor_recente': valor_mais_recente,
                'variacao_percentual': round(variacao, 1),
                'custo_anual_projetado': round(custo_anual, 2),
                'alerta': variacao > 0,
                'meses_rastreados': c.total_meses
            })
            
        analise.sort(key=lambda x: x['custo_anual_projetado'], reverse=True)
        
        return jsonify({
            'sucesso': True,
            'assinaturas': analise,
            'total_anual_assinaturas': round(sum(a['custo_anual_projetado'] for a in analise), 2)
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
