import re

from html.parser import HTMLParser

import pytest

import app.web as web
from app.web import app


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    web.invitaciones_consultadas_total = 0
    return app.test_client()


class ExtractorCSRF(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return

        atributos = dict(attrs)

        if atributos.get("name") == "csrf_token":
            self.token = atributos.get("value")



def obtener_token(cliente):
    """Crea una invitación de prueba y devuelve su token."""

    # Obtener CSRF desde el formulario principal
    pagina = cliente.get("/")
    assert pagina.status_code == 200

    extractor = ExtractorCSRF()
    extractor.feed(pagina.get_data(as_text=True))

    assert extractor.token is not None

    respuesta = cliente.post(
        "/crear-invitaciones",
        data={
            "csrf_token": extractor.token,
            "fecha_limite": "2099-12-31",
            "hora": "11",
            "minuto": "30",
            "periodo": "PM",
            "cantidad_invitados": "1",
            "nombre_1": "Invitado de prueba",
            "correo_1": "invitado@ejemplo.com",
        },
    )

    assert respuesta.status_code == 200

    contenido = respuesta.get_data(as_text=True)

    coincidencia = re.search(
        r"/invitacion/([^\"'<>\s]+)",
        contenido,
    )

    assert coincidencia is not None

    return coincidencia.group(1)



def test_get_invitacion_devuelve_datos_del_contrato(cliente):
    token = obtener_token(cliente)

    respuesta = cliente.get(
        f"/api/v1/invitaciones/{token}"
    )

    assert respuesta.status_code == 200

    datos = respuesta.get_json()

    assert datos["token"] == token
    assert "destinatario" in datos
    assert "estado" in datos
    assert "fecha_limite_respuesta" in datos


def test_post_invitacion_confirma_asistencia(cliente):
    token = obtener_token(cliente)

    respuesta = cliente.post(
        f"/api/v1/invitaciones/{token}",
        json={
            "estado": "confirmado",
        },
    )

    assert respuesta.status_code == 200

    datos = respuesta.get_json()

    assert datos["token"] == token
    assert datos["estado"] == "Confirmimado" or (
        datos["estado"] == "Confirmado"
    )


def test_token_inexistente_devuelve_404(cliente):
    respuesta = cliente.post(
        "/api/v1/invitaciones/token-inexistente",
        json={
            "estado": "confirmado",
        },
    )

    assert respuesta.status_code == 404

    datos = respuesta.get_json()

    assert datos == {
        "error": "Invitación no encontrada.",
    }


def test_metricas_aumentan_al_consultar_invitacion(cliente):

    headers = {
        "Authorization": "Bearer token-local-para-pruebas-2026"
    }

    respuesta_inicial = cliente.get(
        "/metrics",
        headers=headers
    )

    assert respuesta_inicial.status_code == 200

    metricas_iniciales = respuesta_inicial.get_json()

    assert metricas_iniciales["metric"] == (
        "enagenda_invitaciones_consultadas_total"
    )

    assert metricas_iniciales["value"] == 0

    token = obtener_token(cliente)

    respuesta = cliente.get(
        f"/api/v1/invitaciones/{token}"
    )

    assert respuesta.status_code == 200

    respuesta_final = cliente.get(
        "/metrics",
        headers=headers
    )

    assert respuesta_final.status_code == 200

    metricas_finales = respuesta_final.get_json()

    assert metricas_finales["metric"] == (
        "enagenda_invitaciones_consultadas_total"
    )

    assert metricas_finales["value"] == 1