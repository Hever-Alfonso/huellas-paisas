"""Tests de integración de la API FastAPI de Huellas Paisas.

Usan ``TestClient`` para ejercitar los endpoints HTTP sin levantar un
servidor real. La base de datos real se reemplaza por SQLite en memoria
con ``StaticPool`` y el servicio de IA por un doble de prueba determinista.
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.chat_service import ChatService
from src.infrastructure.api.main import app, get_chat_service, get_db
from src.infrastructure.db import models  # noqa: registra los modelos en Base.metadata
from src.infrastructure.db.database import Base
from src.infrastructure.repositories.chat_repository import SQLChatRepository
from src.infrastructure.repositories.product_repository import SQLProductRepository


class _FakeAI:
    """Doble de IA que devuelve una respuesta fija sin llamar a Gemini."""

    async def generate_response(self, user_message, products, context) -> str:
        """Devuelve texto fijo, ignorando los argumentos.

        Args:
            user_message: Mensaje del usuario (ignorado).
            products: Catálogo (ignorado).
            context: Historial conversacional (ignorado).

        Returns:
            Cadena predecible para verificar en los tests.
        """
        return "Respuesta de prueba de Santi."


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente de prueba con base de datos y servicio de IA simulados.

    Crea su propio motor SQLite en memoria con ``StaticPool`` para que
    todas las sesiones compartan la misma conexión subyacente, evitando
    el problema de que cada checkout genere una base vacía. Anula las
    dependencias de FastAPI y parchea ``init_db`` para no tocar la base real.

    Yields:
        ``TestClient`` configurado con las dependencias anuladas.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False)

    def _override_get_db():
        sesion = TestSession()
        try:
            yield sesion
        finally:
            sesion.close()

    def _override_get_chat_service():
        sesion = TestSession()
        return ChatService(
            product_repo=SQLProductRepository(sesion),
            chat_repo=SQLChatRepository(sesion),
            ai_service=_FakeAI(),
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_chat_service] = _override_get_chat_service

    with patch("src.infrastructure.api.main.init_db"):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _payload_producto(**kwargs) -> dict:
    """Construye un payload JSON válido para crear un producto.

    Args:
        **kwargs: Campos a sobreescribir sobre los valores por defecto.

    Returns:
        Diccionario listo para enviar como cuerpo JSON al endpoint.
    """
    datos = {
        "name": "574 Core",
        "brand": "New Balance",
        "category": "Casual",
        "size": "43",
        "color": "Gris",
        "price": 109.0,
        "stock": 7,
        "description": "Clásico moderno con ENCAP.",
    }
    datos.update(kwargs)
    return datos


class TestEndpointsMeta:
    """Tests de los endpoints de estado y métricas del sistema."""

    def test_raiz_devuelve_nombre_y_version(self, client):
        """La raíz debe responder 200 con los campos 'app' y 'version'."""
        respuesta = client.get("/")
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert "app" in cuerpo
        assert "version" in cuerpo

    def test_health_check_estado_ok(self, client):
        """El health check debe devolver status 200 con campo status 'ok'."""
        respuesta = client.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["status"] == "ok"

    def test_stats_devuelve_campos_requeridos(self, client):
        """El endpoint /stats debe incluir los tres contadores."""
        respuesta = client.get("/stats")
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert "total_products" in cuerpo
        assert "products_in_stock" in cuerpo
        assert "total_messages" in cuerpo

    def test_middleware_timing_agrega_header(self, client):
        """El middleware de timing debe añadir el header X-Process-Time-ms."""
        respuesta = client.get("/health")
        assert "x-process-time-ms" in respuesta.headers


class TestEndpointsProductos:
    """Tests de los endpoints CRUD de productos."""

    def test_listar_productos_catalogo_vacio(self, client):
        """Devuelve lista vacía cuando no hay productos en la base."""
        respuesta = client.get("/products")
        assert respuesta.status_code == 200
        assert respuesta.json() == []

    def test_crear_producto_devuelve_201_con_id(self, client):
        """Crea un producto, espera HTTP 201 y verifica que se asignó ID."""
        respuesta = client.post("/products", json=_payload_producto())
        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["id"] is not None
        assert cuerpo["brand"] == "New Balance"

    def test_obtener_producto_por_id_existente(self, client):
        """Recupera el detalle de un producto recién creado por su ID."""
        creado = client.post("/products", json=_payload_producto()).json()
        respuesta = client.get(f"/products/{creado['id']}")
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == creado["id"]

    def test_obtener_producto_inexistente_devuelve_404(self, client):
        """Solicitar un ID que no existe debe devolver HTTP 404."""
        respuesta = client.get("/products/9999")
        assert respuesta.status_code == 404

    def test_listar_disponibles_excluye_sin_stock(self, client):
        """Solo deben aparecer productos con stock mayor a cero."""
        client.post("/products", json=_payload_producto(name="Con stock", stock=5))
        client.post("/products", json=_payload_producto(name="Sin stock", stock=0))
        respuesta = client.get("/products/available")
        assert respuesta.status_code == 200
        nombres = {p["name"] for p in respuesta.json()}
        assert "Con stock" in nombres
        assert "Sin stock" not in nombres

    def test_crear_producto_precio_invalido_devuelve_422(self, client):
        """Un precio negativo debe ser rechazado con HTTP 422."""
        respuesta = client.post("/products", json=_payload_producto(price=-1.0))
        assert respuesta.status_code == 422

    def test_lista_crece_despues_de_crear(self, client):
        """La lista de productos debe reflejar los registros creados."""
        client.post("/products", json=_payload_producto())
        client.post("/products", json=_payload_producto(name="Air Max 90"))
        respuesta = client.get("/products")
        assert len(respuesta.json()) == 2


class TestEndpointsChat:
    """Tests de los endpoints del chat con el asistente Santi."""

    def test_enviar_mensaje_devuelve_turno_completo(self, client):
        """El endpoint /chat debe devolver el mensaje del usuario y la respuesta."""
        payload = {"session_id": "sesion_test", "message": "Hola Santi"}
        respuesta = client.post("/chat", json=payload)
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["user_message"] == "Hola Santi"
        assert cuerpo["assistant_message"] == "Respuesta de prueba de Santi."
        assert cuerpo["session_id"] == "sesion_test"

    def test_historial_vacio_para_sesion_nueva(self, client):
        """Una sesión recién creada no debe tener historial."""
        respuesta = client.get("/chat/history/sesion_nueva_xyz")
        assert respuesta.status_code == 200
        assert respuesta.json() == []

    def test_historial_crece_tras_enviar_mensaje(self, client):
        """Después de un mensaje el historial debe tener user + assistant."""
        payload = {"session_id": "s_hist", "message": "¿Tienen Nike?"}
        client.post("/chat", json=payload)
        respuesta = client.get("/chat/history/s_hist")
        historial = respuesta.json()
        assert len(historial) == 2
        assert historial[0]["role"] == "user"
        assert historial[1]["role"] == "assistant"

    def test_borrar_historial_retorna_conteo(self, client):
        """Eliminar el historial debe devolver los mensajes borrados."""
        payload = {"session_id": "s_borrar", "message": "Hola"}
        client.post("/chat", json=payload)
        respuesta = client.delete("/chat/history/s_borrar")
        assert respuesta.status_code == 200
        assert respuesta.json()["deleted_messages"] == 2

    def test_historial_limit_cero_devuelve_400(self, client):
        """El parámetro limit=0 debe ser rechazado con HTTP 400."""
        respuesta = client.get("/chat/history/cualquier_sesion?limit=0")
        assert respuesta.status_code == 400

    def test_mensaje_vacio_devuelve_422(self, client):
        """Un mensaje compuesto solo de espacios debe ser rechazado con HTTP 422."""
        payload = {"session_id": "s1", "message": "   "}
        respuesta = client.post("/chat", json=payload)
        assert respuesta.status_code == 422
