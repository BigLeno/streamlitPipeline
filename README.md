# Dashboard Financeiro Interativo

Este projeto é um dashboard financeiro robusto, interativo e modular, desenvolvido em Python com Streamlit, para análise e acompanhamento de ativos do mercado financeiro brasileiro e internacional.

## Funcionalidades
- **Extração de dados**: Scraping automatizado e fallback para Yahoo Finance (yfinance)
- **Banco de dados**: Persistência local via SQLite (pronto para migração para SQL Server)
- **Gestão de portfólio**: Cadastro, remoção e atualização automática de ativos
- **Atualização automática de preços**: Thread em background
- **Indicador de mercado aberto/fechado (EUA)**: Com tempo até abertura/fechamento
- **Gráficos interativos**: Todos os gráficos com Plotly
- **Métricas e análises avançadas**:
  - Retorno acumulado
  - Volatilidade
  - Drawdown
  - Médias móveis
  - RSI e MACD
  - Correlação entre ativos (heatmap)
  - Heatmap de retornos mensais
- **Destaques do mercado**: Métricas rápidas dos melhores e piores ativos
- **Interface profissional**: Layout limpo, responsivo e informativo

## Tecnologias Utilizadas
- Python 3.10+
- Streamlit
- Pandas
- Plotly
- SQLAlchemy
- SQLite (padrão, mas adaptável para SQL Server)
- yfinance
- Selenium (scraping)
- pytz

## Instalação

1. **Clone o repositório:**

```bash
git clone https://github.com/BigLeno/streamlitPipeline.git
cd streamlitPipeline
```

2. **Crie e ative um ambiente virtual (recomendado):**

No Windows:
```bash
python -m venv env
.\env\Scripts\activate
```
No Linux/Mac:
```bash
python3 -m venv env
source env/bin/activate
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **(Opcional) Instale o Chrome para uso do Selenium:**
- Baixe o Chrome : https://www.google.com/intl/pt-BR/chrome/

## Como Rodar

```bash
streamlit run streamlit_app.py
```

O dashboard abrirá automaticamente no navegador padrão.

## Estrutura do Projeto
- `streamlit_app.py`: Módulo principal do dashboard
- `assets/`: Módulos utilitários (scraping, banco, analytics, etc)
- `requirements.txt`: Dependências do projeto
- `historicos/`: Arquivos de históricos baixados

## Métodos e Lógica
- **Scraping**: Coleta de preços e históricos via Selenium, com fallback automático para yfinance em caso de erro
- **Banco de dados**: ORM SQLAlchemy, pronto para migrar para SQL Server (basta trocar a string de conexão)
- **Atualização automática**: Thread para atualização periódica dos preços
- **Análises**: Todas as métricas e gráficos são calculados em tempo real a partir dos dados históricos
- **Interface**: Streamlit + Plotly para visualização interativa e responsiva

## Observações
- Para usar SQL Server, basta instalar o driver (ex: `pyodbc`) e alterar a string de conexão no módulo de banco de dados.
- O scraping pode exigir o ChromeDriver instalado e compatível com o navegador.
- O dashboard é modular e fácil de expandir com novas análises ou integrações.

## Autor
BigLeno

---
Dúvidas ou sugestões? Abra uma issue ou entre em contato!
