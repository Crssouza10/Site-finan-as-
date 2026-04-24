from sqlalchemy import create_engine, MetaData, Table, select, insert, text
from sqlalchemy.orm import sessionmaker
import sys

# Configuração das conexões
URI_ORIGEM = "postgresql://postgres:200466@localhost:5432/ContasPagar"
URI_DESTINO = "postgresql://postgres:200466@localhost:5432/ContasOrcamento"

print("=" * 70)
print(" VERIFICANDO CONEXÕES E DADOS...")
print("=" * 70)

try:
    engine_origem = create_engine(URI_ORIGEM)
    with engine_origem.connect() as conn:
        meta = MetaData()
        meta.reflect(bind=engine_origem)
        print(f"📋 Tabelas disponíveis na ORIGEM: {list(meta.tables.keys())}")
        
        tabela_pagamentos_origem = None
        count_pag = 0
        
        if 'pagamentos' in meta.tables:
            result = conn.execute(text("SELECT COUNT(*) FROM pagamentos"))
            count_pag = result.fetchone()[0]
            if count_pag > 0:
                tabela_pagamentos_origem = 'pagamentos'
                print(f"✅ Tabela 'pagamentos' (plural) encontrada com {count_pag} registros")
        
        if count_pag == 0 and 'pagamento' in meta.tables:
            result = conn.execute(text("SELECT COUNT(*) FROM pagamento"))
            count_pag = result.fetchone()[0]
            if count_pag > 0:
                tabela_pagamentos_origem = 'pagamento'
                print(f"✅ Tabela 'pagamento' (singular) encontrada com {count_pag} registros")
        
        if not tabela_pagamentos_origem:
            print("❌ Nenhuma tabela de pagamentos encontrada com dados!")
            sys.exit(1)
            
        print(f"🎯 Usando tabela: {tabela_pagamentos_origem}")
        
except Exception as e:
    print(f"❌ Erro na conexão ORIGEM: {e}")
    sys.exit(1)

try:
    engine_destino = create_engine(URI_DESTINO)
    with engine_destino.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pagamentos"))
        count_pag_dest = result.fetchone()[0]
        print(f"✅ Conexão DESTINO (ContasOrcamento): OK")
        print(f"   📊 Total atual na tabela 'pagamentos': {count_pag_dest}")
