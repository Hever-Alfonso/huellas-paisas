"""Catálogo inicial de Huellas Paisas.

Este módulo contiene la semilla de productos con la que arranca la
tienda. La función ``load_initial_data`` es idempotente: si ya hay
productos en la base de datos, no hace nada.

El catálogo mezcla marcas internacionales (Nike, Adidas, Puma,
Converse, New Balance, ASICS, Dr. Martens, Salomon) con dos
marcas colombianas (Bosi y Vélez) para darle sabor local.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .models import ProductModel

logger = logging.getLogger(__name__)


# Catálogo semilla pensado para conversaciones realistas con el LLM.
# Diez productos variados en marca, categoría, talla y rango de precio.
_CATALOGO_INICIAL: list[dict] = [
    {
        "name": "Air Zoom Pegasus 40",
        "brand": "Nike",
        "category": "Running",
        "size": "42",
        "color": "Negro",
        "price": 139.00,
        "stock": 6,
        "description": "Tenis de running versátil con amortiguación React y malla transpirable, ideal para trote urbano en El Poblado.",
    },
    {
        "name": "Ultraboost Light",
        "brand": "Adidas",
        "category": "Running",
        "size": "41",
        "color": "Blanco",
        "price": 189.00,
        "stock": 3,
        "description": "Boost Light más liviano que la versión anterior, con upper Primeknit. Excelente para maratones y trote de fondo.",
    },
    {
        "name": "Suede Classic XXI",
        "brand": "Puma",
        "category": "Casual",
        "size": "40",
        "color": "Azul",
        "price": 79.00,
        "stock": 12,
        "description": "Ícono urbano en gamuza clásica con suela de goma. Combina con jeans y pantaloneta por igual.",
    },
    {
        "name": "574 Core",
        "brand": "New Balance",
        "category": "Casual",
        "size": "43",
        "color": "Gris",
        "price": 109.00,
        "stock": 7,
        "description": "Clásico moderno con mezcla de gamuza y malla, suela ENCAP para todo el día de pie.",
    },
    {
        "name": "Chuck 70 High",
        "brand": "Converse",
        "category": "Casual",
        "size": "39",
        "color": "Negro",
        "price": 95.00,
        "stock": 0,
        "description": "Caña alta en canvas premium con costuras reforzadas. Agotado temporalmente, reposición en camino.",
    },
    {
        "name": "Gel-Kayano 30",
        "brand": "ASICS",
        "category": "Running",
        "size": "42",
        "color": "Azul oscuro",
        "price": 169.00,
        "stock": 4,
        "description": "Soporte para pisada pronadora con tecnología Gel. Muy recomendado para corredores de gran recorrido.",
    },
    {
        "name": "1460 Original",
        "brand": "Dr. Martens",
        "category": "Formal",
        "size": "41",
        "color": "Cereza",
        "price": 199.00,
        "stock": 2,
        "description": "Bota clásica de ocho ojales en cuero Smooth, suela AirWair. Elegante y resistente al aguacero paisa.",
    },
    {
        "name": "Speedcross 6",
        "brand": "Salomon",
        "category": "Trail",
        "size": "43",
        "color": "Verde militar",
        "price": 159.00,
        "stock": 5,
        "description": "Diseñado para trail running en terreno húmedo. Perfecto para rutas en Santa Elena y el Alto de San Félix.",
    },
    {
        "name": "Oxford Clásico",
        "brand": "Bosi",
        "category": "Formal",
        "size": "42",
        "color": "Café",
        "price": 149.00,
        "stock": 8,
        "description": "Zapato formal en cuero colombiano con construcción Blake. Ideal para oficina o reuniones en Ciudad del Río.",
    },
    {
        "name": "Mocasín Milano",
        "brand": "Vélez",
        "category": "Casual",
        "size": "40",
        "color": "Miel",
        "price": 129.00,
        "stock": 10,
        "description": "Mocasín casual hecho en Medellín, cuero flor entera y plantilla acolchada. Un clásico paisa.",
    },
]


def load_initial_data(session: Session) -> int:
    """Carga el catálogo semilla si la tabla de productos está vacía.

    Args:
        session: Sesión de SQLAlchemy abierta en la que se insertan los datos.

    Returns:
        Cantidad de productos insertados. Cero si la tabla ya tenía datos.
    """
    existentes = session.query(ProductModel).count()
    if existentes > 0:
        logger.info(
            "La tabla products ya tiene %s registros, no se recarga.",
            existentes,
        )
        return 0

    nuevos = [ProductModel(**datos) for datos in _CATALOGO_INICIAL]
    session.add_all(nuevos)
    session.commit()
    logger.info("Se insertaron %s productos iniciales.", len(nuevos))
    return len(nuevos)
