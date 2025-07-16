

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Exemplo de tabela de ativos
class Ativo(Base):
    __tablename__ = 'ativos'
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, nullable=False)
    nome = Column(String)
    historicos = relationship('Historico', back_populates='ativo')

# Exemplo de tabela de histórico de preços
class Historico(Base):
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

