"""Caso de uso: conversación inteligente con el cliente.

``ChatService`` coordina los componentes que hacen falta para
responder un mensaje:

1. El catálogo, para saber qué productos existen.
2. El historial de mensajes, para mantener el hilo.
3. El proveedor de LLM, que genera la respuesta final.

El servicio se mantiene agnóstico respecto al proveedor de IA: usa
un objeto genérico con un método ``generate_response`` y no sabe si
por dentro es Gemini, Claude u otro.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol

from src.config import settings
from src.domain.entities import ChatContext, ChatMessage
from src.domain.exceptions import ChatServiceError
from src.domain.repositories import IChatRepository, IProductRepository

from .dtos import (
    ChatHistoryDTO,
    ChatMessageRequestDTO,
    ChatMessageResponseDTO,
)

logger = logging.getLogger(__name__)


class IAService(Protocol):
    """Protocolo estructural que describe un proveedor de LLM.

    Cualquier clase que implemente un método ``generate_response``
    con esta firma puede inyectarse en ``ChatService``, sin
    necesidad de heredar explícitamente de este protocolo.
    """

    async def generate_response(
        self,
        user_message: str,
        products: list,
        context: ChatContext,
    ) -> str:
        """Genera una respuesta contextual al mensaje del usuario.

        Args:
            user_message: Texto enviado por el usuario.
            products: Catálogo disponible en el momento de responder.
            context: Ventana conversacional reciente.

        Returns:
            La respuesta generada por el LLM como texto plano.
        """
        ...


class ChatService:
    """Orquesta la interacción conversacional con el asistente de IA.

    Esta clase sigue el patrón *service layer*: cada método público
    representa un caso de uso del cliente (procesar mensaje, ver
    historial, borrar conversación). Todos los detalles técnicos
    (base de datos, llamadas HTTP al LLM) quedan encapsulados tras
    las dependencias inyectadas.

    Attributes:
        product_repo: Repositorio de productos para obtener el catálogo.
        chat_repo: Repositorio donde se persiste el historial.
        ai_service: Proveedor de LLM que genera las respuestas.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        chat_repo: IChatRepository,
        ai_service: IAService,
    ) -> None:
        """Inicializa el servicio con todas sus dependencias.

        Args:
            product_repo: Implementación concreta de ``IProductRepository``.
            chat_repo: Implementación concreta de ``IChatRepository``.
            ai_service: Objeto compatible con ``IAService``.
        """
        self.product_repo = product_repo
        self.chat_repo = chat_repo
        self.ai_service = ai_service

    async def process_message(
        self, request: ChatMessageRequestDTO
    ) -> ChatMessageResponseDTO:
        """Procesa un turno completo de la conversación.

        El flujo es:

        1. Carga el catálogo vigente.
        2. Recupera los últimos mensajes de la sesión.
        3. Construye un ``ChatContext`` y delega en el LLM.
        4. Persiste tanto el mensaje del usuario como la respuesta.
        5. Devuelve el turno completo al cliente.

        Args:
            request: Mensaje del usuario con su ``session_id``.

        Returns:
            ``ChatMessageResponseDTO`` con la respuesta del asistente.

        Raises:
            ChatServiceError: Si el proveedor de IA falla o si ocurre
                cualquier problema al persistir los mensajes.

        Example:
            >>> request = ChatMessageRequestDTO(
            ...     session_id="cliente_001",
            ...     message="Busco tenis para trotar por El Poblado",
            ... )
            >>> response = await chat_service.process_message(request)
            >>> print(response.assistant_message)
        """
        try:
            # Paso 1: catálogo actual.
            productos = self.product_repo.get_all()

            # Paso 2: últimos mensajes de la sesión para dar contexto.
            recientes = self.chat_repo.get_recent_messages(
                request.session_id, settings.chat_context_window
            )
            contexto = ChatContext(
                messages=recientes,
                max_messages=settings.chat_context_window,
            )

            # Paso 3: generar la respuesta con el LLM.
            respuesta_texto = await self.ai_service.generate_response(
                user_message=request.message,
                products=productos,
                context=contexto,
            )

            # Paso 4: persistir los dos mensajes del turno.
            ahora = datetime.utcnow()
            mensaje_usuario = ChatMessage(
                id=None,
                session_id=request.session_id,
                role="user",
                message=request.message,
                timestamp=ahora,
            )
            mensaje_asistente = ChatMessage(
                id=None,
                session_id=request.session_id,
                role="assistant",
                message=respuesta_texto,
                timestamp=datetime.utcnow(),
            )
            self.chat_repo.save_message(mensaje_usuario)
            self.chat_repo.save_message(mensaje_asistente)

            # Paso 5: devolver el turno al cliente.
            return ChatMessageResponseDTO(
                session_id=request.session_id,
                user_message=request.message,
                assistant_message=respuesta_texto,
                timestamp=mensaje_asistente.timestamp,
            )
        except ChatServiceError:
            raise
        except Exception as exc:
            logger.exception("Fallo al procesar mensaje de chat.")
            raise ChatServiceError(
                f"No fue posible procesar el mensaje: {exc}"
            ) from exc

    def get_session_history(
        self, session_id: str, limit: int = 20
    ) -> list[ChatHistoryDTO]:
        """Devuelve el historial paginado de una sesión.

        Args:
            session_id: Identificador de la sesión.
            limit: Cantidad máxima de mensajes a retornar.

        Returns:
            Lista de ``ChatHistoryDTO`` en orden cronológico.
        """
        mensajes = self.chat_repo.get_session_history(session_id, limit)
        return [
            ChatHistoryDTO(
                id=m.id or 0,
                role=m.role,
                message=m.message,
                timestamp=m.timestamp,
            )
            for m in mensajes
        ]

    def clear_session_history(self, session_id: str) -> int:
        """Elimina todo el historial de una sesión.

        Args:
            session_id: Identificador de la sesión a limpiar.

        Returns:
            Cantidad de mensajes eliminados.
        """
        return self.chat_repo.delete_session_history(session_id)
