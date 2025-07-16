

from assets.config_assets import ATIVOS
from assets.scrapping import Scraper

scraper = Scraper(headless=True)

scraper.coletar_e_salvar_historico_ativos(ATIVOS, periodos=['5D', '3M', 'YTD'])