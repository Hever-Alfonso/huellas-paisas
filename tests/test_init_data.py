"""Tests de idempotencia y contenido del catálogo inicial.

Verifica que ``load_initial_data`` inserte los diez productos semilla,
que sea idempotente al llamarla varias veces y que el catálogo cumpla
las reglas de negocio básicas (precios positivos, marcas, categorías).
"""

from __future__ import annotations

from src.infrastructure.db.init_data import _CATALOGO_INICIAL, load_initial_data


class TestLoadInitialData:
    """Tests del módulo de carga de datos iniciales del catálogo."""

    def test_inserta_diez_productos(self, db_session):
        """La primera llamada debe insertar los 10 productos del catálogo."""
        insertados = load_initial_data(db_session)
        assert insertados == 10

    def test_es_idempotente(self, db_session):
        """Una segunda llamada no debe insertar nada ni lanzar errores."""
        load_initial_data(db_session)
        segunda_llamada = load_initial_data(db_session)
        assert segunda_llamada == 0

    def test_contiene_marcas_colombianas(self, db_session):
        """El catálogo debe incluir las marcas colombianas Bosi y Vélez."""
        marcas = {p["brand"] for p in _CATALOGO_INICIAL}
        assert "Bosi" in marcas
        assert "Vélez" in marcas

    def test_al_menos_un_producto_agotado(self, db_session):
        """El catálogo debe tener al menos un producto con stock cero."""
        agotados = [p for p in _CATALOGO_INICIAL if p["stock"] == 0]
        assert len(agotados) >= 1

    def test_todos_los_precios_son_positivos(self, db_session):
        """Ningún producto del catálogo debe tener precio menor o igual a cero."""
        for producto in _CATALOGO_INICIAL:
            assert producto["price"] > 0, (
                f"Precio inválido en '{producto['name']}': {producto['price']}"
            )

    def test_todos_tienen_nombre_y_marca(self, db_session):
        """Todos los productos deben tener nombre y marca no vacíos."""
        for producto in _CATALOGO_INICIAL:
            assert producto["name"].strip(), "Producto sin nombre encontrado."
            assert producto["brand"].strip(), "Producto sin marca encontrado."

    def test_catalogo_tiene_variedad_de_categorias(self, db_session):
        """El catálogo debe cubrir al menos 3 categorías distintas."""
        categorias = {p["category"] for p in _CATALOGO_INICIAL}
        assert len(categorias) >= 3
