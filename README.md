# SmartWallet AI 🚀
## Acompanhamento e Educação Financeira Preditiva

O **SmartWallet AI** é uma plataforma SaaS premium para gestão financeira inteligente, focada em transformar dados em educação e previsibilidade financeira.

## 📋 Pré-requisitos

1. **Python 3.10+** instalado.
2. **PostgreSQL** instalado e rodando.
3. Banco de dados criado (ex: `ContasOrcamento`).

## 🚀 Como instalar e rodar

1. **Instalar Dependências**:
   Abra o terminal na pasta do projeto e execute:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar Variáveis de Ambiente**:
   Crie ou edite o arquivo `.env` na raiz do projeto com as seguintes informações:
   ```env
   DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/ContasOrcamento
   SECRET_KEY=uma_chave_secreta_aleatoria
   ADMIN_USER=admin
   ADMIN_PASS=admin123
   EMAIL_USER=seu_email@gmail.com
   EMAIL_PASS=sua_senha_de_app
   ```

3. **Iniciar o Sistema**:
   Execute o comando:
   ```bash
   python app.py
   ```

4. **Acessar**:
   Abra o navegador em `http://localhost:5000`

## 🔐 Credenciais Padrão
- **Usuário**: `admin`
- **Senha**: `admin123`

## 🛠️ Funcionalidades Principais
- **Login Seguro**: Proteção de todos os dados financeiros.
- **Orçamento**: Defina metas mensais por categoria.
- **Recorrência**: Copie contas para o mês seguinte com um clique.
- **Relatórios**: PDFs mensais, anuais e por conta.
- **Backups**: Backup manual e automático do banco de dados.
