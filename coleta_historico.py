
import os

from assets.config_assets import ATIVOS
from assets.scrapping import Scraper

ATIVOS = [ATIVOS[0]]

scraper = Scraper(headless=True)
scraper.coletar_historico_ativos(ATIVOS, periodos=['5D', '3M', 'YTD'])