
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

# Caminho do banco SQLite (será criado automaticamente)
DATABASE_URL = 'sqlite:///streamlit_pipeline.db'

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
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

# Função para criar as tabelas no banco
def criar_banco():
    Base.metadata.create_all(engine)

# Exemplo de inserção de ativo
def inserir_ativo(ticker: str, nome: str = None):
    session = SessionLocal()
    # Só insere se não existir
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        ativo = Ativo(ticker=ticker, nome=nome)
        session.add(ativo)
        session.commit()
    session.close()

# Exemplo de consulta de ativos
def listar_ativos():
    session = SessionLocal()
    ativos = session.query(Ativo).all()
    session.close()
    return ativos

# Exemplo de inserção de histórico
def inserir_historico(ticker: str, data: datetime.date, preco_abertura: float, preco_fechamento: float, maximo: float, minimo: float, volume: float):
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        ativo = Ativo(ticker=ticker)
        session.add(ativo)
        session.commit()
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

# Exemplo de consulta de históricos por ticker
def listar_historicos(ticker: str):
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        session.close()
        return []
    historicos = session.query(Historico).filter_by(ativo_id=ativo.id).all()
    session.close()
    return historicos
