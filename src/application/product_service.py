"""Caso de uso: gestión del catálogo de productos.

``ProductService`` es el punto de entrada de la capa de aplicación
para todo lo relacionado con productos. Recibe un repositorio por
inyección de dependencias y lo utiliza sin conocer su
implementación concreta.
"""

from __future__ import annotations

from typing import Optional

from src.domain.entities import Product
from src.domain.exceptions import (
    InvalidProductDataError,
    ProductNotFoundError,
)
from src.domain.repositories import IProductRepository

from .dtos import ProductDTO


class ProductService:
    """Orquesta los casos de uso asociados al catálogo de zapatos.

    Esta clase no conoce SQLAlchemy, FastAPI ni Pydantic por dentro:
    recibe DTOs, traduce a entidades del dominio, delega la
    persistencia en el repositorio inyectado y devuelve DTOs de
    vuelta. Así se garantiza que la lógica de negocio viva en el
    dominio y no se filtre hacia los extremos.

    Attributes:
        repo: Implementación concreta de ``IProductRepository``.
    """

    def __init__(self, repo: IProductRepository) -> None:
        """Inicializa el servicio con una dependencia de repositorio.

        Args:
            repo: Cualquier objeto que cumpla el contrato
                ``IProductRepository``.
        """
        self.repo = repo

    def get_all_products(self) -> list[ProductDTO]:
        """Lista todos los productos del catálogo.

        Returns:
            Lista de ``ProductDTO``, posiblemente vacía.
        """
        productos = self.repo.get_all()
        return [self._to_dto(p) for p in productos]

    def get_product_by_id(self, product_id: int) -> ProductDTO:
        """Obtiene un producto específico por su identificador.

        Args:
            product_id: ID del producto buscado.

        Returns:
            DTO con los datos del producto encontrado.

        Raises:
            ProductNotFoundError: Si no existe un producto con ese ID.
        """
        producto = self.repo.get_by_id(product_id)
        if producto is None:
            raise ProductNotFoundError(product_id)
        return self._to_dto(producto)

    def get_available_products(self) -> list[ProductDTO]:
        """Filtra los productos que tienen al menos una unidad en stock.

        Returns:
            Lista de productos disponibles para la venta.
        """
        productos = self.repo.get_all()
        return [self._to_dto(p) for p in productos if p.is_available()]

    def get_products_by_brand(self, brand: str) -> list[ProductDTO]:
        """Busca productos por marca.

        Args:
            brand: Nombre de la marca (comparación sin distinguir
                mayúsculas/minúsculas, manejada por el repositorio).

        Returns:
            Lista de productos de esa marca.
        """
        productos = self.repo.get_by_brand(brand)
        return [self._to_dto(p) for p in productos]

    def get_products_by_category(self, category: str) -> list[ProductDTO]:
        """Busca productos por categoría de uso.

        Args:
            category: Nombre de la categoría (``"Running"``, ``"Casual"``...).

        Returns:
            Lista de productos en esa categoría.
        """
        productos = self.repo.get_by_category(category)
        return [self._to_dto(p) for p in productos]

    def create_product(self, dto: ProductDTO) -> ProductDTO:
        """Registra un nuevo producto en el catálogo.

        Args:
            dto: Datos del producto a crear. El ``id`` se ignora.

        Returns:
            DTO del producto persistido, con su ``id`` asignado.

        Raises:
            InvalidProductDataError: Si las reglas del dominio rechazan
                los datos recibidos.
        """
        try:
            entidad = Product(
                id=None,
                name=dto.name,
                brand=dto.brand,
                category=dto.category,
                size=dto.size,
                color=dto.color,
                price=dto.price,
                stock=dto.stock,
                description=dto.description,
            )
        except ValueError as exc:
            raise InvalidProductDataError(str(exc)) from exc

        guardado = self.repo.save(entidad)
        return self._to_dto(guardado)

    def update_product(
        self, product_id: int, dto: ProductDTO
    ) -> ProductDTO:
        """Actualiza un producto existente con datos nuevos.

        Args:
            product_id: ID del producto a modificar.
            dto: Datos nuevos. El ``id`` del DTO se ignora.

        Returns:
            DTO del producto actualizado.

        Raises:
            ProductNotFoundError: Si el producto no existe.
            InvalidProductDataError: Si los datos nuevos son inválidos.
        """
        existente = self.repo.get_by_id(product_id)
        if existente is None:
            raise ProductNotFoundError(product_id)

        try:
            actualizado = Product(
                id=product_id,
                name=dto.name,
                brand=dto.brand,
                category=dto.category,
                size=dto.size,
                color=dto.color,
                price=dto.price,
                stock=dto.stock,
                description=dto.description,
            )
        except ValueError as exc:
            raise InvalidProductDataError(str(exc)) from exc

        guardado = self.repo.save(actualizado)
        return self._to_dto(guardado)

    def delete_product(self, product_id: int) -> None:
        """Elimina un producto del catálogo.

        Args:
            product_id: ID del producto a eliminar.

        Raises:
            ProductNotFoundError: Si el producto no existe.
        """
        if not self.repo.delete(product_id):
            raise ProductNotFoundError(product_id)

    @staticmethod
    def _to_dto(product: Product) -> ProductDTO:
        """Traduce una entidad del dominio a su DTO de salida.

        Args:
            product: Entidad a convertir.

        Returns:
            DTO listo para serializar por FastAPI.
        """
        return ProductDTO(
            id=product.id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            size=product.size,
            color=product.color,
            price=product.price,
            stock=product.stock,
            description=product.description,
        )
