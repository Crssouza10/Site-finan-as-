from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('main.index'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novo usuário"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        nome_completo = request.form.get('nome_completo', '').strip()
        
        # Validações
        if not all([username, email, password, confirm]):
            flash("⚠️ Preencha todos os campos!", "warning")
            return redirect(url_for('auth.register'))
        if password != confirm:
            flash("❌ As senhas não coincidem!", "danger")
            return redirect(url_for('auth.register'))
        if len(password) < 6:
            flash("❌ A senha deve ter pelo menos 6 caracteres!", "danger")
            return redirect(url_for('auth.register'))
        if User.query.filter_by(username=username).first():
            flash("❌ Nome de usuário já existe!", "danger")
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash("❌ E-mail já cadastrado!", "danger")
            return redirect(url_for('auth.register'))
        
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
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erro ao criar conta: {str(e)}", "danger")
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        identifier = request.form.get('email', '').strip()
        user = User.query.filter_by(username=identifier).first()
            
        if user:
            token = user.get_reset_token()
            # Simulando envio de email exibindo o link
            link = url_for('auth.reset_password', token=token)
            flash(f'Simulação de e-mail: Clique <a href="{link}" class="alert-link">aqui para resetar sua senha</a>.', 'info')
        else:
            flash('Se o usuário ou e-mail existir, um link de recuperação será gerado.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_token(token)
    if not user:
        flash('O token é inválido ou expirou.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        user.set_password(password)
        db.session.commit()
        flash('Sua senha foi atualizada! Você já pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password.html')
