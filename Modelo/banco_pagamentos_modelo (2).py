
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexão fornecida
DATABASE_URL = "postgresql://postgres:200466@localhost:5432/Orcamento"

# Configuração do Engine e Base
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definição das Tabelas (Modelos)
class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)

class Conta(Base):
    __tablename__ = "contas"
    
    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    paga = Column(Boolean, default=False)
    tipo = Column(String)  # 'Receita' ou 'Despesa'
    
    # Relacionamento com Categoria
    categoria_id = Column(Integer, ForeignKey("categorias.id"))

def criar_tabelas():
    """Função para criar as tabelas no banco de dados"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Tabelas criadas com sucesso no banco 'Orcamento'!")
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")

if __name__ == "__main__":
    criar_tabelas()