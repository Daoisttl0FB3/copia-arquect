
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.usuarios.infraestructura.modelo_usuario import Base


class InvitacionModelo(Base):
    __tablename__ = "invitaciones"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente', 'confirmado', 'no_asistire')",
            name="ck_invitaciones_estado",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    evento_id: Mapped[int] = mapped_column(
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    correo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pendiente",
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
