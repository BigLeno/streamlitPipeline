
"""
database.py
-----------
Módulo de persistência e consulta ao banco de dados para ativos, históricos, preços e analytics cache.
"""

import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from assets.models import Base, Ativo, Historico, PrecoAtual

DATABASE_URL = 'sqlite:///streamlit_pipeline.db'
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def criar_banco():
    """
    Cria as tabelas do banco de dados, se não existirem.
    """
    Base.metadata.create_all(engine)

def inserir_ativo(ticker: str):
    """
    Insere um novo ativo no banco, se não existir.
    Args:
        ticker (str): Código do ativo.
    """
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        ativo = Ativo(ticker=ticker)
        session.add(ativo)
        session.commit()
    session.close()

def listar_ativos():
    """
    Lista todos os ativos cadastrados.
    Returns:
        list: Lista de objetos Ativo.
    """
    session = SessionLocal()
    ativos = session.query(Ativo).all()
    session.close()
    return ativos

def inserir_historico(ticker: str, data: datetime.date, preco_abertura: float, preco_fechamento: float, maximo: float, minimo: float, volume: float):
    """
    Insere um novo histórico de preço para um ativo.
    """
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        ativo = Ativo(ticker=ticker)
        session.add(ativo)
        session.commit()
    # Verifica duplicidade (ticker, data)
    historico_existente = session.query(Historico).filter_by(ativo_id=ativo.id, data=data).first()
    if not historico_existente:
        historico = Historico(
            ativo_id=ativo.id,
            data=data,
            preco_abertura=preco_abertura,
            preco_fechamento=preco_fechamento,
            maximo=maximo,
            minimo=minimo,
            volume=volume
        )
        session.add(historico)
        session.commit()
    session.close()

def listar_historicos(ticker: str):
    """
    Lista todos os históricos de um ativo.
    Returns:
        list: Lista de objetos Historico.
    """
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        session.close()
        return []
    historicos = session.query(Historico).filter_by(ativo_id=ativo.id).all()
    session.close()
    return historicos

# Função para salvar preço atual
def salvar_preco_atual(ticker: str, preco: float, variacao: float = None, variacao_percentual: float = None, atualizado_em: datetime.datetime = None):
    """
    Salva ou atualiza o preço atual de um ativo.
    """
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        session.close()
        print(f"[salvar_preco_atual] Ativo não encontrado: {ticker}")
        return
    preco_obj = session.query(PrecoAtual).filter_by(ativo_id=ativo.id).order_by(PrecoAtual.atualizado_em.desc()).first()
    if not atualizado_em:
        atualizado_em = datetime.datetime.now()
    if preco_obj:
        preco_obj.preco = preco
        preco_obj.variacao = variacao
        preco_obj.variacao_percentual = variacao_percentual
        preco_obj.atualizado_em = atualizado_em
        print(f"[salvar_preco_atual] Atualizando preço: {ticker} -> {preco}")
    else:
        preco_obj = PrecoAtual(
            ativo_id=ativo.id,
            preco=preco,
            variacao=variacao,
            variacao_percentual=variacao_percentual,
            atualizado_em=atualizado_em
        )
        session.add(preco_obj)
        print(f"[salvar_preco_atual] Inserindo preço: {ticker} -> {preco}")
    session.commit()
    session.close()

# Função para consultar preço atual
def consultar_preco_atual(ticker: str):
    """
    Consulta o preço atual de um ativo.
    Returns:
        PrecoAtual|None: Objeto PrecoAtual ou None se não encontrado.
    """
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        session.close()
        print(f"[consultar_preco_atual] Ativo não encontrado: {ticker}")
        return None
    preco_obj = session.query(PrecoAtual).filter_by(ativo_id=ativo.id).order_by(PrecoAtual.atualizado_em.desc()).first()
    session.close()
    if preco_obj:
        print(f"[consultar_preco_atual] Preço encontrado: {ticker} -> {preco_obj.preco}")
    else:
        print(f"[consultar_preco_atual] Nenhum preço encontrado para: {ticker}")
    return preco_obj

# === Analytics Cache ===
from assets.analytics import ativo_maior_rentabilidade_12m, ativo_menor_rentabilidade_mm3m, ativo_maior_tendencia_crescimento_1m
from assets.models import AnalyticsCache

def atualizar_analytics_cache() -> None:
    """
    Atualiza o cache dos destaques de analytics no banco de dados.
    Remove entradas antigas e salva os novos destaques calculados.
    """
    """
    Atualiza o cache dos destaques de analytics no banco de dados.
    Remove entradas antigas e salva os novos destaques calculados.
    """
    session = SessionLocal()
    session.query(AnalyticsCache).delete()
    ativo1, rent1 = ativo_maior_rentabilidade_12m()
    ativo2, rent2 = ativo_menor_rentabilidade_mm3m()
    ativo3, tend3 = ativo_maior_tendencia_crescimento_1m()
    session.add(AnalyticsCache(tipo='maior_rent_12m', ticker=ativo1, valor=rent1, atualizado_em=datetime.datetime.now()))
    session.add(AnalyticsCache(tipo='menor_rent_mm3m', ticker=ativo2, valor=rent2, atualizado_em=datetime.datetime.now()))
    session.add(AnalyticsCache(tipo='maior_tend_1m', ticker=ativo3, valor=tend3, atualizado_em=datetime.datetime.now()))
    session.commit()
    session.close()

def consultar_analytics_cache() -> list:
    """
    Consulta todos os registros de analytics cache do banco de dados.
    Returns:
        list: Lista de objetos AnalyticsCache.
    """
    """
    Consulta todos os registros de analytics cache do banco de dados.
    Returns:
        list: Lista de objetos AnalyticsCache.
    """
    session = SessionLocal()
    dados = session.query(AnalyticsCache).all()
    session.close()
    return dados
