
import re

from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from src.compartido.infraestructura.base_datos import SessionLocal
from src.usuarios.infraestructura.modelo_usuario import UsuarioModelo
from src.usuarios.infraestructura.repositorio_usuarios import (
    RepositorioUsuarios,
)


def registrar_usuario(nombre: str, correo: str, contrasena: str):
    nombre = nombre.strip()
    correo = correo.strip().lower()

    # Validaciones iniciales
    if not nombre or len(nombre) > 150:
        raise ValueError("El nombre debe tener entre 1 y 150 caracteres.")

    if len(correo) > 255 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", correo
    ):
        raise ValueError("El correo electrónico no es válido.")

    if len(contrasena) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    if len(contrasena) > 128:
        raise ValueError("La contraseña no puede superar los 128 caracteres.")

    with SessionLocal() as sesion:
        repositorio = RepositorioUsuarios(sesion)

        if repositorio.buscar_por_correo(correo):
            raise ValueError("Este correo ya está registrado.")

        usuario = UsuarioModelo(
            nombre=nombre,
            correo=correo,
            contrasena_hash=generate_password_hash(
                contrasena,
                method="scrypt",
            ),
            activo=True,
        )

        try:
            repositorio.guardar(usuario)
            sesion.commit()
            sesion.refresh(usuario)
        except IntegrityError:
            sesion.rollback()
            raise ValueError("Este correo ya está registrado.") from None

        return {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
        }
