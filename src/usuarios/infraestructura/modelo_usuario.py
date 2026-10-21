
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


class UsuarioModelo(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    correo: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    contrasena_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
