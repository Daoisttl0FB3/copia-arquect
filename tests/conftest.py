import os

import pytest


@pytest.fixture(autouse=True)
def configurar_token_metricas(monkeypatch):
    monkeypatch.setenv(
        "ENAGENDA_METRICS_TOKEN",
        "token-local-para-pruebas-2026"
    )