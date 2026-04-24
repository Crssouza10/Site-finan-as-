from datetime import datetime

def limpar_valor(valor_str):
    """Converte string monetária '1.234,56' para float 1234.56"""
    if not valor_str:
        return 0.0
    try:
        limpo = valor_str.replace('.', '').replace(',', '.')
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
