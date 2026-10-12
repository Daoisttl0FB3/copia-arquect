from app.web import app


def test_health_devuelve_estado_ok():
    cliente = app.test_client()

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "service": "enagenda-api",
        "status": "ok",
    }


def test_metrics_expone_metricas_http():
    cliente = app.test_client()

    cliente.get("/health")
    respuesta = cliente.get(
        "/metrics",
        headers={
            "Authorization": "Bearer token-local-para-pruebas-2026"
        }
    )
    datos = respuesta.get_json()

    assert respuesta.status_code == 200
    assert "http_requests_total" in datos
    assert datos["http_requests_total"] >= 1
    assert "http_requests_by_path" in datos
    assert "http_responses_by_status" in datos
    assert "/health" in datos["http_requests_by_path"]

def test_metricas_no_exponen_tokens_de_invitacion():
    import app.web as web

    cliente = app.test_client()
    token = "token-privado-de-prueba-98765"
    cliente.get(f"/invitacion/{token}")
    cliente.get(f"/api/v1/invitaciones/{token}")

    respuesta = cliente.get(
        "/metrics",
        headers={
            "Authorization": "Bearer token-local-para-pruebas-2026"
        }
    )
    assert respuesta.status_code == 200
    contenido = respuesta.get_data(as_text=True)
    assert token not in contenido
    assert "/invitacion/<token>" in respuesta.get_json()["http_requests_by_path"]
    assert "/api/v1/invitaciones/<token>" in respuesta.get_json()["http_requests_by_path"]
