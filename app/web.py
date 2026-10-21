import os
import secrets
import sys
from datetime import datetime
from flask_wtf.csrf import CSRFProtect


from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)


# Permite importar el paquete src cuando ejecutamos:
# python app\web.py
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

from src.invitaciones.aplicacion.gestionar_invitacion import (
    GestionarInvitacion,
)
from src.invitaciones.dominio.invitaciones import EstadoInvitacion
from src.invitaciones.infraestructura.repositorio_memoria import (
    RepositorioInvitacionesMemoria,
)


app = Flask(__name__)

# Configuración de sesiones de usuario
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("FLASK_SECURE_COOKIES", "false").lower() == "true"
)
csrf = CSRFProtect(app)

# Repositorio en memoria para la interfaz.
repositorio = RepositorioInvitacionesMemoria()
gestionar_invitacion = GestionarInvitacion(repositorio)

# Métrica específica de consultas exitosas a invitaciones.
invitaciones_consultadas_total = 0

# Métricas HTTP generales en memoria.
http_requests_total = 0
http_requests_by_path = {}
http_responses_by_status = {}


@app.before_request
def registrar_peticion():
    """Registra cada petición HTTP para observabilidad local."""
    global http_requests_total

    # Evita que /metrics altere sus propias métricas.
    if request.path == "/metrics":
        return

    http_requests_total += 1

    # Usar la plantilla de Flask evita registrar tokens secretos.
    ruta = request.url_rule.rule if request.url_rule is not None else "<sin-ruta>"
    http_requests_by_path[ruta] = (
        http_requests_by_path.get(ruta, 0) + 1
    )


@app.after_request
def registrar_respuesta(response):
    """Registra el código de respuesta HTTP."""
    if request.path == "/metrics":
        return response

    codigo = str(response.status_code)

    http_responses_by_status[codigo] = (
        http_responses_by_status.get(codigo, 0) + 1
    )

    return response


@app.get("/health")
def health():
    """Indica que la API está disponible."""
    return jsonify(
        {
            "service": "enagenda-api",
            "status": "ok",
        }
    ), 200


@app.get("/metrics")
def metrics():
    """Expone métricas solo con un token de observabilidad configurado."""
    token_esperado = os.environ.get("ENAGENDA_METRICS_TOKEN", "")
    if not token_esperado:
        return jsonify({"error": "Métricas no configuradas"}), 503

    autorizacion = request.headers.get("Authorization", "")
    esquema, separador, token_recibido = autorizacion.partition(" ")
    if (not separador or esquema.lower() != "bearer"
            or not secrets.compare_digest(token_recibido, token_esperado)):
        return jsonify({"error": "No autorizado"}), 401

    return jsonify(
        {
            "metric": "enagenda_invitaciones_consultadas_total",
            "value": invitaciones_consultadas_total,
            "description": (
                "Total de consultas de invitaciones realizadas"
            ),
            "http_requests_total": http_requests_total,
            "http_requests_by_path": http_requests_by_path,
            "http_responses_by_status": http_responses_by_status,
        }
    ), 200


@app.get("/openapi.yaml")
def obtener_contrato_openapi():
    """Entrega el contrato OpenAPI de la aplicación."""
    ruta_contrato = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "api",
        "openapi.yaml",
    )

    return send_file(
        ruta_contrato,
        mimetype="application/yaml",
    )


