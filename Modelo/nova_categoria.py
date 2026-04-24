# script_atualizacao.py
from app import app, db, Pagamento, Categoria

with app.app_context():
    # Adicionar colunas novas em Pagamento (se usar Alembic, migre formalmente)
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('pagamentos')]
    
    if 'competencia' not in columns:
        with db.engine.connect() as conn:
            conn.execute("ALTER TABLE pagamentos ADD COLUMN competencia VARCHAR(10)")
            conn.execute("ALTER TABLE pagamentos ADD COLUMN juros NUMERIC(10,2) DEFAULT 0")
            conn.execute("ALTER TABLE pagamentos ADD COLUMN desconto NUMERIC(10,2) DEFAULT 0")
            conn.commit()
        print("✅ Colunas adicionadas!")
    
    # Garantir que 'Outros' exista em Categoria
    if not Categoria.query.filter_by(nome='OUTROS').first():
        db.session.add(Categoria(nome='OUTROS', tipo='D'))
        db.session.commit()
        print("✅ Categoria 'OUTROS' criada!")