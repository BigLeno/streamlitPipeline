import datetime
from assets.database import listar_ativos, listar_historicos, SessionLocal
from assets.analytics import ativo_maior_rentabilidade_12m, ativo_menor_rentabilidade_mm3m, ativo_maior_tendencia_crescimento_1m
from assets.models import AnalyticsCache

def atualizar_analytics_cache():
    session = SessionLocal()
    # Limpa cache anterior
    session.query(AnalyticsCache).delete()
    # Calcula e salva os destaques
    ativo1, rent1 = ativo_maior_rentabilidade_12m()
    ativo2, rent2 = ativo_menor_rentabilidade_mm3m()
    ativo3, tend3 = ativo_maior_tendencia_crescimento_1m()
    session.add(AnalyticsCache(tipo='maior_rent_12m', ticker=ativo1, valor=rent1, atualizado_em=datetime.datetime.now()))
    session.add(AnalyticsCache(tipo='menor_rent_mm3m', ticker=ativo2, valor=rent2, atualizado_em=datetime.datetime.now()))
    session.add(AnalyticsCache(tipo='maior_tend_1m', ticker=ativo3, valor=tend3, atualizado_em=datetime.datetime.now()))
    session.commit()
    session.close()

def consultar_analytics_cache():
    session = SessionLocal()
    dados = session.query(AnalyticsCache).all()
    session.close()
    return dados