@app.route("/", methods=["GET", "POST"])
def inicio():
    """Muestra el formulario inicial para crear invitaciones."""
    mensaje_error = None

    if request.method == "POST":
        fecha_limite = request.form.get(
            "fecha_limite",
            "",
        ).strip()

        hora = request.form.get(
            "hora",
            "",
        ).strip()

        minuto = request.form.get(
            "minuto",
            "",
        ).strip()

        periodo = request.form.get(
            "periodo",
            "",
        ).strip()

        cantidad = request.form.get(
            "cantidad_invitados",
            "",
        ).strip()

        if not fecha_limite:
            mensaje_error = "Debes seleccionar una fecha límite."

        elif not hora:
            mensaje_error = "Debes seleccionar una hora."

        elif minuto not in ("00", "30"):
            mensaje_error = "Los minutos deben ser 00 o 30."

        elif periodo not in ("AM", "PM"):
            mensaje_error = "Debes seleccionar a. m. o p. m."

        else:
            try:
                cantidad_invitados = int(cantidad)
                hora_numero = int(hora)

                if (
                    cantidad_invitados < 1
                    or cantidad_invitados > 200
                ):
                    mensaje_error = (
                        "La cantidad de invitados debe estar "
                        "entre 1 y 200."
                    )

                elif hora_numero < 1 or hora_numero > 12:
                    mensaje_error = (
                        "La hora seleccionada no es válida."
                    )

                else:
                    if periodo == "AM":
                        if hora_numero == 12:
                            hora_numero = 0
                    else:
                        if hora_numero != 12:
                            hora_numero += 12

                    fecha_limite_respuesta = datetime.strptime(
                        (
                            f"{fecha_limite} "
                            f"{hora_numero:02d}:{minuto}"
                        ),
                        "%Y-%m-%d %H:%M",
                    )

                    if fecha_limite_respuesta <= datetime.now():
                        mensaje_error = (
                            "La fecha y hora límite deben ser "
                            "posteriores a la fecha actual."
                        )

                    else:
                        return render_template(
                            "invitados.html",
                            cantidad_invitados=cantidad_invitados,
                            fecha_limite=fecha_limite,
                            hora=hora,
                            minuto=minuto,
                            periodo=periodo,
                        )

            except ValueError:
                mensaje_error = (
                    "Los datos ingresados no son válidos."
                )

    return render_template(
        "inicio.html",
        mensaje_error=mensaje_error,
    )


@app.post("/crear-invitaciones")
def crear_invitaciones():
    """Crea varias invitaciones usando una fecha límite global."""
    fecha_limite = request.form.get(
        "fecha_limite",
        "",
    ).strip()

    hora = request.form.get(
        "hora",
        "",
    ).strip()

    minuto = request.form.get(
        "minuto",
        "",
    ).strip()

    periodo = request.form.get(
        "periodo",
        "",
    ).strip()

    cantidad = request.form.get(
        "cantidad_invitados",
        "",
    ).strip()

    try:
        cantidad_invitados = int(cantidad)
        hora_numero = int(hora)

        if cantidad_invitados < 1 or cantidad_invitados > 200:
            raise ValueError

        if hora_numero < 1 or hora_numero > 12:
            raise ValueError

        if minuto not in ("00", "30"):
            raise ValueError

        if periodo not in ("AM", "PM"):
            raise ValueError

        if periodo == "AM":
            if hora_numero == 12:
                hora_numero = 0
        else:
            if hora_numero != 12:
                hora_numero += 12

        fecha_limite_respuesta = datetime.strptime(
            f"{fecha_limite} {hora_numero:02d}:{minuto}",
            "%Y-%m-%d %H:%M",
        )

        if fecha_limite_respuesta <= datetime.now():
            raise ValueError

    except ValueError:
        return (
            "Los datos generales de las invitaciones "
            "no son válidos.",
            400,
        )

    invitaciones_creadas = []

    for numero in range(1, cantidad_invitados + 1):
        nombre = request.form.get(
            f"nombre_{numero}",
            "",
        ).strip()

        correo = request.form.get(
            f"correo_{numero}",
            "",
        ).strip()

        if not nombre or not correo:
            return (
                f"Faltan datos del invitado número {numero}.",
                400,
            )

        invitacion = gestionar_invitacion.crear_invitacion(
            destinatario=nombre,
            fecha_limite_respuesta=fecha_limite_respuesta,
        )

        invitaciones_creadas.append(
            {
                "nombre": nombre,
                "correo": correo,
                "token": invitacion.token,
                "enlace": url_for(
                    "ver_invitacion",
                    token=invitacion.token,
                    _external=True,
                ),
            }
        )

    return render_template(
        "invitaciones_creadas.html",
        invitaciones=invitaciones_creadas,
        fecha_limite_respuesta=fecha_limite_respuesta,
    )


