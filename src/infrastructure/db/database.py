"""Configuración de SQLAlchemy para Huellas Paisas.

Este módulo expone:

* ``engine``: motor de conexión a SQLite.
* ``SessionLocal``: *factory* de sesiones.
* ``Base``: clase base declarativa de la que heredan los modelos ORM.
* ``get_db``: dependencia de FastAPI que abre y cierra una sesión
  por cada petición.
* ``init_db``: inicializa el esquema y carga el catálogo inicial.
"""

from __future__ import annotations

import logging
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings

logger = logging.getLogger(__name__)

# Nos aseguramos de que la carpeta ./data exista antes de crear el engine,
# para que SQLite pueda materializar el archivo sin errores.
settings.ensure_data_dir()

# ``check_same_thread`` se pone en False porque SQLite, por defecto,
# no permite compartir conexiones entre hilos. FastAPI maneja su pool
# internamente, así que es seguro desactivar esa restricción.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredan los modelos ORM.

    Se usa la API 2.0 de SQLAlchemy (``DeclarativeBase``) para obtener
    tipado estático y mejores errores en los IDEs modernos.
    """


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI que entrega una sesión de SQLAlchemy.

    Cada petición HTTP recibe su propia sesión, que se cierra
    automáticamente al terminar gracias al bloque ``finally``.

    Yields:
        Una ``Session`` lista para ejecutar consultas.

    Example:
        >>> from fastapi import Depends
        >>> def endpoint(db: Session = Depends(get_db)):
        ...     ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Inicializa el esquema y carga los datos iniciales.

    Si las tablas no existen se crean, y si la tabla de productos
    está vacía se inserta el catálogo inicial. La función es
    idempotente: llamarla varias veces no duplica datos.
    """
    # Import local para evitar ciclos: models importa Base desde aquí.
    from . import models  # noqa: F401  (import para registrar tablas)
    from .init_data import load_initial_data

    logger.info("Creando esquema de base de datos si no existe...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as sesion:
        load_initial_data(sesion)
    logger.info("Base de datos lista.")
