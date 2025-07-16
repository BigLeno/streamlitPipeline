import os
from assets.config_assets import ATIVOS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from assets.scrapping import scrape_historical_data

# Pasta para salvar os históricos
os.makedirs('historicos', exist_ok=True)

ATIVOS = [ATIVOS[0]]

from assets.scrapping import coletar_historico_ativos

# Exemplo de uso do método migrado:
coletar_historico_ativos(ATIVOS)
