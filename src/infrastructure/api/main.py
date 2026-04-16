"""Aplicación FastAPI de Huellas Paisas.

Este módulo ensambla la aplicación completa: middleware, rutas,
dependencias y manejo de ciclo de vida. Usa la API moderna de
FastAPI:

* ``lifespan`` en lugar de los deprecated ``@app.on_event``.
* ``Annotated`` para declarar dependencias con tipado estático.
* Manejadores de excepciones del dominio para que ``HTTPException``
  no contamine la capa de aplicación.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.application.chat_service import ChatService
from src.application.dtos import (
    ChatHistoryDTO,
    ChatMessageRequestDTO,
    ChatMessageResponseDTO,
    HealthDTO,
    ProductDTO,
    StatsDTO,
)
from src.application.product_service import ProductService
from src.config import settings
from src.domain.exceptions import (
    ChatServiceError,
    DomainError,
    InvalidProductDataError,
    ProductNotFoundError,
)
from src.infrastructure.db.database import get_db, init_db
from src.infrastructure.db.models import ChatMemoryModel, ProductModel
from src.infrastructure.llm_providers.gemini_service import GeminiService
from src.infrastructure.repositories.chat_repository import SQLChatRepository
from src.infrastructure.repositories.product_repository import (
    SQLProductRepository,
)

# Configuración básica de logging estructurado simple.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("huellas_paisas")


# ---------------------------------------------------------------------------
# Ciclo de vida de la aplicación
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Gestor de ciclo de vida de la aplicación.

    Se ejecuta una vez al arrancar el servidor y otra al apagarlo.
    Aquí se inicializa la base de datos y se cargan los datos semilla.

    Args:
        _: Instancia de FastAPI (no se usa, por eso el guion bajo).

    Yields:
        Ningún valor. El ``yield`` separa el arranque del apagado.
    """
    logger.info("Arrancando Huellas Paisas API (%s)...", settings.environment)
    init_db()
    logger.info("Base de datos inicializada correctamente.")
    yield
    logger.info("Huellas Paisas API detenida limpiamente.")


# ---------------------------------------------------------------------------
# Instanciación de la aplicación
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "API REST de un e-commerce de zapatos con asistente conversacional "
        "impulsado por Google Gemini. Construida con Clean Architecture "
        "para la asignatura de Construcción 2 en la Universidad EAFIT."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware personalizado: tiempo de respuesta
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Middleware que añade el tiempo de respuesta en milisegundos.

    Args:
        request: Petición entrante.
        call_next: Siguiente middleware o endpoint en la cadena.

    Returns:
        La respuesta con un encabezado ``X-Process-Time-ms`` añadido.
    """
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000
    response.headers["X-Process-Time-ms"] = f"{duracion_ms:.2f}"
    return response


# ---------------------------------------------------------------------------
# Manejadores de excepciones del dominio
# ---------------------------------------------------------------------------


@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(
    _: Request, exc: ProductNotFoundError
) -> JSONResponse:
    """Traduce ``ProductNotFoundError`` a HTTP 404.

    Args:
        _: Petición que originó el error (no se usa).
        exc: Excepción capturada.

    Returns:
        Respuesta JSON con status 404.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "product_not_found", "message": exc.message},
    )


@app.exception_handler(InvalidProductDataError)
async def invalid_product_handler(
    _: Request, exc: InvalidProductDataError
) -> JSONResponse:
    """Traduce ``InvalidProductDataError`` a HTTP 422.

    Args:
        _: Petición que originó el error (no se usa).
        exc: Excepción capturada.

    Returns:
        Respuesta JSON con status 422.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "invalid_product_data", "message": exc.message},
    )


@app.exception_handler(ChatServiceError)
async def chat_service_error_handler(
    _: Request, exc: ChatServiceError
) -> JSONResponse:
    """Traduce ``ChatServiceError`` a HTTP 503.

    Args:
        _: Petición que originó el error (no se usa).
        exc: Excepción capturada.

    Returns:
        Respuesta JSON con status 503 (servicio no disponible).
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "chat_service_error", "message": exc.message},
    )


@app.exception_handler(DomainError)
async def generic_domain_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Captura cualquier otra excepción del dominio.

    Args:
        _: Petición que originó el error (no se usa).
        exc: Excepción capturada.

    Returns:
        Respuesta JSON con status 400.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "domain_error", "message": exc.message},
    )


# ---------------------------------------------------------------------------
# Dependencias (factories) que inyectan los servicios
# ---------------------------------------------------------------------------


def get_product_service(
    db: Annotated[Session, Depends(get_db)],
) -> ProductService:
    """Construye un ``ProductService`` para un request concreto.

    Args:
        db: Sesión de base de datos obtenida de ``get_db``.

    Returns:
        Instancia lista para usar del servicio de productos.
    """
    return ProductService(SQLProductRepository(db))


def get_chat_service(
    db: Annotated[Session, Depends(get_db)],
) -> ChatService:
    """Construye un ``ChatService`` con todas sus dependencias.

    Args:
        db: Sesión de base de datos obtenida de ``get_db``.

    Returns:
        Instancia lista para usar del servicio de chat.
    """
    return ChatService(
        product_repo=SQLProductRepository(db),
        chat_repo=SQLChatRepository(db),
        ai_service=GeminiService(),
    )


