
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está configurada."
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def verificar_conexion():
    with engine.connect() as conexion:
        resultado = conexion.execute(
            text("SELECT current_database()")
        )
        return resultado.scalar_one()
