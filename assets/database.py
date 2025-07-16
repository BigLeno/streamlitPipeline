from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from assets.models import Base, Ativo, Historico
import datetime

DATABASE_URL = 'sqlite:///streamlit_pipeline.db'
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def criar_banco():
    Base.metadata.create_all(engine)

def inserir_ativo(ticker: str, nome: str = None):
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        ativo = Ativo(ticker=ticker, nome=nome)
        session.add(ativo)
        session.commit()
    session.close()

def listar_ativos():
    session = SessionLocal()
    ativos = session.query(Ativo).all()
    session.close()
    return ativos

def inserir_historico(ticker: str, data: datetime.date, preco_abertura: float, preco_fechamento: float, maximo: float, minimo: float, volume: float):
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
    session = SessionLocal()
    ativo = session.query(Ativo).filter_by(ticker=ticker).first()
    if not ativo:
        session.close()
        return []
    historicos = session.query(Historico).filter_by(ativo_id=ativo.id).all()
    session.close()
    return historicos
