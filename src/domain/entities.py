"""Entidades del dominio de Huellas Paisas.

Estas clases representan los conceptos centrales del negocio: el
producto que se vende y los mensajes que intercambian el usuario y
el asistente de IA. Son objetos puros de Python, sin dependencias de
frameworks, bases de datos ni servicios externos.

La regla fundamental de esta capa es: **nada de lo que está aquí
debe conocer cómo se persiste, cómo se expone por HTTP o qué LLM
se usa**. Eso permite que el dominio sea reutilizable y testeable
en aislamiento.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Roles permitidos para un mensaje en el chat.
_ROLE_USER = "user"
_ROLE_ASSISTANT = "assistant"
_VALID_ROLES = frozenset({_ROLE_USER, _ROLE_ASSISTANT})


@dataclass
class Product:
    """Representa un par de zapatos dentro del catálogo de la tienda.

    Una entidad ``Product`` agrupa los datos descriptivos del artículo
    junto con las reglas de negocio que le aplican: el precio debe ser
    positivo, el inventario no puede quedar negativo y no puede
    venderse un producto sin existencias.

    Attributes:
        id: Identificador único. Es ``None`` mientras el producto no
            ha sido persistido.
        name: Nombre comercial del modelo (por ejemplo, ``"Air Zoom Pegasus 40"``).
        brand: Marca del fabricante.
        category: Categoría de uso (``"Running"``, ``"Casual"``, ``"Formal"``...).
        size: Talla, almacenada como texto para admitir notaciones mixtas.
        color: Color principal del producto.
        price: Precio de venta en dólares estadounidenses.
        stock: Número de unidades disponibles en inventario.
        description: Descripción corta para el cliente.

    Raises:
        ValueError: Si los datos proporcionados violan alguna regla de negocio.

    Example:
        >>> zapato = Product(
        ...     id=None,
        ...     name="Bosi Oxford Clásico",
        ...     brand="Bosi",
        ...     category="Formal",
        ...     size="42",
        ...     color="Café",
        ...     price=189.0,
        ...     stock=4,
        ...     description="Cuero colombiano, suela de goma antideslizante.",
        ... )
        >>> zapato.is_available()
        True
    """

    id: Optional[int]
    name: str
    brand: str
    category: str
    size: str
    color: str
    price: float
    stock: int
    description: str

    def __post_init__(self) -> None:
        """Valida los invariantes del producto inmediatamente después de construirlo.

        Raises:
            ValueError: Si el precio no es positivo, si el stock es
                negativo o si ``name`` o ``brand`` están vacíos.
        """
        if not self.name or not self.name.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        if not self.brand or not self.brand.strip():
            raise ValueError("La marca del producto no puede estar vacía.")
        if self.price <= 0:
            raise ValueError(
                f"El precio debe ser mayor a 0. Recibido: {self.price}."
            )
        if self.stock < 0:
            raise ValueError(
                f"El stock no puede ser negativo. Recibido: {self.stock}."
            )

    def is_available(self) -> bool:
        """Indica si el producto puede ser vendido en este momento.

        Returns:
            ``True`` si hay al menos una unidad en inventario,
            ``False`` en caso contrario.
        """
        return self.stock > 0

    def reduce_stock(self, quantity: int) -> None:
        """Descuenta unidades del inventario al realizar una venta.

        Args:
            quantity: Cantidad a descontar. Debe ser un entero positivo.

        Raises:
            ValueError: Si ``quantity`` no es positivo o si no hay
                suficiente inventario para cubrir la operación.
        """
        if quantity <= 0:
            raise ValueError("La cantidad a descontar debe ser positiva.")
        if quantity > self.stock:
            raise ValueError(
                f"Stock insuficiente: hay {self.stock} unidades y se "
                f"pidieron {quantity}."
            )
        self.stock -= quantity

    def increase_stock(self, quantity: int) -> None:
        """Añade unidades al inventario, por ejemplo al reabastecer.

        Args:
            quantity: Cantidad a sumar. Debe ser un entero positivo.

        Raises:
            ValueError: Si ``quantity`` no es positivo.
        """
        if quantity <= 0:
            raise ValueError("La cantidad a aumentar debe ser positiva.")
        self.stock += quantity


@dataclass
class ChatMessage:
    """Mensaje individual dentro de una conversación con el asistente.

    Cada mensaje pertenece a una sesión identificada por ``session_id``
    y tiene un ``role`` que distingue quién lo emitió: el usuario o
    el asistente. Ese rol es clave para que el LLM reconstruya el
    diálogo correctamente.

    Attributes:
        id: Identificador único del mensaje. ``None`` si aún no se persiste.
        session_id: Identificador de la sesión o usuario.
        role: Rol del emisor. Debe ser ``"user"`` o ``"assistant"``.
        message: Texto del mensaje.
        timestamp: Fecha y hora de creación.

    Raises:
        ValueError: Si alguno de los campos obligatorios está vacío
            o si el rol no es válido.
    """

    id: Optional[int]
    session_id: str
    role: str
    message: str
    timestamp: datetime

    def __post_init__(self) -> None:
        """Valida los invariantes del mensaje.

        Raises:
            ValueError: Si ``session_id`` o ``message`` están vacíos,
                o si ``role`` no pertenece al conjunto permitido.
        """
        if not self.session_id or not self.session_id.strip():
            raise ValueError("El session_id no puede estar vacío.")
        if not self.message or not self.message.strip():
            raise ValueError("El mensaje no puede estar vacío.")
        if self.role not in _VALID_ROLES:
            raise ValueError(
                f"Rol inválido: '{self.role}'. Debe ser uno de {sorted(_VALID_ROLES)}."
            )

    def is_from_user(self) -> bool:
        """Indica si el mensaje fue enviado por el usuario humano.

        Returns:
            ``True`` si ``role == 'user'``, ``False`` en caso contrario.
        """
        return self.role == _ROLE_USER

    def is_from_assistant(self) -> bool:
        """Indica si el mensaje fue generado por el asistente de IA.

        Returns:
            ``True`` si ``role == 'assistant'``, ``False`` en caso contrario.
        """
        return self.role == _ROLE_ASSISTANT


@dataclass
class ChatContext:
    """Ventana conversacional que se envía al LLM en cada turno.

    ``ChatContext`` es un *Value Object*: no tiene identidad propia,
    simplemente encapsula los últimos ``max_messages`` mensajes para
    que el asistente pueda mantener coherencia con lo ya dicho.

    Attributes:
        messages: Historial disponible en orden cronológico.
        max_messages: Cantidad máxima de mensajes a incluir en el prompt.
    """

    messages: list[ChatMessage] = field(default_factory=list)
    max_messages: int = 6

    def get_recent_messages(self) -> list[ChatMessage]:
        """Devuelve los mensajes más recientes limitados por ``max_messages``.

        Returns:
            Una nueva lista con como máximo ``max_messages`` elementos,
            manteniendo el orden cronológico (del más antiguo al más nuevo).
        """
        if self.max_messages <= 0:
            return []
        return list(self.messages[-self.max_messages:])

    def format_for_prompt(self) -> str:
        """Serializa el contexto a un bloque de texto apto para el prompt.

        El formato usa etiquetas en español (``Usuario`` / ``Asistente``)
        para que el modelo entienda sin ambigüedad quién habló y en
        qué orden.

        Returns:
            Una cadena con un mensaje por línea. Cadena vacía si no
            hay historial.

        Example:
            >>> from datetime import datetime
            >>> ctx = ChatContext(messages=[
            ...     ChatMessage(None, "s1", "user", "Hola", datetime.now()),
            ...     ChatMessage(None, "s1", "assistant", "¡Qué más pues!", datetime.now()),
            ... ])
            >>> print(ctx.format_for_prompt())
            Usuario: Hola
            Asistente: ¡Qué más pues!
        """
        recientes = self.get_recent_messages()
        if not recientes:
            return ""
        lineas: list[str] = []
        for msg in recientes:
            etiqueta = "Usuario" if msg.is_from_user() else "Asistente"
            lineas.append(f"{etiqueta}: {msg.message}")
        return "\n".join(lineas)

    def is_empty(self) -> bool:
        """Indica si el contexto no contiene mensajes todavía.

        Returns:
            ``True`` cuando el historial está vacío, ``False`` si hay al menos uno.
        """
        return len(self.messages) == 0
