
import secrets

from sqlalchemy import select

from src.compartido.infraestructura.base_datos import SessionLocal
from src.eventos.infraestructura.modelo_evento import EventoModelo
from src.invitaciones.infraestructura.modelo_invitacion import (
    InvitacionModelo,
)
from src.invitaciones.infraestructura.repositorio_invitaciones_postgres import (
    RepositorioInvitacionesPostgres,
)

MAX_INVITADOS = 30


def agregar_invitados(evento_id: int, usuario_id: int, invitados: list):
    if not invitados:
        raise ValueError("Debes agregar al menos un invitado.")

    if len(invitados) > MAX_INVITADOS:
        raise ValueError("No puedes agregar más de 30 invitados.")

    invitados_validados = []
    correos_nuevos = set()

    for invitado in invitados:
        nombre = str(invitado.get("nombre", "")).strip()
        correo = str(invitado.get("correo", "")).strip().lower()

        if not nombre or len(nombre) > 150:
            raise ValueError(
                "Cada invitado debe tener un nombre de máximo 150 caracteres."
            )

        if (
            not correo
            or len(correo) > 255
            or correo.count("@") != 1
            or "." not in correo.split("@")[-1]
        ):
            raise ValueError(
                f"El correo del invitado {nombre} no es válido."
            )

        if correo in correos_nuevos:
            raise ValueError(
                f"El correo {correo} está repetido en la lista."
            )

        correos_nuevos.add(correo)
        invitados_validados.append(
            {"nombre": nombre, "correo": correo}
        )

    with SessionLocal() as sesion:
        evento = sesion.scalar(
            select(EventoModelo)
            .where(
                EventoModelo.id == evento_id,
                EventoModelo.usuario_id == usuario_id,
            )
            .with_for_update()
        )

        if evento is None:
            raise ValueError("El evento no existe o no te pertenece.")

        if evento.estado in ("finalizado", "cancelado"):
            raise ValueError(
                "No puedes agregar invitados a un evento cerrado."
            )

        repositorio = RepositorioInvitacionesPostgres(sesion)

        cantidad_actual = repositorio.contar_por_evento(evento_id)

        if cantidad_actual + len(invitados_validados) > MAX_INVITADOS:
            raise ValueError(
                f"Este evento ya tiene {cantidad_actual} invitados. "
                "El máximo permitido es 30."
            )

        correos_existentes = {
            invitacion.correo.lower()
            for invitacion in repositorio.listar_por_evento(evento_id)
        }

        for invitado in invitados_validados:
            if invitado["correo"] in correos_existentes:
                raise ValueError(
                    f"El correo {invitado['correo']} "
                    "ya está registrado en este evento."
                )

        resultado = []

        for invitado in invitados_validados:
            token = secrets.token_urlsafe(32)

            nueva_invitacion = InvitacionModelo(
                evento_id=evento_id,
                nombre=invitado["nombre"],
                correo=invitado["correo"],
                token=token,
                estado="pendiente",
            )

            repositorio.guardar(nueva_invitacion)

            resultado.append(
                {
                    "id": nueva_invitacion.id,
                    "nombre": nueva_invitacion.nombre,
                    "correo": nueva_invitacion.correo,
                    "token": nueva_invitacion.token,
                    "estado": nueva_invitacion.estado,
                }
            )

        sesion.commit()
        return resultado
