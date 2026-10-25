import os
import secrets
import sys
from datetime import datetime
from functools import wraps

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
from flask_wtf.csrf import CSRFProtect

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
from src.usuarios.aplicacion.registrar_usuario import registrar_usuario
from src.usuarios.aplicacion.autenticar_usuario import autenticar_usuario
from src.invitaciones.aplicacion.agregar_invitados import agregar_invitados
from src.invitaciones.infraestructura.repositorio_invitaciones_postgres import (
    RepositorioInvitacionesPostgres,
)
from src.compartido.infraestructura.base_datos import SessionLocal
from src.eventos.infraestructura.repositorio_eventos import (
    RepositorioEventos,
)
from src.usuarios.infraestructura.modelo_usuario import UsuarioModelo
from src.eventos.aplicacion.crear_evento import crear_evento
from src.invitaciones.infraestructura.modelo_invitacion import InvitacionModelo
from src.eventos.infraestructura.modelo_evento import EventoModelo

from zoneinfo import ZoneInfo
from flask import abort
from datetime import datetime, timezone
from sqlalchemy import select

app = Flask(__name__)

# SECRET_KEY se configura en .env, nunca se publica en Git.
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




def login_requerido(funcion):
    @wraps(funcion)
    def decorador(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return funcion(*args, **kwargs)
    return decorador


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if "usuario_id" in session:
        return redirect(url_for("panel"))

    mensaje_error = None
    if request.method == "POST":
        nombre = request.form.get("nombre", "")
        correo = request.form.get("correo", "")
        contrasena = request.form.get("contrasena", "")
        confirmar = request.form.get("confirmar_contrasena", "")

        if contrasena != confirmar:
            mensaje_error = "Las contraseñas no coinciden."
        else:
            try:
                registrar_usuario(nombre, correo, contrasena)
                return redirect(url_for("login"))
            except ValueError as error:
                mensaje_error = str(error)

    return render_template("registro.html", mensaje_error=mensaje_error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("panel"))

    mensaje_error = None
    if request.method == "POST":
        correo = request.form.get("correo", "")
        contrasena = request.form.get("contrasena", "")
        usuario = autenticar_usuario(correo, contrasena)

        if usuario is None:
            mensaje_error = "Correo o contraseña incorrectos."
        else:
            session.clear()
            session["usuario_id"] = usuario["id"]
            return redirect(url_for("panel"))

    return render_template("login.html", mensaje_error=mensaje_error)



@app.get("/panel")
@login_requerido
def panel():
    usuario_id = session["usuario_id"]

    with SessionLocal() as sesion:
        usuario = sesion.get(UsuarioModelo, usuario_id)

        if usuario is None or not usuario.activo:
            session.clear()
            return redirect(url_for("login"))

        repositorio = RepositorioEventos(sesion)

        eventos = repositorio.listar_por_usuario(usuario_id)
        cantidad_activos = repositorio.contar_activos(usuario_id)

        datos_eventos = [
            {
                "id": evento.id,
                "titulo": evento.titulo,
                "descripcion": evento.descripcion,
                "ubicacion": evento.ubicacion,
                "fecha_evento": evento.fecha_evento,
                "estado": evento.estado,
            }
            for evento in eventos
        ]

        nombre_usuario = usuario.nombre

    return render_template(
        "panel.html",
        nombre_usuario=nombre_usuario,
        eventos=datos_eventos,
        cantidad_activos=cantidad_activos,
        limite_eventos=4,
    )



@app.route("/eventos/crear", methods=["GET", "POST"])
@login_requerido
def nuevo_evento():
    mensaje_error = None

    with SessionLocal() as sesion:
        repositorio = RepositorioEventos(sesion)
        cantidad_activos = repositorio.contar_activos(
            session["usuario_id"]
        )

    if cantidad_activos >= 4:
        return redirect(url_for("panel"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "")
        descripcion = request.form.get("descripcion", "")
        ubicacion = request.form.get("ubicacion", "")

        fecha_texto = request.form.get("fecha_evento", "")
        limite_texto = request.form.get(
            "fecha_limite_confirmacion", ""
        )

        try:
            zona = ZoneInfo("America/Bogota")

            fecha_evento = datetime.fromisoformat(
                fecha_texto
            ).replace(tzinfo=zona)

            fecha_limite = datetime.fromisoformat(
                limite_texto
            ).replace(tzinfo=zona)

            crear_evento(
                usuario_id=session["usuario_id"],
                titulo=titulo,
                descripcion=descripcion,
                ubicacion=ubicacion,
                fecha_evento=fecha_evento,
                fecha_limite_confirmacion=fecha_limite,
            )

            return redirect(url_for("panel"))

        except ValueError as error:
            mensaje_error = str(error)

    return render_template(
        "crear_evento.html",
        mensaje_error=mensaje_error,
    )


@app.get("/eventos/<int:evento_id>")
@login_requerido
def detalle_evento(evento_id):
    usuario_id = session["usuario_id"]
    zona = ZoneInfo("America/Bogota")

    with SessionLocal() as sesion:
        repositorio = RepositorioEventos(sesion)
        evento = repositorio.buscar_por_id(evento_id, usuario_id)

        if evento is None:
            abort(404)

        datos_evento = {
            "id": evento.id,
            "titulo": evento.titulo,
            "descripcion": evento.descripcion,
            "ubicacion": evento.ubicacion,
            "estado": evento.estado,
            "fecha_evento": evento.fecha_evento.astimezone(zona),
            "fecha_limite": (
                evento.fecha_limite_confirmacion.astimezone(zona)
            ),
        }

    return render_template(
        "detalle_evento.html",
        evento=datos_evento,
    )


@app.route("/eventos/<int:evento_id>/invitados", methods=["GET", "POST"])
@login_requerido
def invitados_evento(evento_id):
    usuario_id = session["usuario_id"]
    mensaje_error = None

    with SessionLocal() as sesion:
        evento = RepositorioEventos(sesion).buscar_por_id(
            evento_id, usuario_id
        )
        if evento is None:
            abort(404)

        titulo_evento = evento.titulo

    if request.method == "POST":
        nombres = request.form.getlist("nombre[]")
        correos = request.form.getlist("correo[]")

        try:
            if len(nombres) != len(correos):
                raise ValueError("Los datos de los invitados están incompletos.")

            invitados_nuevos = [
                {"nombre": nombre, "correo": correo}
                for nombre, correo in zip(nombres, correos)
            ]

            agregar_invitados(
                evento_id=evento_id,
                usuario_id=usuario_id,
                invitados=invitados_nuevos,
            )

            return redirect(url_for("invitados_evento", evento_id=evento_id))

        except ValueError as error:
            mensaje_error = str(error)

    with SessionLocal() as sesion:
        repositorio = RepositorioInvitacionesPostgres(sesion)
        invitaciones = [
            {
                "nombre": invitacion.nombre,
                "correo": invitacion.correo,
                "estado": invitacion.estado,
                "token": invitacion.token,
            }
            for invitacion in repositorio.listar_por_evento(evento_id)
        ]

    return render_template(
        "invitados_evento.html",
        evento_id=evento_id,
        titulo_evento=titulo_evento,
        invitaciones=invitaciones,
        espacios_disponibles=30 - len(invitaciones),
        mensaje_error=mensaje_error,
    )


@app.route("/eventos/invitacion/<token>", methods=["GET", "POST"])
def ver_invitacion_evento(token):
    mensaje = None
    error = None

    with SessionLocal() as sesion:
        invitacion = sesion.scalar(
            select(InvitacionModelo).where(
                InvitacionModelo.token == token
            )
        )

        if invitacion is None:
            abort(404)

        evento = sesion.get(EventoModelo, invitacion.evento_id)

        if evento is None:
            abort(404)

        ahora = datetime.now(timezone.utc)

        vencida = (
            ahora > evento.fecha_limite_confirmacion
            or evento.estado in ("finalizado", "cancelado")
        )

        if request.method == "POST":
            nuevo_estado = request.form.get("estado")

            if vencida:
                error = "El plazo para responder ha finalizado."

            elif nuevo_estado not in ("confirmado", "no_asistire"):
                error = "Selecciona una respuesta válida."

            else:
                invitacion.estado = nuevo_estado
                sesion.commit()
                mensaje = "Tu respuesta se registró correctamente."

        datos = {
            "nombre": invitacion.nombre,
            "estado": invitacion.estado,
            "titulo": evento.titulo,
            "descripcion": evento.descripcion,
            "ubicacion": evento.ubicacion,
            "fecha_evento": evento.fecha_evento.astimezone(
                ZoneInfo("America/Bogota")
            ),
            "fecha_limite": (
                evento.fecha_limite_confirmacion.astimezone(
                    ZoneInfo("America/Bogota")
                )
            ),
        }

    return render_template(
        "invitacion_evento.html",
        invitacion=datos,
        vencida=vencida,
        mensaje=mensaje,
        error=error,
    )


@app.post("/logout")
@login_requerido
def logout():
    session.clear()
    return redirect(url_for("login"))

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
    if "usuario_id" in session:
        return redirect(url_for("panel"))

    return redirect(url_for("login"))


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
@csrf.exempt
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
