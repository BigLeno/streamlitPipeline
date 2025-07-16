

# Teste dos insights de analytics
from assets.analytics import (
    ativo_maior_rentabilidade_12m,
    ativo_menor_rentabilidade_mm3m,
    ativo_maior_tendencia_crescimento_1m
)

if __name__ == "__main__":
    print("--- Analytics obrigatórios ---")
    ativo, rent = ativo_maior_rentabilidade_12m()
    print(f"Ativo com maior rentabilidade (12 meses): {ativo} ({rent:.2%} de retorno)")

    ativo, rent = ativo_menor_rentabilidade_mm3m()
    print(f"Ativo com menor rentabilidade (média móvel 3 meses): {ativo} ({rent:.2%} de retorno)")

    ativo, tendencia = ativo_maior_tendencia_crescimento_1m()
    print(f"Ativo com maior tendência de crescimento (próximo mês): {ativo} (coeficiente: {tendencia:.4f})")