@app.get("/invitacion-creada/<token>")
def invitacion_creada(token):
    """Muestra al organizador la invitación creada."""
    try:
        invitacion = gestionar_invitacion.consultar(
            token=token,
            ahora=datetime.now(),
        )

    except ValueError as error:
        return f"<h1>Error</h1><p>{error}</p>", 404

    enlace_invitacion = url_for(
        "ver_invitacion",
        token=invitacion.token,
        _external=True,
    )

    return render_template(
        "invitacion_creada.html",
        invitacion=invitacion,
        enlace_invitacion=enlace_invitacion,
    )


@app.route("/invitacion/<token>", methods=["GET", "POST"])
def ver_invitacion(token):
    """Muestra una invitación y permite responderla."""
    mensaje = None

    if request.method == "POST":
        estado = request.form.get("estado")

        if estado == "confirmado":
            nuevo_estado = EstadoInvitacion.CONFIRMADO

        elif estado == "no_asistire":
            nuevo_estado = EstadoInvitacion.NO_ASISTIRE

        else:
            nuevo_estado = None

        if nuevo_estado is None:
            mensaje = "Estado no válido."

        else:
            try:
                gestionar_invitacion.responder(
                    token=token,
                    estado=nuevo_estado,
                    ahora=datetime.now(),
                )

                mensaje = (
                    "Respuesta registrada correctamente."
                )

            except ValueError as error:
                return (
                    f"<h1>Error</h1><p>{error}</p>",
                    404,
                )

    try:
        invitacion = gestionar_invitacion.consultar(
            token=token,
            ahora=datetime.now(),
        )

    except ValueError as error:
        return f"<h1>Error</h1><p>{error}</p>", 404

    return render_template(
        "invitacion.html",
        invitacion=invitacion,
        mensaje=mensaje,
    )


@app.route(
    "/api/v1/invitaciones/<token>",
    methods=["GET"],
)
def api_consultar_invitacion(token):
    """Consulta una invitación y devuelve sus datos en JSON."""
    global invitaciones_consultadas_total

    try:
        invitacion = gestionar_invitacion.consultar(
            token=token,
            ahora=datetime.now(),
        )

    except ValueError as error:
        return jsonify(
            {
                "error": str(error),
            }
        ), 404

    invitaciones_consultadas_total += 1

    return jsonify(
        {
            "token": invitacion.token,
            "destinatario": invitacion.destinatario,
            "fecha_limite_respuesta": (
                invitacion.fecha_limite_respuesta.isoformat()
            ),
            "estado": invitacion.estado.value,
        }
    ), 200


@app.route(
    "/api/v1/invitaciones/<token>",
    methods=["POST"],
)
def api_responder_invitacion(token):
    """Registra la respuesta del invitado y devuelve la invitación."""
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict) or "estado" not in datos:
        return jsonify(
            {
                "error": "Debe proporcionar el campo 'estado'.",
            }
        ), 400

    estado = datos["estado"]

    if estado == "confirmado":
        nuevo_estado = EstadoInvitacion.CONFIRMADO

    elif estado == "no_asistire":
        nuevo_estado = EstadoInvitacion.NO_ASISTIRE

    else:
        return jsonify(
            {
                "error": (
                    "El estado proporcionado no es válido."
                ),
            }
        ), 400

    try:
        invitacion = gestionar_invitacion.responder(
            token=token,
            estado=nuevo_estado,
            ahora=datetime.now(),
        )

    except ValueError as error:
        return jsonify(
            {
                "error": str(error),
            }
        ), 404

    return jsonify(
        {
            "token": invitacion.token,
            "destinatario": invitacion.destinatario,
            "fecha_limite_respuesta": (
                invitacion.fecha_limite_respuesta.isoformat()
            ),
            "estado": invitacion.estado.value,
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True)