"""Implementación SQL del repositorio del chat.

Persiste y recupera mensajes conversacionales agrupados por
``session_id``. Se encarga de devolver los mensajes en orden
cronológico, invirtiendo la consulta cuando conviene usar índices
descendentes por ``timestamp``.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.domain.entities import ChatMessage
from src.domain.repositories import IChatRepository
from src.infrastructure.db.models import ChatMemoryModel


class SQLChatRepository(IChatRepository):
    """Repositorio del historial de chat respaldado por SQLAlchemy.

    Attributes:
        db: Sesión activa de SQLAlchemy inyectada desde FastAPI.
    """

    def __init__(self, db: Session) -> None:
        """Inicializa el repositorio con una sesión.

        Args:
            db: Sesión abierta de SQLAlchemy.
        """
        self.db = db

    def save_message(self, message: ChatMessage) -> ChatMessage:
        """Guarda un mensaje en la base de datos.

        Args:
            message: Entidad ``ChatMessage`` a persistir.

        Returns:
            La misma entidad con su ``id`` asignado.
        """
        modelo = ChatMemoryModel(
            session_id=message.session_id,
            role=message.role,
            message=message.message,
            timestamp=message.timestamp,
        )
        self.db.add(modelo)
        self.db.commit()
        self.db.refresh(modelo)
        return self._model_to_entity(modelo)

    def get_session_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[ChatMessage]:
        """Devuelve el historial de una sesión en orden cronológico.

        Args:
            session_id: Identificador de la sesión.
            limit: Si se pasa, se devuelven los últimos ``limit``
                mensajes; si es ``None``, se devuelven todos.

        Returns:
            Lista de ``ChatMessage`` en orden cronológico ascendente.
        """
        if limit is None:
            stmt = (
                select(ChatMemoryModel)
                .where(ChatMemoryModel.session_id == session_id)
                .order_by(ChatMemoryModel.timestamp.asc())
            )
            modelos = self.db.execute(stmt).scalars().all()
            return [self._model_to_entity(m) for m in modelos]

        # Para obtener los últimos N, consultamos descendente y luego
        # invertimos la lista, aprovechando el índice sobre timestamp.
        stmt = (
            select(ChatMemoryModel)
            .where(ChatMemoryModel.session_id == session_id)
            .order_by(ChatMemoryModel.timestamp.desc())
            .limit(limit)
        )
        modelos = list(self.db.execute(stmt).scalars().all())
        modelos.reverse()
        return [self._model_to_entity(m) for m in modelos]

    def delete_session_history(self, session_id: str) -> int:
        """Elimina todos los mensajes de una sesión.

        Args:
            session_id: Identificador de la sesión.

        Returns:
            Cantidad de filas eliminadas.
        """
        stmt = delete(ChatMemoryModel).where(
            ChatMemoryModel.session_id == session_id
        )
        resultado = self.db.execute(stmt)
        self.db.commit()
        return resultado.rowcount or 0

    def get_recent_messages(
        self, session_id: str, count: int
    ) -> list[ChatMessage]:
        """Obtiene los últimos ``count`` mensajes de una sesión.

        Args:
            session_id: Identificador de la sesión.
            count: Máximo de mensajes a recuperar.

        Returns:
            Lista en orden cronológico ascendente, con hasta ``count``
            mensajes.
        """
        if count <= 0:
            return []
        return self.get_session_history(session_id, limit=count)

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_entity(modelo: ChatMemoryModel) -> ChatMessage:
        """Convierte un modelo ORM en entidad del dominio.

        Args:
            modelo: Registro ORM de ``chat_memory``.

        Returns:
            Entidad ``ChatMessage`` equivalente.
        """
        return ChatMessage(
            id=modelo.id,
            session_id=modelo.session_id,
            role=modelo.role,
            message=modelo.message,
            timestamp=modelo.timestamp,
        )
