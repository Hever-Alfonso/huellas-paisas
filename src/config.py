"""Configuración global de Huellas Paisas.

Carga las variables de entorno desde el archivo ``.env`` y las expone
mediante una clase ``Settings`` que se instancia una sola vez al
importar este módulo.

Centralizar la configuración aquí evita que otras capas necesiten
leer ``os.environ`` directamente, lo que facilita los tests y permite
cambiar el origen de configuración (por ejemplo, Vault o AWS Secrets
Manager) sin tocar la lógica de negocio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Carga las variables de entorno desde .env si existe. En producción
# las variables vendrán del orquestador (Docker, Kubernetes, etc.).
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable de la aplicación.

    Se declara como ``frozen=True`` para que sea imposible modificarla
    en tiempo de ejecución por accidente. Si se necesita cambiar algún
    valor en tests, se crea una instancia nueva.

    Attributes:
        app_name: Nombre visible de la API, usado en Swagger y logs.
        app_version: Versión semántica del proyecto.
        environment: Entorno de ejecución (``development``, ``production``).
        gemini_api_key: Clave de acceso a la API de Google Gemini.
        gemini_model: Identificador del modelo de Gemini a utilizar.
        database_url: URL de conexión de SQLAlchemy.
        data_dir: Carpeta donde se persiste la base de datos SQLite.
        chat_context_window: Cantidad de mensajes recientes que se
            incluyen como contexto en cada invocación al LLM.
        cors_origins: Lista de orígenes permitidos por el middleware CORS.
    """

    app_name: str = "Huellas Paisas API"
    app_version: str = "1.0.0"
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///./data/huellas_paisas.db"
        )
    )
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    chat_context_window: int = 6
    cors_origins: tuple[str, ...] = ("*",)

    def is_production(self) -> bool:
        """Indica si la aplicación se está ejecutando en producción.

        Returns:
            ``True`` si la variable de entorno ``ENVIRONMENT`` vale
            ``"production"``, ``False`` en cualquier otro caso.
        """
        return self.environment.lower() == "production"

    def ensure_data_dir(self) -> None:
        """Crea la carpeta de datos si no existe.

        Útil al arrancar la aplicación para evitar errores la primera
        vez que se intenta crear la base de datos SQLite.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Instancia global reutilizable en toda la aplicación.
settings = Settings()
