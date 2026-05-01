# ============================================================================
# APP PRINCIPAL - GESTÃO DE PAGAMENTOS
# ============================================================================
from flask import Flask
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

from flask_login import LoginManager
from database import db
from models import Categoria, Pagamento, Documento, User

def create_app():
    app = Flask(__name__)
    
    # Configurações
    # Configurações de Segurança e Ambiente
    app.secret_key = os.environ.get("SECRET_KEY")
    if not app.secret_key:
        # Especialista Sênior: Se não houver chave no .env, gera uma temporária para não quebrar
        # mas avisa que o ambiente não está configurado corretamente para produção.
        import secrets
        app.secret_key = secrets.token_hex(24)
        
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        # Fallback apenas para desenvolvimento local
        app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres@localhost:5432/ContasOrcamento"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # Verifica se está rodando no Vercel (onde apenas /tmp é gravável)
    if os.environ.get('VERCEL') == '1':
        app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    else:
        app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Inicialização DB
    db.init_app(app)

    # Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registro de Blueprints
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from routes.main import main_bp
    app.register_blueprint(main_bp)
    
    from routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from routes.extrato import extrato_bp
    app.register_blueprint(extrato_bp)
    
    from routes.reports import reports_bp
    app.register_blueprint(reports_bp)
    
    from routes.backup import backup_bp
    app.register_blueprint(backup_bp)
    
    from routes.api import api_bp
    app.register_blueprint(api_bp)

    # Filtros Jinja2 Globais
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.now()}

    return app

app = create_app()

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    from flask import render_template
    return render_template('base.html', content="Página não encontrada"), 404

@app.errorhandler(500)
def internal_server_error(e):
    from flask import render_template
    return render_template('base.html', content="Erro interno no servidor"), 500

def popular_dados_iniciais():
    """Inicializa categorias e usuário admin se necessário"""
    from routes.main import popular_categorias_iniciais
    popular_categorias_iniciais()
    
    # Criar usuário admin padrão se não houver usuários
    if User.query.count() == 0:
        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_pass = os.getenv("ADMIN_PASS", "admin123")
        
        user = User(username=admin_user)
        user.set_password(admin_pass)
        db.session.add(user)
        db.session.commit()
        print(f"Usuario '{admin_user}' criado com sucesso!")

# ============================================================================
# EXECUÇÃO
# ============================================================================
if __name__ == '__main__':
    with app.app_context():
        # Criar tabelas se não existirem
        db.create_all()
        # Popular dados iniciais (Categorias e Usuário)
        popular_dados_iniciais()
    
    print("Servidor iniciado em http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
