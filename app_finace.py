# ============================================================================
# 🚀 APLICAÇÃO FLASK - GESTÃO FINANCEIRA COM LANDING PAGE + AUTH
# ============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from dotenv import load_dotenv
from pathlib import Path
import os, json, io, calendar, csv, zipfile, tempfile, shutil
from datetime import datetime, timedelta, timezone  
# Carrega variáveis de ambiente
load_dotenv()

# ============================================================================
# INICIALIZAÇÃO DO FLASK
# ============================================================================
app = Flask(__name__)

# Configurações de segurança e banco
app.secret_key = os.environ.get("SECRET_KEY", "chave_segura_fallback_2026_alterar_em_prod")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:200466@localhost:5432/ContasOrcamento"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializa banco de dados
db = SQLAlchemy(app)
print("✅ Banco de dados configurado!")

# 🔐 INICIALIZAÇÃO DO FLASK-LOGIN (CORREÇÃO DO ERRO)
login_manager = LoginManager()
login_manager.init_app(app)  # ← Vincula ao app Flask
login_manager.login_view = 'login'  # Redireciona não-autenticados
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

# ============================================================================
# MODELO DE USUÁRIO (NOVO - OBRIGATÓRIO PARA FLASK-LOGIN)
# ============================================================================
class User(UserMixin, db.Model):
    """Modelo de usuário para autenticação"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Gera hash seguro para a senha"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nome_completo': self.nome_completo,
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================================
# MODELOS EXISTENTES (MANTIDOS)
# ============================================================================
class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    tipo = db.Column(db.String(1), default='D')  # R=Receita, D=Despesa
    instituicao = db.Column(db.String(100))
    fonte_paga = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    pagamentos = db.relationship('Pagamento', back_populates='categoria_ref', lazy=True)
    
    def __repr__(self):
        return f'<Categoria {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome, 'tipo': self.tipo,
            'instituicao': self.instituicao or '',
            'fonte_paga': self.fonte_paga or '',
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None
        }


class Pagamento(db.Model):
    __tablename__ = 'pagamentos'
    cod = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Campos obrigatórios
    mes_ano = db.Column(db.String(7), nullable=False)  # MM/AAAA
    conta = db.Column(db.String(200), nullable=False)
    data_venc = db.Column(db.String(10), nullable=False)  # DD/MM/AAAA
    valor_pagar = db.Column(db.Numeric(10, 2), nullable=False)
    receita_despesa = db.Column(db.String(1), default='D')
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    
    # Campos opcionais
    instituicao = db.Column(db.String(100))
    fonte_paga = db.Column(db.String(100))
    data_pago = db.Column(db.String(10))
    valor_pago = db.Column(db.Numeric(10, 2), default=0)
    parcela = db.Column(db.String(10))
    observacao = db.Column(db.Text)
    competencia = db.Column(db.String(7))
    juros = db.Column(db.Numeric(10, 2), default=0)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    categoria_ref = db.relationship('Categoria', back_populates='pagamentos', lazy=True)
    documentos = db.relationship('Documento', backref='pagamento_ref', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Pagamento {self.conta} - {self.mes_ano}>'
    
    @property
    def status(self):
        """Retorna: 'pago', 'atrasado' ou 'pendente'"""
        if self.valor_pago and float(self.valor_pago) > 0:
            return 'pago'
        if not self.data_pago or self.data_pago == '':
            try:
                venc = datetime.strptime(self.data_venc, '%d/%m/%Y')
                if venc.date() < datetime.now().date():
                    return 'atrasado'
                return 'pendente'
            except:
                return 'pendente'
        return 'pendente'
    
    def to_dict(self):
        return {
            "id": self.cod, "cod": self.cod,
            "mes_ano": self.mes_ano or "", "conta": self.conta or "",
            "instituicao": self.instituicao or "", "fonte_paga": self.fonte_paga or "",
            "data_venc": self.data_venc or "", 
            "valor_pagar": float(self.valor_pagar) if self.valor_pagar else 0.0,
            "data_pago": self.data_pago or "", 
            "valor_pago": float(self.valor_pago) if self.valor_pago else 0.0,
            "parcela": self.parcela or "", "observacao": self.observacao or "",
            "receita_despesa": self.receita_despesa or "D", 
            "competencia": self.competencia or "",
            "juros": float(self.juros) if self.juros else 0.0, 
            "desconto": float(self.desconto) if self.desconto else 0.0,
            "categoria": self.categoria_ref.nome if self.categoria_ref else "",
            "categoria_id": self.categoria_id,
            "status": self.status,
            "documentos": [{"id": d.id, "nome": d.nome_arquivo} for d in self.documentos],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Documento(db.Model):
    __tablename__ = 'documentos_pagamento'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pagamento_id = db.Column(db.Integer, db.ForeignKey('pagamentos.cod', ondelete='CASCADE'), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_mime = db.Column(db.String(100), default='application/pdf')
    conteudo = db.Column(db.LargeBinary, nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    tamanho = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Documento {self.nome_arquivo}>'
    
    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome_arquivo,
            'tipo': self.tipo_mime, 'tamanho': self.tamanho,
            'data_upload': self.data_upload.isoformat() if self.data_upload else None,
            'url_visualizar': f'/visualizar_documento/{self.id}' if self.id else None
        }

# ============================================================================
# CALLBACK OBRIGATÓRIO: USER LOADER (CORREÇÃO DO ERRO)
# ============================================================================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ============================================================================
# CONTEXT PROCESSOR: GARANTE current_user NOS TEMPLATES
# ============================================================================
@app.context_processor
def inject_user():
    """Disponibiliza current_user em TODOS os templates Jinja2"""
    return dict(current_user=current_user)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def limpar_valor(valor_str):
    """Converte string monetária '1.234,56' para float 1234.56"""
    if not valor_str:
        return 0.0
    try:
        limpo = str(valor_str).replace('.', '').replace(',', '.')
        return float(limpo)
    except:
        return 0.0

def formatar_data_br(data_iso):
    """Converte 'AAAA-MM-DD' para 'DD/MM/AAAA'"""
    if not data_iso:
        return None
    try:
        dt = datetime.strptime(data_iso, '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except:
        return None

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
            print("✅ Categorias iniciais criadas.")
    except Exception as e:
        print(f"⚠️ Aviso ao criar categorias: {e}")
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

# ============================================================================
# CONFIGURAÇÃO DE E-MAIL
# ============================================================================
CONFIG_FILE = 'config_notificacoes.json'

def carregar_config_email():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'email_destino': os.getenv('EMAIL_RECEIVER', ''),
        'alertas_ativos': True,
        'backup_ativo': True
    }

def salvar_config_email(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar config: {e}")
        return False

# ============================================================================
# 🔐 ROTAS DE AUTENTICAÇÃO (NOVAS)
# ============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login para usuários"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash("⚠️ Preencha usuário e senha!", "warning")
            return redirect(url_for('login'))
        
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.check_password(password) and user.ativo:
            login_user(user, remember=remember)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            flash(f"👋 Bem-vindo, {user.nome_completo or user.username}!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash("❌ Usuário ou senha inválidos!", "danger")
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Encerra sessão do usuário"""
    username = current_user.username
    logout_user()
    flash(f"👋 Até logo, {username}!", "info")
    return redirect(url_for('landing_page'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novo usuário (apenas para desenvolvimento)"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        nome_completo = request.form.get('nome_completo', '').strip()
        
        # Validações
        if not all([username, email, password, confirm]):
            flash("⚠️ Preencha todos os campos!", "warning")
            return redirect(url_for('register'))
        if password != confirm:
            flash("❌ As senhas não coincidem!", "danger")
            return redirect(url_for('register'))
        if len(password) < 6:
            flash("❌ A senha deve ter pelo menos 6 caracteres!", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash("❌ Nome de usuário já existe!", "danger")
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash("❌ E-mail já cadastrado!", "danger")
            return redirect(url_for('register'))
        
        # Cria usuário
        novo_user = User(
            username=username,
            email=email,
            nome_completo=nome_completo or username
        )
        novo_user.set_password(password)
        
        try:
            db.session.add(novo_user)
            db.session.commit()
            flash("✅ Conta criada com sucesso! Faça login para continuar.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao criar conta: {str(e)}", "danger")
            return redirect(url_for('register'))
    
    return render_template('register.html')


# ============================================================================
# 🏠 ROTAS PRINCIPAIS
# ============================================================================

@app.route('/')
def landing_page():
    """🎯 Página inicial: Landing Page profissional"""
    return render_template('landing_page.html')


@app.route('/index')
@app.route('/sistema')
def index():
    """📊 Sistema principal: Grid de pagamentos com filtros"""
    data_hoje_str = datetime.now().strftime('%d/%m/%Y')
    
    # Captura parâmetros de filtro
    filtros = {k: request.args.get(k, '').strip() for k in [
        'MesAno', 'Conta', 'Instituicao', 'Fontepaga', 
        'Competencia', 'Categoria', 'status'
    ]}
    
    # Verifica se há filtros ativos
    tem_filtros = any(filtros.values())
    
    # Primeiro acesso sem filtros → grid vazio
    if not tem_filtros:
        categorias = Categoria.query.order_by(Categoria.nome).all()
        return render_template('index.html',
            pagamentos=[], total_a_pagar=0, total_pago=0, total_receitas=0, contas_hoje=0,
            data_hoje=data_hoje_str, categorias=categorias
        )
    
    # Busca com filtros
    query = Pagamento.query
    for chave, valor in filtros.items():
        if valor:
            if chave == 'Categoria':
                query = query.join(Categoria).filter(Categoria.nome.ilike(f"%{valor}%"))
            elif chave == 'status':
                if valor == 'pago':
                    query = query.filter(Pagamento.valor_pago > 0)
                elif valor == 'pendente':
                    query = query.filter((Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)))
                elif valor == 'atrasado':
                    query = query.filter(
                        Pagamento.data_venc < data_hoje_str,
                        (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None))
                    )
            else:
                campo = getattr(Pagamento, chave.lower(), None)
                if campo:
                    query = query.filter(campo.ilike(f"%{valor}%"))
    
    pagamentos = query.order_by(
        func.to_date(Pagamento.mes_ano, 'MM/YYYY').desc(),
        Pagamento.conta.asc()
    ).all()
    
    # Cálculos de totais
    total_a_pagar = sum(float(p.valor_pagar or 0) for p in pagamentos if p.receita_despesa == 'D')
    total_receitas = sum(float(p.valor_pagar or 0) for p in pagamentos if p.receita_despesa == 'R')
    total_pago = sum(float(p.valor_pago or 0) for p in pagamentos)
    
    contas_hoje = Pagamento.query.filter(
        Pagamento.data_venc == data_hoje_str,
        (Pagamento.valor_pago == 0) | (Pagamento.valor_pago.is_(None)),
        Pagamento.receita_despesa == 'D'
    ).count()
    
    categorias = Categoria.query.order_by(Categoria.nome).all()
    
    return render_template('index.html',
        pagamentos=pagamentos,
        total_a_pagar=total_a_pagar, total_pago=total_pago, total_receitas=total_receitas,
        contas_hoje=contas_hoje, data_hoje=data_hoje_str, categorias=categorias
    )


# ============================================================================
# 📊 ROTA PARA O DASHBOARD
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """📈 Dashboard analítico com gráficos"""
    
    # ✅ Variáveis necessárias para o template
    now = datetime.now(timezone.utc)
    ano_atual = datetime.now().year
    
    # ✅ Buscar categorias para o filtro
    categorias = Categoria.query.order_by(Categoria.nome).all()
    
    # ✅ Capturar parâmetros de filtro (se existirem)
    ano_selecionado = request.args.get('ano', ano_atual, type=int)
    categoria_selecionada = request.args.get('categoria', '', type=str)
    
    # ✅ Dados básicos para os KPIs (exemplo - ajuste conforme sua lógica)
    # Estes são valores placeholder - substitua pelas consultas reais ao banco
    receitas_vig = 0.0
    despesas_vig = 0.0
    
    # Exemplo: buscar dados reais se houver filtros
    if ano_selecionado:
        # Ajuste estas consultas conforme sua necessidade
        from sqlalchemy import extract
        
        receitas_vig = db.session.query(
            db.func.sum(Pagamento.valor_pagar)
        ).filter(
            Pagamento.receita_despesa == 'R',
            extract('year', Pagamento.created_at) == ano_selecionado
        ).scalar() or 0.0
        
        despesas_vig = db.session.query(
            db.func.sum(Pagamento.valor_pagar)
        ).filter(
            Pagamento.receita_despesa == 'D',
            extract('year', Pagamento.created_at) == ano_selecionado
        ).scalar() or 0.0
    
    # ✅ Dados para os gráficos (placeholder - ajuste conforme necessário)
    ant = [0] * 12  # Ano anterior
    vig = [0] * 12  # Ano vigente
    fut = [0] * 12  # Ano futuro (projeção)
    
    # ✅ Renderizar template com TODAS as variáveis necessárias
    return render_template(
        'dashboard.html',
        now=now,                          # ← ESSENCIAL para o link do relatório
        categorias=categorias,            # ← Para o select de filtros
        ano_selecionado=ano_selecionado,
        categoria_selecionada=categoria_selecionada,
        ano_vig=ano_atual,
        ano_ant=ano_atual - 1,
        ano_fut=ano_atual + 1,
        receitas_vig=receitas_vig,
        despesas_vig=despesas_vig,
        saldo_liquido=receitas_vig - despesas_vig,
        pct_receitas=(receitas_vig / (receitas_vig + despesas_vig) * 100) if (receitas_vig + despesas_vig) > 0 else 0,
        pct_despesas=(despesas_vig / (receitas_vig + despesas_vig) * 100) if (receitas_vig + despesas_vig) > 0 else 0,
        ant=ant,
        vig=vig,
        fut=fut,
        dados_categorias=[],  # ← Preencher com dados reais se necessário
        dados_tendencia={}    # ← Preencher com dados reais se necessário
    )

# ============================================================================
# 📊 API PARA DASHBOARD
# ============================================================================
@app.route('/api/dashboard/data')
@login_required  # 🔐 Protege API
def api_dashboard_data():
    """Retorna dados para gráficos do dashboard"""
    try:
        # Despesas por categoria (Top 10)
        despesas_cat = db.session.query(
            Categoria.nome,
            func.sum(Pagamento.valor_pagar).label('total')
        ).join(Pagamento).filter(
            Pagamento.receita_despesa == 'D'
        ).group_by(Categoria.nome).order_by(
            func.sum(Pagamento.valor_pagar).desc()
        ).limit(10).all()
        
        # Evolução mensal (últimos 12 meses)
        meses, despesas_vals, receitas_vals = [], [], []
        for i in range(11, -1, -1):
            ref = datetime.now() - timedelta(days=i*30)
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
        
        # Status pagamentos
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


# ============================================================================
# 🔄 CRUD - AÇÕES DO SISTEMA
# ============================================================================
@app.route('/add', methods=['POST'])
@login_required  # 🔐 Protege ação
def add():
    """Adicionar novo pagamento"""
    try:
        mes_ano = request.form.get('MesAno', '').strip()
        conta = request.form.get('Conta', '').strip()
        data_venc_raw = request.form.get('Data_venc', '').strip()
        valor_pagar_raw = request.form.get('Valor_pagar', '').strip()
        categoria_nome = request.form.get('Categoria', '').strip()
        tipo_op = request.form.get('ReceitaDespesa', 'D').strip().upper()
        
        # Validações
        if not all([mes_ano, conta, data_venc_raw, valor_pagar_raw]):
            flash("⚠️ Preencha todos os campos obrigatórios!", "warning")
            return redirect(url_for('index'))
        
        # Processa valores
        valor_pagar = limpar_valor(valor_pagar_raw)
        data_venc = formatar_data_br(data_venc_raw)
        
        # Resolve categoria
        categoria_id = None
        if categoria_nome and categoria_nome != 'Outros':
            cat = Categoria.query.filter_by(nome=categoria_nome).first()
            if cat:
                categoria_id = cat.id
        
        novo = Pagamento(
            mes_ano=mes_ano, conta=conta, data_venc=data_venc,
            valor_pagar=valor_pagar, receita_despesa=tipo_op,
            categoria_id=categoria_id,
            instituicao=request.form.get('Instituicao', '').strip() or None,
            fonte_paga=request.form.get('Fontepaga', '').strip() or None,
            observacao=request.form.get('Observacao', '').strip() or None,
            competencia=request.form.get('Competencia', '').strip() or None,
            juros=limpar_valor(request.form.get('Juros', '0')),
            desconto=limpar_valor(request.form.get('Desconto', '0'))
        )
        
        db.session.add(novo)
        db.session.commit()
        flash("✅ Registro inserido com sucesso!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao salvar: {str(e)}", "danger")
    
    return redirect(url_for('index'))


@app.route('/alterar', methods=['POST'])
@login_required  # 🔐 Protege ação
def alterar():
    """Atualizar registro existente"""
    cod = request.form.get('cod', '').strip()
    if not cod:
        flash("⚠️ Selecione um registro para alterar!", "warning")
        return redirect(url_for('index'))
    
    try:
        pg = Pagamento.query.get(int(cod))
        if not pg:
            flash("❌ Registro não encontrado!", "danger")
            return redirect(url_for('index'))
        
        # Atualiza campos
        pg.mes_ano = request.form.get('MesAno', pg.mes_ano)
        pg.conta = request.form.get('Conta', pg.conta)
        pg.receita_despesa = request.form.get('ReceitaDespesa', pg.receita_despesa)
        
        dv = request.form.get('Data_venc')
        if dv:
            pg.data_venc = formatar_data_br(dv)
        
        vp = request.form.get('Valor_pagar')
        if vp:
            pg.valor_pagar = limpar_valor(vp)
        
        vpg = request.form.get('Valor_pago')
        pg.valor_pago = limpar_valor(vpg) if vpg else 0
        
        db.session.commit()
        flash("✅ Registro alterado com sucesso!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao alterar: {str(e)}", "danger")
    
    return redirect(url_for('index'))


@app.route('/apagar', methods=['POST'])
@login_required  # 🔐 Protege ação
def apagar():
    """Excluir registro"""
    cod = request.form.get('cod')
    if not cod:
        flash("⚠️ Selecione um registro para excluir!", "warning")
        return redirect(url_for('index'))
    
    try:
        pg = Pagamento.query.get(int(cod))
        if pg:
            db.session.delete(pg)
            db.session.commit()
            flash("✅ Registro excluído permanentemente!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao excluir: {str(e)}", "danger")
    
    return redirect(url_for('index'))


# ============================================================================
# 📎 GESTÃO DE DOCUMENTOS
# ============================================================================
@app.route('/upload_documento/<int:cod>', methods=['POST'])
@login_required  # 🔐 Protege upload
def upload_documento(cod):
    """Upload de PDF para um registro"""
    if 'documento' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
    
    arquivo = request.files['documento']
    if arquivo.filename == '' or not arquivo.filename.lower().endswith('.pdf'):
        return jsonify({'erro': 'Apenas arquivos PDF são permitidos'}), 400
    
    try:
        pg = db.session.get(Pagamento, int(cod))
        if not pg:
            return jsonify({'erro': 'Registro não encontrado'}), 404
        
        doc = Documento(
            nome_arquivo=secure_filename(arquivo.filename),
            conteudo=arquivo.read(),
            tipo_mime='application/pdf',
            pagamento_id=cod,
            tamanho=arquivo.content_length or 0
        )
        db.session.add(doc)
        db.session.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Arquivo enviado com sucesso!'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao salvar: {str(e)}'}), 500