except Exception as e:
    print(f"❌ Erro na conexão DESTINO: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print(f" INICIANDO MIGRAÇÃO: ContasPagar → ContasOrcamento")
print("=" * 70)

SessionOrigem = sessionmaker(bind=engine_origem)
SessionDestino = sessionmaker(bind=engine_destino)

def migrar_categorias():
    """Migra categorias do banco origem para destino"""
    print("\n" + "=" * 70)
    print("📂 MIGRANDO CATEGORIAS...")
    print("=" * 70)
    
    session_origem = SessionOrigem()
    session_destino = SessionDestino()
    
    try:
        meta_origem = MetaData()
        meta_origem.reflect(bind=engine_origem)
        tbl_categorias_origem = meta_origem.tables['categorias']
        
        meta_destino = MetaData()
        meta_destino.reflect(bind=engine_destino)
        tbl_categorias_destino = meta_destino.tables['categorias']
        
        stmt = select(tbl_categorias_origem)
        categorias = session_origem.execute(stmt).fetchall()
        
        print(f"✅ Encontradas {len(categorias)} categorias na origem")
        
        mapa_ids = {}
        migradas = 0
        existentes = 0
        
        for cat in categorias:
            stmt_check = select(tbl_categorias_destino).where(
                tbl_categorias_destino.c.nome == cat.nome
            )
            existente = session_destino.execute(stmt_check).first()
            
            if existente:
                mapa_ids[cat.id] = existente.id
                existentes += 1
            else:
                novo_registro = {
                    'nome': cat.nome,
                    'tipo': getattr(cat, 'tipo_operacao', 'D') if hasattr(cat, 'tipo_operacao') else 'D'
                }
                
                if hasattr(cat, 'instituicao'):
                    novo_registro['instituicao'] = cat.instituicao
                if hasattr(cat, 'fonte_paga'):
                    novo_registro['fonte_paga'] = cat.fonte_paga
                
                result = session_destino.execute(
                    insert(tbl_categorias_destino).values(**novo_registro)
                )
                session_destino.commit()
                
                stmt_new_id = select(tbl_categorias_destino).where(
                    tbl_categorias_destino.c.nome == cat.nome
                )
                nova_cat = session_destino.execute(stmt_new_id).first()
                mapa_ids[cat.id] = nova_cat.id
                migradas += 1
        
        print(f"📊 RESUMO CATEGORIAS:")
        print(f"   Total: {len(categorias)} | Migradas: {migradas} | Já existiam: {existentes}")
        
        return mapa_ids
        
    except Exception as e:
        session_destino.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        session_origem.close()
        session_destino.close()

def migrar_pagamentos(mapa_ids_categorias, nome_tabela_origem):
    """Migra pagamentos do banco origem para destino"""
    print("\n" + "=" * 70)
    print(f"💰 MIGRANDO PAGAMENTOS (tabela: {nome_tabela_origem})...")
    print("=" * 70)
    
    session_origem = SessionOrigem()
    session_destino = SessionDestino()
    
    try:
        meta_origem = MetaData()
        meta_origem.reflect(bind=engine_origem)
        tbl_pagamentos_origem = meta_origem.tables[nome_tabela_origem]
        
        colunas_origem = [c.name for c in tbl_pagamentos_origem.columns]
        print(f"📋 Colunas na tabela ORIGEM: {colunas_origem}")
        
        meta_destino = MetaData()
        meta_destino.reflect(bind=engine_destino)
        tbl_pagamentos_destino = meta_destino.tables['pagamentos']
        
        colunas_destino = [c.name for c in tbl_pagamentos_destino.columns]
        print(f"📋 Colunas na tabela DESTINO: {colunas_destino}")
        
        stmt = select(tbl_pagamentos_origem)
        pagamentos = session_origem.execute(stmt).fetchall()
        
        print(f"✅ Encontrados {len(pagamentos)} pagamentos na origem")
        
        if len(pagamentos) == 0:
            print("⚠️  Nenhum pagamento para migrar!")
            return {}, 0
        
        migrados = 0
        erros = 0
        alertas_parcela = 0
        
        # Mapeamento: cod_origem -> cod_destino
        mapa_ids_pagamentos = {}
        
        for i, pag in enumerate(pagamentos, 1):
            try:
                cod_origem = pag.cod if hasattr(pag, 'cod') else pag.id if hasattr(pag, 'id') else None
                conta_nome = getattr(pag, 'conta', 'N/A')
                
                print(f"\n  [{i}/{len(pagamentos)}] cod={cod_origem} - {conta_nome}")
                
                if i == 1:
                    print(f"    Colunas disponíveis: {list(pag._mapping.keys())}")
                
                tipo_rd = 'D'
                if hasattr(pag, 'receita_despesa') and pag.receita_despesa:
                    tipo_rd = pag.receita_despesa
                elif hasattr(pag, 'tipo_operacao'):
                    tipo_rd = pag.tipo_operacao
                
                categoria_id_destino = None
                if hasattr(pag, 'categoria_id') and pag.categoria_id:
                    categoria_id_destino = mapa_ids_categorias.get(pag.categoria_id)
                
                parcela_original = getattr(pag, 'parcela', '') or ''
                parcela_ajustada = ajustar_parcela(parcela_original)
                
                if parcela_original != parcela_ajustada:
                    alertas_parcela += 1
                    print(f"    ⚠️  Parcela ajustada: '{parcela_original}' -> '{parcela_ajustada}'")
                
                novo_pagamento = {}
                
                if hasattr(pag, 'mes_ano'):
                    novo_pagamento['mes_ano'] = str(pag.mes_ano or '')[:10]
                if hasattr(pag, 'conta'):
                    novo_pagamento['conta'] = str(pag.conta or '')[:100]
                if hasattr(pag, 'instituicao'):
                    novo_pagamento['instituicao'] = str(pag.instituicao or '')[:50]
                if hasattr(pag, 'fonte_paga'):
                    novo_pagamento['fonte_paga'] = str(pag.fonte_paga or '')[:50]
                if hasattr(pag, 'data_venc'):
                    novo_pagamento['data_venc'] = str(pag.data_venc or '')[:20]
                if hasattr(pag, 'data_pago'):
                    novo_pagamento['data_pago'] = str(pag.data_pago or '')[:20]
                if hasattr(pag, 'valor_pagar'):
                    novo_pagamento['valor_pagar'] = float(pag.valor_pagar or 0)
                if hasattr(pag, 'valor_pago'):
                    novo_pagamento['valor_pago'] = float(pag.valor_pago or 0)
                elif hasattr(pag, 'val_paga'):
                    novo_pagamento['valor_pago'] = float(pag.val_paga or 0)
                
                novo_pagamento['parcela'] = parcela_ajustada
                
                if hasattr(pag, 'observacao'):
                    obs = pag.observacao or ''
                    if len(obs) > 500:
                        obs = obs[:500]
                    novo_pagamento['observacao'] = str(obs)
                
                novo_pagamento['receita_despesa'] = tipo_rd
                novo_pagamento['categoria_id'] = categoria_id_destino
                
                print(f"    📝 Inserindo: parcela='{parcela_ajustada}'")
                
                result = session_destino.execute(
                    insert(tbl_pagamentos_destino).values(**novo_pagamento)
                )
                session_destino.commit()
                
                # Pega o ID gerado no destino
                cod_destino = result.inserted_primary_key[0]
                mapa_ids_pagamentos[cod_origem] = cod_destino
                
                migrados += 1
                print(f"    ✅ Migrado com sucesso! (ID destino: {cod_destino})")
                
                if migrados % 50 == 0:
                    print(f"  ⏳ Progresso: {migrados}/{len(pagamentos)}...")
                    
            except Exception as e:
                erros += 1
                print(f"    ❌ Erro: {e}")
                import traceback
                traceback.print_exc()
                session_destino.rollback()
                continue
        
        print(f"\n📊 RESUMO PAGAMENTOS:")
        print(f"   Total: {len(pagamentos)}")
        print(f"   Migrados: {migrados}")
        print(f"   Erros: {erros}")
        print(f"   Parcelas ajustadas: {alertas_parcela}")
        
        return mapa_ids_pagamentos, migrados
        
    except Exception as e:
        session_destino.rollback()
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session_origem.close()
        session_destino.close()

def ajustar_parcela(valor_parcela):
    """Ajusta o valor da parcela para caber no campo de destino (varchar(2))"""
    if not valor_parcela:
        return ''
    
    valor_parcela = str(valor_parcela).strip()
    
    if '/' in valor_parcela:
        partes = valor_parcela.split('/')
        if len(partes) >= 1:
            return partes[0].strip()[:2]
    
    return valor_parcela[:2]


def migrar_documentos(mapa_ids_pagamentos):
    """Migra documentos_pagamento do banco origem para destino"""
    print("\n" + "=" * 70)
    print("📎 MIGRANDO DOCUMENTOS (documentos_pagamento)...")
    print("=" * 70)
    
    session_origem = SessionOrigem()
    session_destino = SessionDestino()
    
    try:
        meta_origem = MetaData()
        meta_origem.reflect(bind=engine_origem)
        
        if 'documentos_pagamento' not in meta_origem.tables:
            print("⚠️  Tabela 'documentos_pagamento' não encontrada na origem!")
            return 0
        
        tbl_documentos_origem = meta_origem.tables['documentos_pagamento']
        
        meta_destino = MetaData()
        meta_destino.reflect(bind=engine_destino)
        tbl_documentos_destino = meta_destino.tables['documentos_pagamento']
        
        # Mostra colunas
        colunas_origem = [c.name for c in tbl_documentos_origem.columns]
        colunas_destino = [c.name for c in tbl_documentos_destino.columns]
        print(f"📋 Colunas ORIGEM: {colunas_origem}")
        print(f"📋 Colunas DESTINO: {colunas_destino}")
        
        stmt = select(tbl_documentos_origem)
        documentos = session_origem.execute(stmt).fetchall()
        
        print(f"✅ Encontrados {len(documentos)} documentos na origem")
        
        if len(documentos) == 0:
            print("⚠️  Nenhum documento para migrar!")
            return 0
        
        migrados = 0
        erros = 0
        sem_pagamento = 0
        
        for i, doc in enumerate(documentos, 1):
            try:
                print(f"\n  [{i}/{len(documentos)}] ID={doc.id} - {doc.nome_arquivo}")
                
                pagamento_id_origem = doc.pagamento_id
                pagamento_id_destino = mapa_ids_pagamentos.get(pagamento_id_origem)
                
                if not pagamento_id_destino:
                    sem_pagamento += 1
                    print(f"    ⚠️  Pagamento ID {pagamento_id_origem} não encontrado - PULANDO")
                    continue
                
                print(f"    🔗 Pagamento: {pagamento_id_origem} (origem) -> {pagamento_id_destino} (destino)")
                
                # Prepara dados para inserção - SEM data_upload!
                novo_documento = {
                    'pagamento_id': pagamento_id_destino,
                    'nome_arquivo': str(doc.nome_arquivo or '')[:255],
                    'tipo_mime': str(doc.tipo_mime or 'application/pdf')[:100],
                    'conteudo': doc.conteudo,  # Dados binários do arquivo
                    # ❌ REMOVIDO: data_upload (não existe na tabela destino)
                }
                
                tamanho_bytes = len(novo_documento['conteudo']) if novo_documento['conteudo'] else 0
                print(f"    📝 Inserindo: {novo_documento['nome_arquivo']} ({tamanho_bytes} bytes)")
                
                session_destino.execute(
                    insert(tbl_documentos_destino).values(**novo_documento)
                )
                session_destino.commit()
                
                migrados += 1
                print(f"    ✅ Documento migrado com sucesso!")
                
                if migrados % 10 == 0:
                    print(f"  ⏳ Progresso: {migrados}/{len(documentos)}...")
                    
            except Exception as e:
                erros += 1
                print(f"    ❌ Erro: {e}")
                import traceback
                traceback.print_exc()
                session_destino.rollback()
                continue
        
        print(f"\n📊 RESUMO DOCUMENTOS:")
        print(f"   Total encontrados: {len(documentos)}")
        print(f"   Migrados: {migrados}")
        print(f"   Erros: {erros}")
        print(f"   Sem pagamento vinculado: {sem_pagamento}")
        
        return migrados
        
    except Exception as e:
        session_destino.rollback()
        print(f"❌ Erro na migração de documentos: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session_origem.close()
        session_destino.close()

def main():
    try:
        # 1. Migra categorias primeiro
        mapa_ids_categorias = migrar_categorias()
        
        # 2. Migra pagamentos (e retorna mapeamento de IDs)
        mapa_ids_pagamentos, total_pagamentos = migrar_pagamentos(mapa_ids_categorias, tabela_pagamentos_origem)
        
        # 3. Migra documentos (depende dos pagamentos)
        if total_pagamentos > 0:
            migrar_documentos(mapa_ids_pagamentos)
        else:
            print("\n⚠️  Pulando migração de documentos (nenhum pagamento migrado)")
        
        print("\n" + "=" * 70)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ MIGRAÇÃO FALHOU: {e}")
        print("=" * 70)
        raise

if __name__ == "__main__":
    main()