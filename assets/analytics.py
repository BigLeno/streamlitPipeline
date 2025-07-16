
"""
analytics.py
------------
Funções de análise financeira: maior rentabilidade, menor rentabilidade (MM3M), maior tendência de crescimento.
"""

import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from assets.database import listar_historicos, listar_ativos

def ativo_maior_rentabilidade_12m():
    """
    Retorna o ativo com maior rentabilidade nos últimos 12 meses.
    Returns:
        tuple: (ticker, rentabilidade)
    """
    """Retorna o ativo com maior rentabilidade nos últimos 12 meses."""
    hoje = datetime.date.today()
    doze_meses_atras = hoje - datetime.timedelta(days=365)
    melhor_ativo = None
    melhor_rent = float('-inf')
    for ativo in listar_ativos():
        historicos = [h for h in listar_historicos(ativo.ticker) if h.data >= doze_meses_atras and h.preco_fechamento]
        if len(historicos) < 2:
            continue
        historicos.sort(key=lambda h: h.data)
        preco_ini = historicos[0].preco_fechamento
        preco_fim = historicos[-1].preco_fechamento
        if preco_ini and preco_fim and preco_ini > 0:
            rent = (preco_fim - preco_ini) / preco_ini
            if rent > melhor_rent:
                melhor_rent = rent
                melhor_ativo = ativo.ticker
    return melhor_ativo, melhor_rent

def ativo_menor_rentabilidade_mm3m():
    """
    Retorna o ativo com menor rentabilidade pela média móvel de 3 meses.
    Returns:
        tuple: (ticker, rentabilidade)
    """
    """Retorna o ativo com menor rentabilidade pela média móvel de 3 meses."""
    hoje = datetime.date.today()
    tres_meses_atras = hoje - datetime.timedelta(days=90)
    pior_ativo = None
    pior_rent = float('inf')
    for ativo in listar_ativos():
        historicos = [h for h in listar_historicos(ativo.ticker) if h.data >= tres_meses_atras and h.preco_fechamento]
        if len(historicos) < 2:
            continue
        historicos.sort(key=lambda h: h.data)
        precos = [h.preco_fechamento for h in historicos]
        mm3 = pd.Series(precos).rolling(window=3).mean().dropna()
        if len(mm3) == 0:
            continue
        rent = (mm3.iloc[-1] - mm3.iloc[0]) / mm3.iloc[0] if mm3.iloc[0] else None
        if rent is not None and rent < pior_rent:
            pior_rent = rent
            pior_ativo = ativo.ticker
    return pior_ativo, pior_rent

def ativo_maior_tendencia_crescimento_1m():
    """
    Retorna o ativo com maior tendência de crescimento para o próximo mês (regressão linear).
    Returns:
        tuple: (ticker, tendencia)
    """
    """Retorna o ativo com maior tendência de crescimento para o próximo mês (regressão linear)."""
    hoje = datetime.date.today()
    tres_meses_atras = hoje - datetime.timedelta(days=90)
    melhor_ativo = None
    maior_tend = float('-inf')
    for ativo in listar_ativos():
        historicos = [h for h in listar_historicos(ativo.ticker) if h.data >= tres_meses_atras and h.preco_fechamento]
        if len(historicos) < 10:
            continue
        historicos.sort(key=lambda h: h.data)
        datas = np.array([(h.data - tres_meses_atras).days for h in historicos]).reshape(-1, 1)
        precos = np.array([h.preco_fechamento for h in historicos])
        if len(datas) < 2:
            continue
        reg = LinearRegression().fit(datas, precos)
        tendencia = reg.coef_[0]
        if tendencia > maior_tend:
            maior_tend = tendencia
            melhor_ativo = ativo.ticker
    return melhor_ativo, maior_tend
