from app.web import app


def test_health_devuelve_estado_ok():
    cliente = app.test_client()

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "service": "enagenda-api",
        "status": "ok",
    }

