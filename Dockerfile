# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas quando só o código muda.
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data \
    && chown app:app /app/data

COPY --chown=app:app .streamlit/ .streamlit/
COPY --chown=app:app dashboard/ dashboard/
COPY --chown=app:app streamlit_app.py .

USER app

ENV DATABASE_URL=sqlite:////app/data/dashboard.db \
    MARKET_DATA=yahoo
VOLUME ["/app/data"]
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)"]

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
