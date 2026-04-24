from datetime import datetime
from database import db
from sqlalchemy import func, extract
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Categoria(db.Model):
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    tipo = db.Column(db.String(1), default='D')
    instituicao = db.Column(db.String(100))
    fonte_paga = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
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
    mes_ano = db.Column(db.String(7), nullable=False)
    conta = db.Column(db.String(200), nullable=False)
    data_venc = db.Column(db.String(10), nullable=False)
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
        if self.valor_pago and float(self.valor_pago) > 0:
            return 'pago'
        if not self.data_pago or self.data_pago == '':
            try:
                from datetime import datetime as dt
                # Ajuste para formatos DD/MM/YYYY ou YYYY-MM-DD
                sep = '/' if '/' in self.data_venc else '-'
                if sep == '/':
                    venc = dt.strptime(self.data_venc, '%d/%m/%Y')
                else:
                    venc = dt.strptime(self.data_venc, '%Y-%m-%d')
                
                hoje = dt.now()
                if venc.date() < hoje.date():
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
            "data_venc": self.data_venc or "", "valor_pagar": float(self.valor_pagar) if self.valor_pagar else 0.0,
            "data_pago": self.data_pago or "", "valor_pago": float(self.valor_pago) if self.valor_pago else 0.0,
            "parcela": self.parcela or "", "observacao": self.observacao or "",
            "receita_despesa": self.receita_despesa or "D", "competencia": self.competencia or "",
            "juros": float(self.juros) if self.juros else 0.0, "desconto": float(self.desconto) if self.desconto else 0.0,
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

class MetaOrcamento(db.Model):
    __tablename__ = 'metas_orcamento'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    mes_ano = db.Column(db.String(7), nullable=False) # MM/YYYY
    valor_meta = db.Column(db.Float, nullable=False, default=0.0)
    
    categoria = db.relationship('Categoria', backref=db.backref('metas', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'categoria': self.categoria.nome,
            'mes_ano': self.mes_ano,
            'valor_meta': self.valor_meta
        }

class TransacaoExtrato(db.Model):
    __tablename__ = 'transacoes_extrato'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fitid = db.Column(db.String(100), unique=True) # ID único da transação no banco (evita duplicatas)
    data = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    tipo = db.Column(db.String(1)) # 'R' ou 'D'
    conciliado = db.Column(db.Boolean, default=False)
    pagamento_id = db.Column(db.Integer, db.ForeignKey('pagamentos.cod', ondelete='SET NULL'))
    
    # Metadados de importação
    data_importacao = db.Column(db.DateTime, default=datetime.utcnow)
    banco = db.Column(db.String(50)) # Ex: Nubank, Itaú
    
    # Relacionamento com o registro de pagamento real
    pagamento_ref = db.relationship('Pagamento', backref=db.backref('transacoes_bancarias', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'fitid': self.fitid,
            'data': self.data.isoformat() if self.data else None,
            'descricao': self.descricao,
            'valor': float(self.valor),
            'tipo': self.tipo,
            'conciliado': self.conciliado,
            'pagamento_id': self.pagamento_id,
            'banco': self.banco
        }

class ReservaEmergencia(db.Model):
    __tablename__ = 'reserva_emergencia'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    objetivo_meses = db.Column(db.Integer, default=6) # Ex: 6 meses de despesas
    valor_manual = db.Column(db.Numeric(10, 2), default=0) # Valor que o usuário já tem guardado fora do sistema
    
    def to_dict(self):
        return {
            'id': self.id,
            'objetivo_meses': self.objetivo_meses,
            'valor_manual': float(self.valor_manual)
        }
