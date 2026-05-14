# test_app.py
from app_finace import app, db, User, Pagamento, Categoria
from datetime import datetime, timezone

def test_app():
    with app.app_context():
        print("🔍 Testando aplicação...")
        
        # Teste 1: Conexão com banco
        try:
            total_users = db.session.query(User).count()
            print(f"✅ Banco conectado | Users: {total_users}")
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return
        
        # Teste 2: Timezone-aware
        user = db.session.query(User).first()
        if user and user.created_at:
            tz = user.created_at.tzinfo
            print(f"✅ Timezone: {tz} {'(CORRETO)' if tz else '(⚠️ Sem timezone)'}")
        
        # Teste 3: Dados de pagamento
        total_pag = db.session.query(Pagamento).count()
        receitas = db.session.query(Pagamento).filter_by(receita_despesa='R').count()
        despesas = db.session.query(Pagamento).filter_by(receita_despesa='D').count()
        print(f"✅ Pagamentos: {total_pag} | Receitas: {receitas} | Despesas: {despesas}")
        
        # Teste 4: Categorias
        total_cat = db.session.query(Categoria).count()
        print(f"✅ Categorias: {total_cat}")
        
        print("\n🎉 Aplicação validada com sucesso!")

if __name__ == '__main__':
    test_app()