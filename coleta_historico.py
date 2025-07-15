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

def main():
    options = Options()
    # REMOVA o modo headless para debug visual
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.set_window_size(1150, 1000)
    for ticker in ATIVOS:
        print(f"Coletando histórico de {ticker}...")
        try:
            df = scrape_historical_data(driver, ticker, days=365)
            if df.empty:
                print(f"[ERRO] DataFrame vazio para {ticker}. Verifique se a tabela carregou corretamente.")
            else:
                df.to_csv(f"historicos/historical_{ticker}.csv", index=False)
                print(f"Histórico salvo em historicos/historical_{ticker}.csv")
        except Exception as e:
            print(f"[ERRO] Não foi possível coletar histórico de {ticker}: {e}")
    input("Pressione Enter para fechar o navegador...")
    driver.quit()

if __name__ == "__main__":
    main()
