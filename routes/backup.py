from flask_login import login_required
from flask import Blueprint, render_template, request, jsonify, send_file
from pathlib import Path
from datetime import datetime
import os
import zipfile
import tempfile
import shutil
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup')
@login_required
def backup_page():
    """Página de gerenciamento de backups"""
    backup_dir = Path(__file__).parent.parent / "backups"
    backups = []
    if backup_dir.exists():
        for backup_file in sorted(backup_dir.glob("backup_*.zip"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                'nome': backup_file.name,
                'tamanho_kb': round(stat.st_size / 1024, 2),
                'data_criacao': datetime.fromtimestamp(stat.st_ctime).strftime('%d/%m/%Y %H:%M')
            })
    return render_template('backup.html', backups=backups)

@backup_bp.route('/api/backup/create', methods=['POST'])
@login_required
def api_create_backup():
    """Cria backup manual e retorna informações"""
    try:
        from backup_db import criar_backup
        zip_path = criar_backup()
        return jsonify({
            'success': True, 'message': 'Backup realizado com sucesso!',
            'file': Path(zip_path).name, 'path': str(Path(zip_path).parent)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@backup_bp.route('/api/backup/download/<filename>')
@login_required
def download_backup(filename):
    """Permite download de um backup específico"""
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_file = backup_dir / filename
    if not backup_file.exists() or not backup_file.resolve().is_relative_to(backup_dir.resolve()):
        return jsonify({'error': 'Arquivo não encontrado ou acesso negado'}), 404
    return send_file(backup_file, as_attachment=True, download_name=filename)

@backup_bp.route('/api/backup/delete/<filename>', methods=['POST'])
@login_required
def delete_backup(filename):
    """Exclui um backup específico"""
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_file = backup_dir / filename
    if not backup_file.exists() or not backup_file.resolve().is_relative_to(backup_dir.resolve()):
        return jsonify({'error': 'Arquivo não encontrado ou acesso negado'}), 404
    try:
        backup_file.unlink()
        return jsonify({'success': True, 'message': f'Backup {filename} excluído!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@backup_bp.route('/api/backup/restore', methods=['POST'])
@login_required
def api_restore_backup():
    """Restaura banco de dados a partir de um backup"""
    filename = request.json.get('filename')
    if not filename or not filename.endswith('.zip'):
        return jsonify({'success': False, 'error': 'Arquivo inválido'}), 400
    
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_file = backup_dir / filename
    if not backup_file.exists() or not backup_file.resolve().is_relative_to(backup_dir.resolve()):
        return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    
    try:
        temp_dir = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(backup_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            sql_files = list(temp_dir.glob("*.sql"))
            if not sql_files: raise Exception("Arquivo SQL não encontrado no backup")
            sql_file = sql_files[0]
        
        conn = psycopg2.connect(
            host="localhost", port="5432", user="postgres",
            password=os.getenv("DB_PASSWORD", "200466"), dbname="ContasOrcamento"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        commands = sql_script.split(';')
        executed = 0
        for command in commands:
            cmd = command.strip()
            if cmd and not cmd.startswith('--'):
                try:
                    cur.execute(cmd)
                    executed += 1
                except Exception as cmd_error:
                    if 'already exists' not in str(cmd_error): print(f"⚠️ {cmd_error}")
        
        cur.close(); conn.close(); shutil.rmtree(temp_dir)
        return jsonify({'success': True, 'message': f'Banco restaurado! {executed} comandos executados.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
