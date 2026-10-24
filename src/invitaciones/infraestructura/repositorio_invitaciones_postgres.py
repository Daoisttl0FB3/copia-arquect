
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.invitaciones.infraestructura.modelo_invitacion import (
    InvitacionModelo,
)


class RepositorioInvitacionesPostgres:

    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, invitacion: InvitacionModelo):
        self.sesion.add(invitacion)
        self.sesion.flush()
        return invitacion

    def buscar_por_token(self, token: str):
        consulta = select(InvitacionModelo).where(
            InvitacionModelo.token == token
        )
        return self.sesion.scalar(consulta)

    def listar_por_evento(self, evento_id: int):
        consulta = (
            select(InvitacionModelo)
            .where(InvitacionModelo.evento_id == evento_id)
            .order_by(InvitacionModelo.id.asc())
        )
        return self.sesion.scalars(consulta).all()

    def contar_por_evento(self, evento_id: int):
        consulta = select(func.count(InvitacionModelo.id)).where(
            InvitacionModelo.evento_id == evento_id
        )
        return self.sesion.scalar(consulta) or 0

    def contar_por_estado(self, evento_id: int, estado: str):
        consulta = select(func.count(InvitacionModelo.id)).where(
            InvitacionModelo.evento_id == evento_id,
            InvitacionModelo.estado == estado,
        )
        return self.sesion.scalar(consulta) or 0

    def actualizar_estado(self, invitacion: InvitacionModelo, estado: str):
        if estado not in ("pendiente", "confirmado", "no_asistire"):
            raise ValueError("Estado de invitación no válido.")

        invitacion.estado = estado
        self.sesion.flush()

        return invitacion
