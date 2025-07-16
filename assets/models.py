
"""
models.py
---------
Modelos ORM para as tabelas do banco de dados: Ativo, Historico, PrecoAtual, AnalyticsCache.
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class AnalyticsCache(Base):
    """
    Modelo para cache de destaques de analytics (maior rentabilidade, tendência, etc).
    """
    __tablename__ = 'analytics_cache'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo = Column(String, nullable=False)  # Ex: maior_rent_12m, menor_rent_mm3m, maior_tend_1m
    ticker = Column(String, nullable=True)
    valor = Column(Float, nullable=True)
    atualizado_em = Column(DateTime, default=datetime.datetime.now)




# Tabela para preço atual
class PrecoAtual(Base):
    """
    Modelo para preço atual do ativo.
    """
    __tablename__ = 'precos_atualizados'
    id = Column(Integer, primary_key=True)
    ativo_id = Column(Integer, ForeignKey('ativos.id'))
    preco = Column(Float, nullable=False)
    variacao = Column(Float)
    variacao_percentual = Column(Float)
    atualizado_em = Column(DateTime)
    ativo = relationship('Ativo')

# Exemplo de tabela de ativos
class Ativo(Base):
    """
    Modelo para ativos financeiros cadastrados.
    """
    __tablename__ = 'ativos'
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, nullable=False)
    historicos = relationship('Historico', back_populates='ativo')

# Exemplo de tabela de histórico de preços
class Historico(Base):
    """
    Modelo para histórico de preços de um ativo.
    """
    __tablename__ = 'historicos'
    id = Column(Integer, primary_key=True)
    ativo_id = Column(Integer, ForeignKey('ativos.id'))
    data = Column(Date, nullable=False)
    preco_abertura = Column(Float)
    preco_fechamento = Column(Float)
    maximo = Column(Float)
    minimo = Column(Float)
    volume = Column(Float)
    ativo = relationship('Ativo', back_populates='historicos')

