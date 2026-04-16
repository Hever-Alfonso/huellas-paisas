"""Implementación SQL del repositorio de productos.

``SQLProductRepository`` traduce entre la entidad ``Product`` del
dominio y el modelo ORM ``ProductModel``. Su responsabilidad es
exclusivamente de persistencia: no valida datos de negocio ni
toma decisiones del catálogo.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.entities import Product
from src.domain.repositories import IProductRepository
from src.infrastructure.db.models import ProductModel


class SQLProductRepository(IProductRepository):
    """Repositorio de productos respaldado por SQLAlchemy.

    Attributes:
        db: Sesión activa de SQLAlchemy. Se asume que su ciclo de
            vida (apertura/cierre) lo gestiona quien instancia el
            repositorio, normalmente FastAPI vía ``get_db``.
    """

    def __init__(self, db: Session) -> None:
        """Inicializa el repositorio con una sesión de base de datos.

        Args:
            db: Sesión abierta de SQLAlchemy.
        """
        self.db = db

    def get_all(self) -> list[Product]:
        """Lista todos los productos del catálogo.

        Returns:
            Lista de entidades ``Product``. Lista vacía si no hay datos.
        """
        modelos = self.db.execute(select(ProductModel)).scalars().all()
        return [self._model_to_entity(m) for m in modelos]

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Busca un producto por su ID.

        Args:
            product_id: Identificador numérico del producto.

        Returns:
            Entidad ``Product`` correspondiente o ``None`` si no existe.
        """
        modelo = self.db.get(ProductModel, product_id)
        return self._model_to_entity(modelo) if modelo else None

    def get_by_brand(self, brand: str) -> list[Product]:
        """Filtra productos por marca de forma insensible a mayúsculas.

        Args:
            brand: Nombre de la marca.

        Returns:
            Lista de productos cuya marca coincide.
        """
        stmt = select(ProductModel).where(
            func.lower(ProductModel.brand) == brand.lower()
        )
        modelos = self.db.execute(stmt).scalars().all()
        return [self._model_to_entity(m) for m in modelos]

    def get_by_category(self, category: str) -> list[Product]:
        """Filtra productos por categoría de uso.

        Args:
            category: Categoría (``"Running"``, ``"Casual"``, etc.).

        Returns:
            Lista de productos en esa categoría.
        """
        stmt = select(ProductModel).where(
            func.lower(ProductModel.category) == category.lower()
        )
        modelos = self.db.execute(stmt).scalars().all()
        return [self._model_to_entity(m) for m in modelos]

    def save(self, product: Product) -> Product:
        """Inserta o actualiza un producto según tenga o no ID.

        Args:
            product: Entidad a persistir.

        Returns:
            La misma entidad con el ID asegurado.
        """
        if product.id is None:
            modelo = self._entity_to_model(product)
            self.db.add(modelo)
            self.db.commit()
            self.db.refresh(modelo)
            return self._model_to_entity(modelo)

        modelo_existente = self.db.get(ProductModel, product.id)
        if modelo_existente is None:
            # El repositorio no valida existencia: simplemente inserta.
            # La capa de aplicación es responsable de lanzar
            # ``ProductNotFoundError`` cuando corresponde.
            modelo_existente = self._entity_to_model(product)
            self.db.add(modelo_existente)
        else:
            self._apply_entity_to_model(product, modelo_existente)

        self.db.commit()
        self.db.refresh(modelo_existente)
        return self._model_to_entity(modelo_existente)

    def delete(self, product_id: int) -> bool:
        """Elimina un producto por ID.

        Args:
            product_id: ID del producto a eliminar.

        Returns:
            ``True`` si había algo que eliminar, ``False`` en caso contrario.
        """
        modelo = self.db.get(ProductModel, product_id)
        if modelo is None:
            return False
        self.db.delete(modelo)
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_entity(modelo: ProductModel) -> Product:
        """Traduce un ``ProductModel`` a la entidad ``Product``.

        Args:
            modelo: Instancia ORM proveniente de la base de datos.

        Returns:
            Entidad del dominio equivalente.
        """
        return Product(
            id=modelo.id,
            name=modelo.name,
            brand=modelo.brand,
            category=modelo.category,
            size=modelo.size,
            color=modelo.color,
            price=modelo.price,
            stock=modelo.stock,
            description=modelo.description or "",
        )

    @staticmethod
    def _entity_to_model(entidad: Product) -> ProductModel:
        """Crea un nuevo modelo ORM a partir de una entidad del dominio.

        Args:
            entidad: Entidad ``Product`` a convertir.

        Returns:
            Instancia de ``ProductModel`` lista para insertar.
        """
        return ProductModel(
            id=entidad.id,
            name=entidad.name,
            brand=entidad.brand,
            category=entidad.category,
            size=entidad.size,
            color=entidad.color,
            price=entidad.price,
            stock=entidad.stock,
            description=entidad.description,
        )

    @staticmethod
    def _apply_entity_to_model(
        entidad: Product, modelo: ProductModel
    ) -> None:
        """Copia los campos de la entidad al modelo existente.

        Usado en actualizaciones para evitar crear objetos nuevos.

        Args:
            entidad: Entidad con los datos nuevos.
            modelo: Modelo ORM ya cargado desde la base de datos.
        """
        modelo.name = entidad.name
        modelo.brand = entidad.brand
        modelo.category = entidad.category
        modelo.size = entidad.size
        modelo.color = entidad.color
        modelo.price = entidad.price
        modelo.stock = entidad.stock
        modelo.description = entidad.description
