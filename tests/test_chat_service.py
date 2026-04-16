"""Tests del ``ChatService`` usando un doble de IA.

Verifican que el servicio orqueste correctamente:
- obtención de productos
- recuperación de historial
- llamado al LLM
- persistencia del turno completo
"""

from __future__ import annotations

import pytest

from src.application.chat_service import ChatService
from src.application.dtos import ChatMessageRequestDTO
from src.domain.exceptions import ChatServiceError


@pytest.fixture
def chat_service(product_repo, chat_repo, fake_ai) -> ChatService:
    return ChatService(
        product_repo=product_repo,
        chat_repo=chat_repo,
        ai_service=fake_ai,
    )


class TestChatService:

    async def test_process_message_persiste_dos_mensajes(
        self, chat_service, chat_repo, sample_products, fake_ai
    ):
        request = ChatMessageRequestDTO(
            session_id="cliente_001",
            message="Busco tenis para correr",
        )
        respuesta = await chat_service.process_message(request)

        assert respuesta.user_message == "Busco tenis para correr"
        assert respuesta.assistant_message == "Respuesta de prueba."
        historial = chat_repo.get_session_history("cliente_001")
        assert len(historial) == 2
        assert historial[0].role == "user"
        assert historial[1].role == "assistant"

    async def test_process_message_incluye_catalogo_al_llm(
        self, chat_service, sample_products, fake_ai
    ):
        request = ChatMessageRequestDTO(
            session_id="s1", message="hola"
        )
        await chat_service.process_message(request)
        assert fake_ai.last_products is not None
        assert len(fake_ai.last_products) == 3

    async def test_process_message_mantiene_contexto_entre_turnos(
        self, chat_service, fake_ai
    ):
        req1 = ChatMessageRequestDTO(session_id="s1", message="Hola")
        req2 = ChatMessageRequestDTO(session_id="s1", message="¿Y algo en 42?")

        await chat_service.process_message(req1)
        await chat_service.process_message(req2)

        # En el segundo turno el contexto ya debe tener mensajes previos.
        assert fake_ai.last_context is not None
        assert not fake_ai.last_context.is_empty()
        assert len(fake_ai.last_context.messages) >= 2

    async def test_process_message_aisla_sesiones(
        self, chat_service, chat_repo
    ):
        await chat_service.process_message(
            ChatMessageRequestDTO(session_id="userA", message="Hola A")
        )
        await chat_service.process_message(
            ChatMessageRequestDTO(session_id="userB", message="Hola B")
        )
        historial_a = chat_repo.get_session_history("userA")
        historial_b = chat_repo.get_session_history("userB")
        assert len(historial_a) == 2
        assert len(historial_b) == 2
        assert historial_a[0].message == "Hola A"
        assert historial_b[0].message == "Hola B"

    async def test_process_message_envuelve_errores_del_llm(
        self, product_repo, chat_repo
    ):
        class BrokenAI:
            async def generate_response(self, user_message, products, context):
                raise RuntimeError("Gemini caído")

        service = ChatService(product_repo, chat_repo, BrokenAI())
        with pytest.raises(ChatServiceError):
            await service.process_message(
                ChatMessageRequestDTO(session_id="s1", message="hola")
            )

    def test_clear_session_history(
        self, chat_service, chat_repo, sample_products
    ):
        import asyncio

        asyncio.run(
            chat_service.process_message(
                ChatMessageRequestDTO(session_id="s1", message="hola")
            )
        )
        eliminados = chat_service.clear_session_history("s1")
        assert eliminados == 2
        assert chat_repo.get_session_history("s1") == []

    async def test_get_session_history_retorna_dtos(
        self, chat_service
    ):
        await chat_service.process_message(
            ChatMessageRequestDTO(session_id="s1", message="Hola Santi")
        )
        historial = chat_service.get_session_history("s1")
        assert len(historial) == 2
        assert historial[0].role == "user"
        assert historial[0].message == "Hola Santi"
