
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.usuarios.infraestructura.modelo_usuario import UsuarioModelo


class RepositorioUsuarios:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_por_correo(self, correo: str):
        consulta = select(UsuarioModelo).where(
            UsuarioModelo.correo == correo
        )
        return self.sesion.scalar(consulta)

    def guardar(self, usuario: UsuarioModelo):
        self.sesion.add(usuario)
        self.sesion.flush()
        return usuario
