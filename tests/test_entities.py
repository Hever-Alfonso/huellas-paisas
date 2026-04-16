"""Tests de las entidades del dominio.

Estos tests no tocan ni FastAPI, ni SQLAlchemy, ni Gemini. Ejercen
las reglas de negocio puras del dominio.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.entities import ChatContext, ChatMessage, Product


class TestProduct:
    """Pruebas para la entidad ``Product``."""

    def _crear(self, **overrides) -> Product:
        datos = dict(
            id=None,
            name="Air Zoom Pegasus 40",
            brand="Nike",
            category="Running",
            size="42",
            color="Negro",
            price=139.0,
            stock=5,
            description="Tenis de prueba",
        )
        datos.update(overrides)
        return Product(**datos)

    def test_producto_valido_se_crea_sin_errores(self):
        producto = self._crear()
        assert producto.name == "Air Zoom Pegasus 40"
        assert producto.is_available() is True

    def test_precio_cero_lanza_error(self):
        with pytest.raises(ValueError, match="precio"):
            self._crear(price=0)

    def test_precio_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="precio"):
            self._crear(price=-10)

    def test_stock_negativo_lanza_error(self):
        with pytest.raises(ValueError, match="stock"):
            self._crear(stock=-1)

    def test_nombre_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="nombre"):
            self._crear(name="")

    def test_nombre_solo_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="nombre"):
            self._crear(name="   ")

    def test_marca_vacia_lanza_error(self):
        with pytest.raises(ValueError, match="marca"):
            self._crear(brand="")

    def test_is_available_con_stock_cero_retorna_false(self):
        producto = self._crear(stock=0)
        assert producto.is_available() is False

    def test_reduce_stock_descuenta_correctamente(self):
        producto = self._crear(stock=5)
        producto.reduce_stock(2)
        assert producto.stock == 3

    def test_reduce_stock_con_cantidad_negativa_lanza_error(self):
        producto = self._crear(stock=5)
        with pytest.raises(ValueError, match="positiva"):
            producto.reduce_stock(-1)

    def test_reduce_stock_con_cantidad_cero_lanza_error(self):
        producto = self._crear(stock=5)
        with pytest.raises(ValueError, match="positiva"):
            producto.reduce_stock(0)

    def test_reduce_stock_excediendo_existencias_lanza_error(self):
        producto = self._crear(stock=3)
        with pytest.raises(ValueError, match="insuficiente"):
            producto.reduce_stock(10)

    def test_increase_stock_suma_correctamente(self):
        producto = self._crear(stock=5)
        producto.increase_stock(7)
        assert producto.stock == 12

    def test_increase_stock_con_cantidad_negativa_lanza_error(self):
        producto = self._crear(stock=5)
        with pytest.raises(ValueError, match="positiva"):
            producto.increase_stock(-3)


class TestChatMessage:
    """Pruebas para la entidad ``ChatMessage``."""

    def _crear(self, **overrides) -> ChatMessage:
        datos = dict(
            id=None,
            session_id="sesion_001",
            role="user",
            message="Hola, busco tenis",
            timestamp=datetime(2024, 1, 15, 10, 30),
        )
        datos.update(overrides)
        return ChatMessage(**datos)

    def test_mensaje_valido_se_crea_sin_errores(self):
        mensaje = self._crear()
        assert mensaje.session_id == "sesion_001"

    def test_rol_invalido_lanza_error(self):
        with pytest.raises(ValueError, match="Rol"):
            self._crear(role="bot")

    def test_session_id_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="session_id"):
            self._crear(session_id="")

    def test_mensaje_vacio_lanza_error(self):
        with pytest.raises(ValueError, match="mensaje"):
            self._crear(message="")

    def test_is_from_user_para_rol_user(self):
        mensaje = self._crear(role="user")
        assert mensaje.is_from_user() is True
        assert mensaje.is_from_assistant() is False

    def test_is_from_assistant_para_rol_assistant(self):
        mensaje = self._crear(role="assistant")
        assert mensaje.is_from_user() is False
        assert mensaje.is_from_assistant() is True


class TestChatContext:
    """Pruebas para el value object ``ChatContext``."""

    def _msg(self, role: str, texto: str) -> ChatMessage:
        return ChatMessage(
            id=None,
            session_id="s1",
            role=role,
            message=texto,
            timestamp=datetime.utcnow(),
        )

    def test_contexto_vacio(self):
        ctx = ChatContext(messages=[])
        assert ctx.is_empty() is True
        assert ctx.format_for_prompt() == ""
        assert ctx.get_recent_messages() == []

    def test_respeta_max_messages(self):
        mensajes = [self._msg("user", f"msg{i}") for i in range(10)]
        ctx = ChatContext(messages=mensajes, max_messages=3)
        recientes = ctx.get_recent_messages()
        assert len(recientes) == 3
        assert recientes[0].message == "msg7"
        assert recientes[-1].message == "msg9"

    def test_format_for_prompt_genera_etiquetas(self):
        ctx = ChatContext(
            messages=[
                self._msg("user", "Hola"),
                self._msg("assistant", "¡Qué más pues!"),
            ]
        )
        resultado = ctx.format_for_prompt()
        assert "Usuario: Hola" in resultado
        assert "Asistente: ¡Qué más pues!" in resultado

    def test_max_messages_cero_retorna_vacio(self):
        mensajes = [self._msg("user", "hola")]
        ctx = ChatContext(messages=mensajes, max_messages=0)
        assert ctx.get_recent_messages() == []
