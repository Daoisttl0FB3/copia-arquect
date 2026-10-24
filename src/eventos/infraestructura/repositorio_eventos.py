
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.eventos.infraestructura.modelo_evento import EventoModelo


ESTADOS_ACTIVOS = ("borrador", "en_preparacion")


class RepositorioEventos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def guardar(self, evento: EventoModelo):
        self.sesion.add(evento)
        self.sesion.flush()
        return evento

    def buscar_por_id(self, evento_id: int, usuario_id: int):
        consulta = select(EventoModelo).where(
            EventoModelo.id == evento_id,
            EventoModelo.usuario_id == usuario_id,
        )
        return self.sesion.scalar(consulta)

    def listar_por_usuario(self, usuario_id: int):
        consulta = (
            select(EventoModelo)
            .where(EventoModelo.usuario_id == usuario_id)
            .order_by(EventoModelo.fecha_evento.asc())
        )
        return self.sesion.scalars(consulta).all()

    def contar_activos(self, usuario_id: int):
        consulta = select(func.count(EventoModelo.id)).where(
            EventoModelo.usuario_id == usuario_id,
            EventoModelo.estado.in_(ESTADOS_ACTIVOS),
        )
        return self.sesion.scalar(consulta) or 0
