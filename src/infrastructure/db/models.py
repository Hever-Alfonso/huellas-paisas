"""Modelos ORM de Huellas Paisas.

Los modelos aquí definidos son la representación física de las
tablas en SQLite. NO deben confundirse con las entidades del
dominio: estas clases tienen tipado específico de SQLAlchemy y
conocen detalles de persistencia.

Los repositorios concretos son los encargados de traducir entre
modelos ORM y entidades del dominio.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ProductModel(Base):
    """Tabla ``products``: catálogo de zapatos.

    Attributes:
        id: Clave primaria autoincremental.
        name: Nombre comercial del modelo.
        brand: Marca del fabricante, indexada para búsquedas rápidas.
        category: Categoría de uso, también indexada.
        size: Talla como texto.
        color: Color principal.
        price: Precio en USD.
        stock: Unidades disponibles en inventario.
        description: Descripción corta del producto.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        """Representación legible para depuración.

        Returns:
            Cadena con los campos clave del producto.
        """
        return (
            f"<ProductModel id={self.id} brand={self.brand!r} "
            f"name={self.name!r} stock={self.stock}>"
        )


class ChatMemoryModel(Base):
    """Tabla ``chat_memory``: historial conversacional.

    Almacena mensajes individuales y permite reconstruir la
    conversación de una sesión concreta. El índice en
    ``session_id`` es crítico porque las consultas más frecuentes
    filtran justamente por ese campo.

    Attributes:
        id: Clave primaria autoincremental.
        session_id: Identificador de sesión, indexado.
        role: Rol del emisor (``user`` o ``assistant``).
        message: Contenido del mensaje.
        timestamp: Fecha de creación, valor por defecto ``utcnow``.
    """

    __tablename__ = "chat_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        """Representación legible para depuración.

        Returns:
            Cadena con sesión, rol y timestamp del mensaje.
        """
        return (
            f"<ChatMemoryModel id={self.id} session={self.session_id!r} "
            f"role={self.role} ts={self.timestamp.isoformat()}>"
        )
