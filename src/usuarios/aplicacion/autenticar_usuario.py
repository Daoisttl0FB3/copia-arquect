
from werkzeug.security import check_password_hash

from src.compartido.infraestructura.base_datos import SessionLocal
from src.usuarios.infraestructura.repositorio_usuarios import (
    RepositorioUsuarios,
)


def autenticar_usuario(correo: str, contrasena: str):
    correo = correo.strip().lower()

    with SessionLocal() as sesion:
        repositorio = RepositorioUsuarios(sesion)
        usuario = repositorio.buscar_por_correo(correo)

        if usuario is None:
            return None

        if not usuario.activo:
            return None

        if not check_password_hash(
            usuario.contrasena_hash,
            contrasena,
        ):
            return None

        return {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
        }