@app.route('/visualizar_documento/<int:doc_id>')
@login_required  # 🔐 Protege visualização
def visualizar_documento(doc_id):
    """Visualizar documento anexado"""
    try:
        doc = Documento.query.get_or_404(doc_id)
        if not doc.conteudo:
            flash("Arquivo vazio ou não encontrado.", "warning")
            return redirect(url_for('index'))
        
        return send_file(
            io.BytesIO(doc.conteudo),
            mimetype=doc.tipo_mime,
            as_attachment=False,
            download_name=doc.nome_arquivo
        )
    except Exception as e:
        flash(f"Erro ao visualizar: {e}", "danger")
        return redirect(url_for('index'))


# ============================================================================
# 📧 CONFIGURAÇÃO DE E-MAIL (API)
# ============================================================================
@app.route('/api/config/email', methods=['GET'])
@login_required
def get_config_email():
    config = carregar_config_email()
    return jsonify({'sucesso': True, 'config': config})


@app.route('/api/config/email', methods=['POST'])
@login_required
def set_config_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email or '@' not in email:
            return jsonify({'sucesso': False, 'erro': 'E-mail inválido'}), 400
        
        config = {
            'email_destino': email,
            'alertas_ativos': data.get('alertas_ativos', True),
            'backup_ativos': data.get('backup_ativos', True),
            'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        if salvar_config_email(config):
            return jsonify({'sucesso': True, 'mensagem': 'Configuração salva com sucesso!'})
        return jsonify({'sucesso': False, 'erro': 'Erro ao salvar'}), 500
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================================================
# 📊 CATEGORIAS (API AJAX)
# ============================================================================
@app.route('/api/categorias')
def api_categorias():
    """Listar categorias para autocomplete"""
    tipo = request.args.get('tipo')
    query = Categoria.query.order_by(Categoria.nome)
    if tipo in ['R', 'D']:
        query = query.filter_by(tipo=tipo)
    return jsonify([c.to_dict() for c in query.all()])


@app.route('/api/categorias', methods=['POST'])
@login_required
def api_adicionar_categoria():
    """Adicionar nova categoria via AJAX"""
    try:
        data = request.get_json() or request.form
        nome = data.get('nome', '').strip().upper()
        tipo = data.get('tipo', 'D')
        
        if not nome or len(nome) < 3:
            return jsonify({'erro': 'Nome deve ter pelo menos 3 caracteres'}), 400
        if tipo not in ['R', 'D']:
            return jsonify({'erro': 'Tipo deve ser R ou D'}), 400
        if Categoria.query.filter_by(nome=nome).first():
            return jsonify({'erro': 'Categoria já existe'}), 409
        
        nova = Categoria(nome=nome, tipo=tipo)
        db.session.add(nova)
        db.session.commit()
        return jsonify({'sucesso': True, 'categoria': nova.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# ============================================================================
# 📄 RELATÓRIOS
# ============================================================================
@app.route('/exportar_csv')
@login_required
def exportar_csv():
    """Exportar dados para CSV"""
    mes_ano = request.args.get('MesAno', '').strip()
    
    query = Pagamento.query.order_by(Pagamento.data_venc)
    if mes_ano:
        query = query.filter(Pagamento.mes_ano.ilike(f"%{mes_ano}%"))
    
    pagamentos = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow([
        'Cód', 'Mês/Ano', 'Conta', 'Categoria', 'Tipo',
        'Vencimento', 'Valor Pagar', 'Data Pago', 'Valor Pago', 'Observação'
    ])
    
    for p in pagamentos:
        writer.writerow([
            p.cod, p.mes_ano or '', p.conta or '',
            p.categoria_ref.nome if p.categoria_ref else '',
            'Receita' if p.receita_despesa == 'R' else 'Despesa',
            p.data_venc or '',
            f"{float(p.valor_pagar or 0):.2f}".replace('.', ','),
            p.data_pago or '',
            f"{float(p.valor_pago or 0):.2f}".replace('.', ','),
            (p.observacao or '').replace(';', ',')
        ])
    
    output.seek(0)
    csv_content = output.getvalue().encode('utf-8-sig')
    
    return send_file(
        io.BytesIO(csv_content),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'pagamentos_{datetime.now().strftime("%Y%m%d")}.csv'
    )


# ============================================================================
# ⚙️ ERROR HANDLERS
# ============================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template('landing_page.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    flash('❌ Erro interno do servidor. Tente novamente.', 'danger')
    return redirect(url_for('index'))

@app.errorhandler(401)
def unauthorized(e):
    """Trata acesso não autorizado"""
    flash("🔐 Acesso restrito. Faça login para continuar.", "warning")
    return redirect(url_for('login'))


# ============================================================================
# 🚀 EXECUÇÃO + INICIALIZAÇÃO DO BANCO
# ============================================================================
if __name__ == '__main__':
    with app.app_context():
        # Cria todas as tabelas (incluindo 'users' para autenticação)
        db.create_all()
        
        # Popula categorias iniciais
        popular_categorias_iniciais()
        
        # Cria usuário admin padrão se não existir (apenas para dev)
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@localhost',
                nome_completo='Administrador'
            )
            admin.set_password('admin123')  # 🔐 Alterar em produção!
            db.session.add(admin)
            db.session.commit()
            print("👤 Usuário 'admin' criado (senha: admin123)")
    
    print("✅ Banco de dados configurado!")
    print("🚀 Servidor iniciado em http://localhost:5000")
    print("🏠 Landing Page: http://localhost:5000/")
    print("🔐 Login: http://localhost:5000/login")
    print("📊 Sistema: http://localhost:5000/sistema")
    print("📈 Dashboard: http://localhost:5000/dashboard")
    
    app.run(debug=True, host='0.0.0.0', port=5000)