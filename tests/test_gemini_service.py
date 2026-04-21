"""Tests de ``GeminiService`` sin llamar a la API real de Google.

Cubre el modo degradado (sin credenciales), los helpers de construcción
del prompt y el comportamiento ante respuestas vacías o errores del SDK,
usando ``unittest.mock`` para aislar completamente la llamada a Google.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities import ChatContext, ChatMessage, Product
from src.domain.exceptions import ChatServiceError
from src.infrastructure.llm_providers.gemini_service import GeminiService


def _producto(stock: int = 5, producto_id: int = 1) -> Product:
    """Crea un producto de prueba con valores predecibles.

    Args:
        stock: Unidades disponibles. Por defecto 5.
        producto_id: Identificador numérico. Por defecto 1.

    Returns:
        Instancia de ``Product`` lista para usar en los tests.
    """
    return Product(
        id=producto_id,
        name="Air Zoom Pegasus 40",
        brand="Nike",
        category="Running",
        size="42",
        color="Negro",
        price=139.0,
        stock=stock,
        description="Tenis de prueba.",
    )


def _contexto_vacio() -> ChatContext:
    """Crea un ``ChatContext`` sin mensajes previos.

    Returns:
        ``ChatContext`` con lista de mensajes vacía.
    """
    return ChatContext(messages=[])


def _servicio_sin_key() -> GeminiService:
    """Crea un ``GeminiService`` en modo degradado mockeando las credenciales.

    Parchea ``settings`` en el módulo de Gemini para que ``gemini_api_key``
    devuelva ``None``, lo que activa el modo sin credenciales sin modificar
    la configuración global de la app.

    Returns:
        ``GeminiService`` con ``_model`` en ``None``.
    """
    mock_cfg = MagicMock()
    mock_cfg.gemini_api_key = None
    mock_cfg.gemini_model = "gemini-2.5-flash"
    with patch("src.infrastructure.llm_providers.gemini_service.settings", mock_cfg):
        return GeminiService()


class TestModoDegradado:
    """Verifica el comportamiento de ``GeminiService`` sin credenciales."""

    def test_sin_api_key_modelo_es_none(self):
        """Sin API key el modelo interno debe quedar como ``None``."""
        servicio = _servicio_sin_key()
        assert servicio._model is None

    async def test_sin_api_key_devuelve_fallback_con_santi(self):
        """Sin API key la respuesta menciona a Santi y Huellas Paisas."""
        servicio = _servicio_sin_key()
        respuesta = await servicio.generate_response(
            "Hola", [_producto()], _contexto_vacio()
        )
        assert "Santi" in respuesta
        assert "Huellas Paisas" in respuesta

    async def test_fallback_catalogo_vacio_devuelve_texto(self):
        """Fallback con catálogo vacío retorna cadena no vacía."""
        servicio = _servicio_sin_key()
        respuesta = await servicio.generate_response(
            "Hola", [], _contexto_vacio()
        )
        assert isinstance(respuesta, str)
        assert len(respuesta) > 0

    async def test_fallback_todos_agotados_devuelve_cadena(self):
        """Fallback con stock 0 en todos los productos retorna texto no vacío."""
        servicio = _servicio_sin_key()
        respuesta = await servicio.generate_response(
            "¿Tienen algo?", [_producto(stock=0)], _contexto_vacio()
        )
        assert isinstance(respuesta, str)
        assert len(respuesta) > 0


class TestFormatProductosInfo:
    """Tests del helper estático que convierte el catálogo en texto."""

    def test_lista_vacia_retorna_cadena_vacia(self):
        """Sin productos el resultado debe ser cadena vacía."""
        assert GeminiService.format_products_info([]) == ""

    def test_incluye_marca_nombre_y_precio(self):
        """El texto debe incluir la marca, el nombre y el precio del producto."""
        texto = GeminiService.format_products_info([_producto()])
        assert "Nike" in texto
        assert "Air Zoom Pegasus 40" in texto
        assert "139.00" in texto

    def test_producto_agotado_indica_agotado(self):
        """Un producto con stock 0 debe aparecer como AGOTADO."""
        texto = GeminiService.format_products_info([_producto(stock=0)])
        assert "AGOTADO" in texto

    def test_producto_con_stock_muestra_unidades(self):
        """Un producto con stock > 0 debe mostrar el número de unidades."""
        texto = GeminiService.format_products_info([_producto(stock=7)])
        assert "7 unidades" in texto

    def test_multiples_productos_una_linea_por_producto(self):
        """Cada producto debe aparecer en su propia línea."""
        p1 = _producto(producto_id=1)
        p2 = _producto(producto_id=2)
        texto = GeminiService.format_products_info([p1, p2])
        lineas = [linea for linea in texto.splitlines() if linea.strip()]
        assert len(lineas) == 2


class TestBuildPrompt:
    """Tests del método privado que ensambla el prompt completo."""

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    def test_prompt_incluye_instrucciones_de_sistema(self, mock_genai):
        """El prompt debe contener el nombre del asistente Santi."""
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = MagicMock()
        servicio = GeminiService(api_key="clave-falsa", model_name="gemini-2.5-flash")
        prompt = servicio._build_prompt("Hola", [_producto()], _contexto_vacio())
        assert "Santi" in prompt
        assert "PRODUCTOS DISPONIBLES" in prompt

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    def test_prompt_incluye_mensaje_del_usuario(self, mock_genai):
        """El mensaje del usuario debe estar presente al final del prompt."""
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = MagicMock()
        servicio = GeminiService(api_key="clave-falsa", model_name="gemini-2.5-flash")
        prompt = servicio._build_prompt(
            "Busco zapatillas para trail", [_producto()], _contexto_vacio()
        )
        assert "Busco zapatillas para trail" in prompt

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    def test_prompt_con_historial_incluye_seccion_conversacion(self, mock_genai):
        """Si hay historial, el prompt debe incluir la sección de conversación previa."""
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = MagicMock()
        servicio = GeminiService(api_key="clave-falsa", model_name="gemini-2.5-flash")
        historial = [
            ChatMessage(
                id=None,
                session_id="s1",
                role="user",
                message="¿Tienen Adidas?",
                timestamp=datetime.utcnow(),
            )
        ]
        ctx = ChatContext(messages=historial)
        prompt = servicio._build_prompt("¿Y en talla 42?", [_producto()], ctx)
        assert "CONVERSACIÓN PREVIA" in prompt
        assert "¿Tienen Adidas?" in prompt


class TestGenerateResponseConMock:
    """Tests de ``generate_response`` con el SDK de Gemini simulado."""

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    async def test_llama_gemini_y_retorna_texto(self, mock_genai):
        """Cuando Gemini responde correctamente se retorna el texto recibido."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            return_value=MagicMock(text="¡Con mucho gusto! Te recomiendo el Nike.")
        )
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = mock_model

        servicio = GeminiService(api_key="clave-valida", model_name="gemini-2.5-flash")
        respuesta = await servicio.generate_response(
            "¿Tienen Nike?", [_producto()], _contexto_vacio()
        )
        assert respuesta == "¡Con mucho gusto! Te recomiendo el Nike."
        mock_model.generate_content_async.assert_called_once()

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    async def test_respuesta_vacia_activa_fallback(self, mock_genai):
        """Si Gemini devuelve texto vacío, la respuesta debe usar el fallback."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            return_value=MagicMock(text="   ")
        )
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = mock_model

        servicio = GeminiService(api_key="clave-valida", model_name="gemini-2.5-flash")
        respuesta = await servicio.generate_response(
            "Hola", [_producto()], _contexto_vacio()
        )
        assert "Santi" in respuesta

    @patch("src.infrastructure.llm_providers.gemini_service.genai")
    async def test_error_de_api_lanza_chat_service_error(self, mock_genai):
        """Un error en la API de Gemini debe convertirse en ``ChatServiceError``."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=RuntimeError("cuota excedida")
        )
        mock_genai.configure.return_value = None
        mock_genai.GenerativeModel.return_value = mock_model

        servicio = GeminiService(api_key="clave-valida", model_name="gemini-2.5-flash")
        with pytest.raises(ChatServiceError):
            await servicio.generate_response(
                "Hola", [_producto()], _contexto_vacio()
            )