# Alias cortos para las anotaciones de dependencia.
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
DbDep = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", tags=["meta"])
def root() -> dict:
    """Endpoint raíz con información básica del servicio.

    Returns:
        Diccionario con nombre, versión y enlaces útiles.
    """
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health", response_model=HealthDTO, tags=["meta"])
def health_check() -> HealthDTO:
    """Health check simple para balanceadores y monitoreo.

    Returns:
        Objeto ``HealthDTO`` con el estado y timestamp actual.
    """
    return HealthDTO(
        status="ok",
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        version=settings.app_version,
    )


@app.get("/stats", response_model=StatsDTO, tags=["meta"])
def stats(db: DbDep) -> StatsDTO:
    """Métricas básicas del sistema.

    Expuesto como bonus para que el estudiante pueda documentar el
    estado de la tienda en tiempo real.

    Args:
        db: Sesión de base de datos inyectada.

    Returns:
        ``StatsDTO`` con totales de productos y mensajes.
    """
    total_productos = db.query(func.count(ProductModel.id)).scalar() or 0
    en_stock = (
        db.query(func.count(ProductModel.id))
        .filter(ProductModel.stock > 0)
        .scalar()
        or 0
    )
    total_mensajes = db.query(func.count(ChatMemoryModel.id)).scalar() or 0
    return StatsDTO(
        total_products=int(total_productos),
        products_in_stock=int(en_stock),
        total_messages=int(total_mensajes),
    )


# ------------------------------- Productos --------------------------------


@app.get("/products", response_model=list[ProductDTO], tags=["products"])
def list_products(service: ProductServiceDep) -> list[ProductDTO]:
    """Lista todos los productos del catálogo.

    Args:
        service: Servicio de productos inyectado.

    Returns:
        Lista de ``ProductDTO``.
    """
    return service.get_all_products()


@app.get(
    "/products/available",
    response_model=list[ProductDTO],
    tags=["products"],
)
def list_available_products(service: ProductServiceDep) -> list[ProductDTO]:
    """Lista únicamente los productos que tienen stock.

    Args:
        service: Servicio de productos inyectado.

    Returns:
        Lista de ``ProductDTO`` con stock mayor a cero.
    """
    return service.get_available_products()


@app.get("/products/{product_id}", response_model=ProductDTO, tags=["products"])
def get_product(product_id: int, service: ProductServiceDep) -> ProductDTO:
    """Devuelve el detalle de un producto por ID.

    Args:
        product_id: ID del producto.
        service: Servicio de productos inyectado.

    Returns:
        ``ProductDTO`` con toda la información del producto.

    Raises:
        ProductNotFoundError: Si el producto no existe (convertido a
            HTTP 404 por el manejador de excepciones global).
    """
    return service.get_product_by_id(product_id)


@app.post(
    "/products",
    response_model=ProductDTO,
    status_code=status.HTTP_201_CREATED,
    tags=["products"],
)
def create_product(
    product: ProductDTO, service: ProductServiceDep
) -> ProductDTO:
    """Crea un nuevo producto en el catálogo.

    Args:
        product: DTO con los datos del producto a crear.
        service: Servicio de productos inyectado.

    Returns:
        ``ProductDTO`` del producto recién creado.
    """
    return service.create_product(product)


# ---------------------------------- Chat ----------------------------------


@app.post("/chat", response_model=ChatMessageResponseDTO, tags=["chat"])
async def chat_endpoint(
    request: ChatMessageRequestDTO, service: ChatServiceDep
) -> ChatMessageResponseDTO:
    """Procesa un mensaje del usuario y devuelve la respuesta del asistente.

    Args:
        request: DTO con ``session_id`` y ``message``.
        service: Servicio de chat inyectado.

    Returns:
        ``ChatMessageResponseDTO`` con la respuesta generada por IA.

    Raises:
        ChatServiceError: Si el proveedor de IA falla (convertido a
            HTTP 503 por el manejador de excepciones global).
    """
    return await service.process_message(request)


@app.get(
    "/chat/history/{session_id}",
    response_model=list[ChatHistoryDTO],
    tags=["chat"],
)
def get_chat_history(
    session_id: str,
    service: ChatServiceDep,
    limit: int = 20,
) -> list[ChatHistoryDTO]:
    """Obtiene el historial reciente de una sesión.

    Args:
        session_id: Identificador de la sesión.
        service: Servicio de chat inyectado.
        limit: Número máximo de mensajes a retornar (por defecto 20).

    Returns:
        Lista de ``ChatHistoryDTO`` en orden cronológico.
    """
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'limit' debe ser mayor a cero.",
        )
    return service.get_session_history(session_id, limit)


@app.delete("/chat/history/{session_id}", tags=["chat"])
def delete_chat_history(
    session_id: str, service: ChatServiceDep
) -> dict:
    """Elimina todo el historial de una sesión.

    Args:
        session_id: Identificador de la sesión a limpiar.
        service: Servicio de chat inyectado.

    Returns:
        Diccionario con la cantidad de mensajes eliminados.
    """
    eliminados = service.clear_session_history(session_id)
    return {"session_id": session_id, "deleted_messages": eliminados}
