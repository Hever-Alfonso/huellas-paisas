"""Tests del ``ProductService``.

Usan repositorios reales contra una base SQLite en memoria, así
se ejercita también la capa de infraestructura sin depender de
archivos en disco.
"""

from __future__ import annotations

import pytest

from src.application.dtos import ProductDTO
from src.application.product_service import ProductService
from src.domain.exceptions import (
    InvalidProductDataError,
    ProductNotFoundError,
)


@pytest.fixture
def service(product_repo) -> ProductService:
    return ProductService(product_repo)


def _dto(**overrides) -> ProductDTO:
    datos = dict(
        name="New Balance 574",
        brand="New Balance",
        category="Casual",
        size="42",
        color="Gris",
        price=109.0,
        stock=3,
        description="Clásico moderno",
    )
    datos.update(overrides)
    return ProductDTO(**datos)


class TestProductService:
    """Tests del ``ProductService`` con repositorio real contra SQLite en memoria."""

    def test_get_all_con_catalogo_vacio(self, service):
        """Devuelve lista vacía cuando no hay productos en la base."""
        assert service.get_all_products() == []

    def test_create_y_get_all(self, service):
        """Crear un producto y luego listarlo debe devolver ese único registro."""
        creado = service.create_product(_dto())
        assert creado.id is not None
        todos = service.get_all_products()
        assert len(todos) == 1
        assert todos[0].brand == "New Balance"

    def test_get_product_by_id_existente(self, service):
        """Recuperar por ID un producto recién creado debe retornar el mismo objeto."""
        creado = service.create_product(_dto())
        encontrado = service.get_product_by_id(creado.id)
        assert encontrado.id == creado.id

    def test_get_product_by_id_no_existente_lanza_error(self, service):
        """Buscar un ID inexistente debe lanzar ``ProductNotFoundError``."""
        with pytest.raises(ProductNotFoundError):
            service.get_product_by_id(999)

    def test_get_available_products_excluye_sin_stock(
        self, service, sample_products
    ):
        """Los productos con stock 0 no deben aparecer en la lista de disponibles."""
        disponibles = service.get_available_products()
        nombres = {p.name for p in disponibles}
        assert "Oxford Clásico" not in nombres  # stock = 0
        assert len(disponibles) == 2

    def test_get_products_by_brand_case_insensitive(
        self, service, sample_products
    ):
        """Filtrar por marca debe ser insensible a mayúsculas y minúsculas."""
        resultado = service.get_products_by_brand("nike")
        assert len(resultado) == 1
        assert resultado[0].brand == "Nike"

    def test_get_products_by_category(self, service, sample_products):
        """Filtrar por categoría debe retornar solo los productos de esa categoría."""
        resultado = service.get_products_by_category("Casual")
        assert len(resultado) == 1
        assert resultado[0].brand == "Puma"

    def test_update_product(self, service):
        """Actualizar un campo debe persistir el nuevo valor correctamente."""
        creado = service.create_product(_dto(price=100.0))
        actualizado = service.update_product(
            creado.id, _dto(price=125.0)
        )
        assert actualizado.price == 125.0

    def test_update_product_no_existente_lanza_error(self, service):
        """Actualizar un ID inexistente debe lanzar ``ProductNotFoundError``."""
        with pytest.raises(ProductNotFoundError):
            service.update_product(999, _dto())

    def test_delete_product(self, service):
        """Eliminar un producto debe hacer que ya no sea recuperable por ID."""
        creado = service.create_product(_dto())
        service.delete_product(creado.id)
        with pytest.raises(ProductNotFoundError):
            service.get_product_by_id(creado.id)

    def test_delete_product_no_existente_lanza_error(self, service):
        """Eliminar un ID inexistente debe lanzar ``ProductNotFoundError``."""
        with pytest.raises(ProductNotFoundError):
            service.delete_product(999)

    def test_create_product_con_precio_invalido_lanza_error(self, service):
        """Un DTO con precio negativo construido con ``model_construct`` debe lanzar error en el servicio."""
        # model_construct salta la validación de Pydantic para ejercitar
        # la validación en la capa de dominio.
        dto_invalido = ProductDTO.model_construct(
            id=None,
            name="Malo",
            brand="X",
            category="Y",
            size="40",
            color="rojo",
            price=-10.0,
            stock=1,
            description="",
        )
        with pytest.raises(InvalidProductDataError):
            service.create_product(dto_invalido)
