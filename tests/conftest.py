"""Fixtures compartidas de pytest para Huellas Paisas.

Provee una base de datos SQLite en memoria aislada por test, así
como dobles de prueba para el servicio de IA.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.domain.entities import ChatContext, Product
from src.infrastructure.db.database import Base
from src.infrastructure.db.models import ProductModel
from src.infrastructure.repositories.chat_repository import SQLChatRepository
from src.infrastructure.repositories.product_repository import (
    SQLProductRepository,
)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Crea una base de datos SQLite en memoria, aislada por test.

    Yields:
        Sesión de SQLAlchemy lista para usar. Se cierra automáticamente.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)
    sesion = TestSession()
    try:
        yield sesion
    finally:
        sesion.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def product_repo(db_session: Session) -> SQLProductRepository:
    """Repositorio de productos usando la base en memoria."""
    return SQLProductRepository(db_session)


@pytest.fixture
def chat_repo(db_session: Session) -> SQLChatRepository:
    """Repositorio de chat usando la base en memoria."""
    return SQLChatRepository(db_session)


@pytest.fixture
def sample_products(db_session: Session) -> list[ProductModel]:
    """Inserta tres productos de prueba directamente en la base."""
    productos = [
        ProductModel(
            name="Air Zoom Pegasus 40",
            brand="Nike",
            category="Running",
            size="42",
            color="Negro",
            price=139.0,
            stock=5,
            description="Test running shoe",
        ),
        ProductModel(
            name="Oxford Clásico",
            brand="Bosi",
            category="Formal",
            size="41",
            color="Café",
            price=149.0,
            stock=0,
            description="Test formal shoe",
        ),
        ProductModel(
            name="Suede Classic XXI",
            brand="Puma",
            category="Casual",
            size="40",
            color="Azul",
            price=79.0,
            stock=12,
            description="Test casual shoe",
        ),
    ]
    db_session.add_all(productos)
    db_session.commit()
    for p in productos:
        db_session.refresh(p)
    return productos


class FakeAIService:
    """Doble de prueba para el servicio de IA.

    Graba los argumentos recibidos y devuelve una respuesta fija.
    Así los tests del ``ChatService`` no dependen de Gemini.
    """

    def __init__(self, canned_response: str = "Respuesta de prueba.") -> None:
        self.canned_response = canned_response
        self.last_user_message: str | None = None
        self.last_products: list[Product] | None = None
        self.last_context: ChatContext | None = None
        self.call_count = 0

    async def generate_response(
        self,
        user_message: str,
        products: list[Product],
        context: ChatContext,
    ) -> str:
        self.last_user_message = user_message
        self.last_products = list(products)
        self.last_context = context
        self.call_count += 1
        return self.canned_response


@pytest.fixture
def fake_ai() -> FakeAIService:
    """Instancia de ``FakeAIService`` para inyectar en ``ChatService``."""
    return FakeAIService()


@pytest.fixture
def frozen_now() -> datetime:
    """Timestamp fijo útil para tests deterministas."""
    return datetime(2024, 1, 15, 10, 30, 0)
