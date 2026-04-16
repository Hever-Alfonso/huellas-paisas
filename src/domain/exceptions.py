"""Excepciones específicas del dominio de Huellas Paisas.

Las excepciones de esta capa representan **errores de negocio**, no
fallos técnicos. Por ejemplo, "producto no encontrado" es un error
de negocio, mientras que "la conexión TCP falló" es un error técnico.

Distinguir ambos tipos permite que la capa de infraestructura (por
ejemplo, FastAPI) traduzca cada error a la respuesta HTTP adecuada
(404 para lo primero, 500 para lo segundo).
"""

from __future__ import annotations

from typing import Optional


class DomainError(Exception):
    """Excepción base para todos los errores del dominio.

    Heredar de esta clase facilita capturar de forma genérica
    cualquier error de negocio con un único ``except DomainError``.

    Attributes:
        message: Mensaje descriptivo del error.
    """

    def __init__(self, message: str = "Error del dominio") -> None:
        """Inicializa la excepción.

        Args:
            message: Descripción legible del error.
        """
        self.message = message
        super().__init__(self.message)


class ProductNotFoundError(DomainError):
    """Se lanza cuando se consulta un producto que no existe.

    Attributes:
        product_id: ID del producto buscado, si se conoce.
    """

    def __init__(self, product_id: Optional[int] = None) -> None:
        """Construye la excepción con un mensaje útil.

        Args:
            product_id: Identificador del producto que no se encontró.
                Si se pasa, se incluye en el mensaje.
        """
        self.product_id = product_id
        if product_id is not None:
            mensaje = f"Producto con ID {product_id} no encontrado."
        else:
            mensaje = "Producto no encontrado."
        super().__init__(mensaje)


class InvalidProductDataError(DomainError):
    """Se lanza cuando los datos de un producto violan una regla de negocio.

    Por ejemplo: precio negativo, stock no entero, marca vacía, etc.
    """

    def __init__(self, message: str = "Datos de producto inválidos") -> None:
        """Construye la excepción con el motivo del fallo.

        Args:
            message: Descripción específica del dato inválido.
        """
        super().__init__(message)


class ChatServiceError(DomainError):
    """Se lanza cuando el servicio de chat no puede procesar un mensaje.

    Agrupa fallos como: el LLM no responde, el prompt es demasiado
    largo, la sesión está corrupta, etc.
    """

    def __init__(self, message: str = "Error en el servicio de chat") -> None:
        """Construye la excepción con el detalle del fallo.

        Args:
            message: Descripción del error ocurrido durante el chat.
        """
        super().__init__(message)


class EmptySessionError(DomainError):
    """Se lanza al intentar operar sobre una sesión que no tiene mensajes."""

    def __init__(self, session_id: str) -> None:
        """Construye la excepción indicando la sesión afectada.

        Args:
            session_id: Identificador de la sesión vacía.
        """
        super().__init__(f"La sesión '{session_id}' no tiene mensajes.")
