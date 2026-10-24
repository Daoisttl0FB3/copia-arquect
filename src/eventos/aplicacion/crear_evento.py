
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from src.compartido.infraestructura.base_datos import SessionLocal
from src.eventos.infraestructura.modelo_evento import EventoModelo
from src.eventos.infraestructura.repositorio_eventos import (
    RepositorioEventos,
)
from src.usuarios.infraestructura.modelo_usuario import UsuarioModelo


ZONA_HORARIA = ZoneInfo("America/Bogota")
MAX_EVENTOS_ACTIVOS = 4


def crear_evento(
    usuario_id: int,
    titulo: str,
    descripcion: str,
    ubicacion: str,
    fecha_evento: datetime,
    fecha_limite_confirmacion: datetime,
):
    titulo = titulo.strip()
    descripcion = (descripcion or "").strip()
    ubicacion = ubicacion.strip()

    if not titulo or len(titulo) > 150:
        raise ValueError(
            "El título debe tener entre 1 y 150 caracteres."
        )

    if len(descripcion) > 2000:
        raise ValueError(
            "La descripción no puede superar los 2000 caracteres."
        )

    if not ubicacion or len(ubicacion) > 255:
        raise ValueError(
            "La ubicación debe tener entre 1 y 255 caracteres."
        )

    if (
        fecha_evento.tzinfo is None
        or fecha_limite_confirmacion.tzinfo is None
    ):
        raise ValueError(
            "Las fechas deben incluir una zona horaria."
        )

    ahora = datetime.now(timezone.utc)

    if fecha_evento <= ahora:
        raise ValueError(
            "La fecha del evento debe ser futura."
        )

    if fecha_limite_confirmacion <= ahora:
        raise ValueError(
            "La fecha límite de confirmación debe ser futura."
        )

    if fecha_limite_confirmacion >= fecha_evento:
        raise ValueError(
            "La fecha límite de confirmación debe ser "
            "anterior al evento."
        )

    with SessionLocal() as sesion:
        # Bloqueamos la fila del organizador para que dos
        # solicitudes simultáneas no superen el límite.
        usuario = sesion.scalar(
            select(UsuarioModelo)
            .where(UsuarioModelo.id == usuario_id)
            .with_for_update()
        )

        if usuario is None or not usuario.activo:
            raise ValueError(
                "El usuario no existe o está inactivo."
            )

        repositorio = RepositorioEventos(sesion)

        if repositorio.contar_activos(usuario_id) >= MAX_EVENTOS_ACTIVOS:
            raise ValueError(
                "Ya tienes cuatro eventos activos. "
                "Finaliza o cancela uno antes de crear otro."
            )

        evento = EventoModelo(
            usuario_id=usuario_id,
            titulo=titulo,
            descripcion=descripcion or None,
            ubicacion=ubicacion,
            fecha_evento=fecha_evento.astimezone(timezone.utc),
            fecha_limite_confirmacion=(
                fecha_limite_confirmacion.astimezone(timezone.utc)
            ),
            estado="borrador",
        )

        repositorio.guardar(evento)
        sesion.commit()
        sesion.refresh(evento)

        return {
            "id": evento.id,
            "titulo": evento.titulo,
            "estado": evento.estado,
            "usuario_id": evento.usuario_id,
        }
