"""Data Transfer Objects (DTOs) de la capa de aplicación.

Los DTOs son la frontera de datos entre el mundo externo (HTTP,
clientes, tests) y el dominio. Están construidos sobre Pydantic
porque ofrece:

* Validación automática de tipos y reglas.
* Serialización a JSON lista para FastAPI.
* Documentación OpenAPI sin código extra.

Aquí se usa la API moderna de Pydantic v2 (``field_validator`` y
``ConfigDict``). Los validadores ``v1`` están obsoletos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductDTO(BaseModel):
    """DTO para lectura y escritura de productos.

    Se utiliza como cuerpo de entrada en ``POST/PUT`` y como modelo
    de respuesta en los endpoints que devuelven productos.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(
        default=None,
        description="Identificador único. Nulo al crear.",
        examples=[1],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre comercial del modelo.",
        examples=["Bosi Oxford Clásico"],
    )
    brand: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Marca del fabricante.",
        examples=["Bosi"],
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Categoría de uso del producto.",
        examples=["Formal"],
    )
    size: str = Field(..., description="Talla del calzado.", examples=["42"])
    color: str = Field(..., description="Color principal.", examples=["Café"])
    price: float = Field(..., description="Precio en USD.", examples=[189.0])
    stock: int = Field(..., description="Unidades disponibles.", examples=[4])
    description: str = Field(
        default="",
        description="Descripción corta del producto.",
        examples=["Cuero colombiano con suela antideslizante."],
    )

    @field_validator("price")
    @classmethod
    def _validar_precio(cls, v: float) -> float:
        """Garantiza que el precio sea estrictamente positivo.

        Args:
            v: Valor propuesto para el precio.

        Returns:
            El mismo valor si es válido.

        Raises:
            ValueError: Si el precio es menor o igual a cero.
        """
        if v <= 0:
            raise ValueError("El precio debe ser mayor a 0.")
        return v

    @field_validator("stock")
    @classmethod
    def _validar_stock(cls, v: int) -> int:
        """Garantiza que el stock nunca sea negativo.

        Args:
            v: Cantidad propuesta.

        Returns:
            El mismo valor si es válido.

        Raises:
            ValueError: Si el valor es negativo.
        """
        if v < 0:
            raise ValueError("El stock no puede ser negativo.")
        return v


class ChatMessageRequestDTO(BaseModel):
    """DTO de entrada para el endpoint ``POST /chat``.

    Recibe el mensaje que el usuario quiere enviar al asistente,
    junto con el identificador de sesión que permite agrupar la
    conversación.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Identificador único de la sesión del usuario.",
        examples=["cliente_001"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mensaje del usuario al asistente.",
        examples=["Hola, busco tenis Nike para correr."],
    )

    @field_validator("message", "session_id")
    @classmethod
    def _no_solo_espacios(cls, v: str) -> str:
        """Rechaza cadenas que solo contienen espacios en blanco.

        Args:
            v: Cadena a validar.

        Returns:
            La cadena recortada si contiene caracteres útiles.

        Raises:
            ValueError: Si la cadena está vacía tras el ``strip``.
        """
        limpio = v.strip()
        if not limpio:
            raise ValueError("El campo no puede estar vacío.")
        return limpio


class ChatMessageResponseDTO(BaseModel):
    """DTO de salida para el endpoint ``POST /chat``.

    Devuelve tanto el mensaje del usuario como la respuesta que el
    asistente generó, para que el cliente pueda renderizar el turno
    completo.
    """

    session_id: str = Field(..., description="ID de la sesión.")
    user_message: str = Field(..., description="Mensaje original del usuario.")
    assistant_message: str = Field(
        ..., description="Respuesta generada por el asistente de IA."
    )
    timestamp: datetime = Field(
        ..., description="Instante en que se generó la respuesta."
    )


class ChatHistoryDTO(BaseModel):
    """DTO para listar el historial de una sesión.

    Es un proyección plana de ``ChatMessage`` pensada para ser
    consumida por el frontend.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str = Field(
        ..., description="Emisor del mensaje: 'user' o 'assistant'."
    )
    message: str
    timestamp: datetime


class HealthDTO(BaseModel):
    """Respuesta del endpoint ``GET /health`` para monitoreo."""

    status: str = Field(..., examples=["ok"])
    timestamp: datetime
    environment: str
    version: str


class StatsDTO(BaseModel):
    """Respuesta del endpoint ``GET /stats`` con métricas básicas."""

    total_products: int = Field(..., description="Total de productos en catálogo.")
    products_in_stock: int = Field(
        ..., description="Productos con al menos una unidad."
    )
    total_messages: int = Field(
        ..., description="Mensajes almacenados en todas las sesiones."
    )
