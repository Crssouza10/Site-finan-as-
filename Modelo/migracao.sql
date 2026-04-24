-- Adiciona colunas faltantes na tabela pagamentos
ALTER TABLE pagamentos 
ADD COLUMN IF NOT EXISTS receita_despesa VARCHAR(1),
ADD COLUMN IF NOT EXISTS categoria_id INTEGER;

-- Cria a tabela categorias se não existir
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    tipo_operacao VARCHAR(1) NOT NULL,
    instituicao VARCHAR(100),
    fonte_paga VARCHAR(100)
);

-- Adiciona a chave estrangeira
ALTER TABLE pagamentos 
ADD CONSTRAINT fk_categoria 
FOREIGN KEY (categoria_id) REFERENCES categorias(id);

-- Popula categorias iniciais
INSERT INTO categorias (nome, tipo_operacao, instituicao, fonte_paga)
VALUES 
    ('Moradia', 'D', NULL, NULL),
    ('Alimentação', 'D', NULL, NULL),
    ('Transporte', 'D', NULL, NULL),
    ('Saúde', 'D', NULL, NULL),
    ('Educação', 'D', NULL, NULL),
    ('Lazer', 'D', NULL, NULL),
    ('Salário', 'R', NULL, NULL),
    ('Freelance', 'R', NULL, NULL),
    ('Investimentos', 'R', NULL, NULL),
    ('Renda Extra', 'R', NULL, NULL)
ON CONFLICT (nome) DO NOTHING;