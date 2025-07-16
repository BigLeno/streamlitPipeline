
import os

from assets.config_assets import ATIVOS
from assets.scrapping import Scraper

if os.path.exists("historicos"):
    for file in os.listdir("historicos"):
        os.remove(os.path.join("historicos", file))

ATIVOS = [ATIVOS[0]]

scraper = Scraper(headless=True)
scraper.coletar_historico_ativos(ATIVOS)