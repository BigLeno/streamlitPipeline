"""Tira uma captura de tela do dashboard em execução. Uso: python scripts/screenshot.py URL ARQUIVO"""

import sys
import time

from playwright.sync_api import sync_playwright


def main(url: str, output: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=2)
        for _ in range(60):
            try:
                page.goto(url)
                break
            except Exception:
                time.sleep(1)
        page.wait_for_selector("text=Destaques da carteira", timeout=120_000)
        page.wait_for_selector(".js-plotly-plot", timeout=60_000)
        time.sleep(3)
        page.screenshot(path=output, full_page=False)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
