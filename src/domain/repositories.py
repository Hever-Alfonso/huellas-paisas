"""Interfaces (puertos) de los repositorios del dominio.

Este módulo declara los contratos que cualquier implementación de
persistencia debe cumplir para ser utilizable por la capa de
aplicación. Las implementaciones concretas viven en
``src/infrastructure/repositories`` y pueden usar SQLAlchemy,
MongoDB, un cliente REST externo o incluso listas en memoria.

Siguiendo el principio de inversión de dependencias, la capa de
aplicación depende de estas interfaces y no de las implementaciones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .entities import ChatMessage, Product


class IProductRepository(ABC):
    """Puerto de salida para la persistencia de productos.

    Cualquier clase que herede de ``IProductRepository`` debe
    implementar todos los métodos declarados como abstractos. La
    capa de aplicación recibe una instancia concreta por inyección
    de dependencias y la utiliza sin conocer los detalles técnicos.
    """

    @abstractmethod
    def get_all(self) -> list[Product]:
        """Obtiene todos los productos disponibles en el catálogo.

        Returns:
            Lista de entidades ``Product`` (puede estar vacía).
        """

    @abstractmethod
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Busca un producto por su identificador único.

        Args:
            product_id: ID numérico del producto.

        Returns:
            La entidad correspondiente o ``None`` si no existe.
        """

    @abstractmethod
    def get_by_brand(self, brand: str) -> list[Product]:
        """Filtra productos por marca (comparación sin distinguir mayúsculas).

        Args:
            brand: Nombre de la marca a buscar.

        Returns:
            Lista de productos cuya marca coincide. Lista vacía si
            no hay coincidencias.
        """

    @abstractmethod
    def get_by_category(self, category: str) -> list[Product]:
        """Filtra productos por categoría de uso.

        Args:
            category: Nombre de la categoría (``"Running"``, ``"Casual"``...).

        Returns:
            Lista de productos en esa categoría.
        """

    @abstractmethod
    def save(self, product: Product) -> Product:
        """Crea o actualiza un producto.

        Si la entidad tiene ``id=None`` se inserta un nuevo registro y
        se devuelve la entidad con el ID asignado. Si ya tiene ID se
        actualiza el registro existente.

        Args:
            product: Entidad a persistir.

        Returns:
            Entidad persistida, con su ID garantizado.
        """

    @abstractmethod
    def delete(self, product_id: int) -> bool:
        """Elimina un producto del catálogo.

        Args:
            product_id: ID del producto a eliminar.

        Returns:
            ``True`` si se eliminó, ``False`` si no existía.
        """


class IChatRepository(ABC):
    """Puerto de salida para la persistencia de los mensajes del chat.

    Encapsula todas las operaciones necesarias para guardar y
    recuperar el historial conversacional. Se usa tanto para
    mostrar conversaciones previas al usuario como para alimentar
    el contexto que se envía al LLM en cada turno.
    """

    @abstractmethod
    def save_message(self, message: ChatMessage) -> ChatMessage:
        """Persiste un mensaje individual en la sesión.

        Args:
            message: Entidad del mensaje a guardar.

        Returns:
            El mensaje con su ID asignado por la base de datos.
        """

    @abstractmethod
    def get_session_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> list[ChatMessage]:
        """Obtiene el historial completo de una sesión.

        Args:
            session_id: Identificador de la sesión.
            limit: Si se pasa, devuelve solo los últimos ``limit``
                mensajes. Si es ``None``, devuelve todos.

        Returns:
            Lista de mensajes en orden cronológico ascendente.
        """

    @abstractmethod
    def delete_session_history(self, session_id: str) -> int:
        """Elimina todos los mensajes de una sesión.

        Args:
            session_id: Identificador de la sesión a limpiar.

        Returns:
            Cantidad de mensajes que fueron eliminados.
        """

    @abstractmethod
    def get_recent_messages(
        self, session_id: str, count: int
    ) -> list[ChatMessage]:
        """Obtiene los últimos ``count`` mensajes de la sesión.

        Este método es esencial para construir el ``ChatContext``
        que se envía al LLM. Los mensajes deben devolverse en orden
        cronológico ascendente aunque internamente se consulten al
        revés por eficiencia.

        Args:
            session_id: Identificador de la sesión.
            count: Número máximo de mensajes a recuperar.

        Returns:
            Lista de mensajes recientes, del más antiguo al más nuevo.
        """
