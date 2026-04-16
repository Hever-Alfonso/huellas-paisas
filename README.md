# Huellas Paisas

E-commerce de zapatos con asistente conversacional impulsado por Google Gemini. Proyecto del taller de **Construcción 2** de la Universidad EAFIT, implementado con **Clean Architecture** en tres capas.

La tienda está ambientada en Medellín, Colombia: el catálogo mezcla marcas internacionales (Nike, Adidas, Puma, ASICS, New Balance, Converse, Dr. Martens, Salomon) con dos marcas colombianas (Bosi y Vélez), y el asistente virtual ("Santi") habla con toque paisa sutil.

---

## Tabla de contenidos

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos previos](#requisitos-previos)
- [Instalación local](#instalación-local)
- [Ejecución con Docker](#ejecución-con-docker)
- [Uso de la API](#uso-de-la-api)
- [Endpoints](#endpoints)
- [Tests](#tests)
- [Obtener API key de Gemini](#obtener-api-key-de-gemini)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Decisiones de diseño](#decisiones-de-diseño)

---

## Características

- **API REST** completa con FastAPI y documentación automática en `/docs`.
- **Chat inteligente** con Google Gemini y memoria conversacional de los últimos 6 mensajes.
- **Clean Architecture** en tres capas: dominio, aplicación, infraestructura.
- **Repository Pattern** con interfaces en el dominio e implementaciones SQL en la infraestructura.
- **Dependency Injection** nativa de FastAPI usando `Annotated`.
- **Pydantic v2** con `field_validator` y `ConfigDict`.
- **SQLAlchemy 2.0** con `DeclarativeBase` y `Mapped`.
- **Modo degradado**: si no hay API key de Gemini, la app sigue funcionando con respuestas determinísticas útiles para desarrollo.
- **Middleware de timing** que añade `X-Process-Time-ms` a cada respuesta.
- **Endpoint `/stats`** como bonus con métricas básicas del sistema.
- **Tests unitarios** con pytest y cobertura sobre `src`.
- **Containerización** con Docker y Docker Compose con healthcheck.

---

## Arquitectura

```
┌────────────────────────────────────────────────────────┐
│  CAPA DE INFRAESTRUCTURA                               │
│  ┌───────────────────┐  ┌──────────────────────────┐  │
│  │ FastAPI (main.py) │  │ GeminiService (Santi)    │  │
│  └───────────────────┘  └──────────────────────────┘  │
│  ┌───────────────────┐  ┌──────────────────────────┐  │
│  │ SQLAlchemy models │  │ SQL*Repository           │  │
│  └───────────────────┘  └──────────────────────────┘  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  CAPA DE APLICACIÓN                                    │
│  ProductService · ChatService · DTOs (Pydantic)        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  CAPA DE DOMINIO                                       │
│  Product · ChatMessage · ChatContext                   │
│  IProductRepository · IChatRepository                  │
│  DomainError y sus subclases                           │
└────────────────────────────────────────────────────────┘
```

**Regla fundamental:** el dominio no importa nada de infraestructura ni de frameworks. La aplicación depende del dominio. La infraestructura depende de ambas.

---

## Requisitos previos

- **Python 3.10+**
- **Docker** y **Docker Compose** (para la ejecución containerizada)
- **API key de Google Gemini** (ver sección [Obtener API key de Gemini](#obtener-api-key-de-gemini))

---

## Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/Hever-Alfonso/huellas-paisas.git
cd huellas-paisas

# 2. Crear y activar entorno virtual (macOS / Linux)
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env y pega tu GEMINI_API_KEY real

# 5. Ejecutar la API
uvicorn src.infrastructure.api.main:app --reload
```

Visita:

- http://localhost:8000/docs — documentación interactiva Swagger UI
- http://localhost:8000/redoc — documentación alternativa
- http://localhost:8000/health — health check

---

## Ejecución con Docker

```bash
# Construir y levantar el contenedor
docker compose up --build

# En segundo plano
docker compose up -d

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

El contenedor expone el puerto `8000` y persiste la base de datos SQLite en `./data/huellas_paisas.db` gracias al volumen montado.

---

## Uso de la API

### Listar productos

```bash
curl http://localhost:8000/products
```

### Obtener un producto

```bash
curl http://localhost:8000/products/1
```

### Conversar con el asistente

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "cliente_001",
    "message": "Hola Santi, busco tenis Nike para correr en El Poblado"
  }'
```

Respuesta esperada:

```json
{
  "session_id": "cliente_001",
  "user_message": "Hola Santi, busco tenis Nike para correr en El Poblado",
  "assistant_message": "¡Con mucho gusto! Te recomiendo el Nike Air Zoom Pegasus 40 en talla 42 por USD 139.00. Tenemos 6 unidades disponibles y es ideal para trote urbano. ¿Te interesa?",
  "timestamp": "2026-04-12T10:30:00"
}
```

### Ver historial de una sesión

```bash
curl http://localhost:8000/chat/history/cliente_001
```

### Borrar historial

```bash
curl -X DELETE http://localhost:8000/chat/history/cliente_001
```

---

## Endpoints

| Método | Ruta                         | Descripción                             |
| ------ | ---------------------------- | --------------------------------------- |
| GET    | `/`                          | Información básica del servicio         |
| GET    | `/health`                    | Health check                            |
| GET    | `/stats`                     | Métricas del sistema (bonus)            |
| GET    | `/products`                  | Lista todos los productos               |
| GET    | `/products/available`        | Lista solo productos con stock          |
| GET    | `/products/{id}`             | Detalle de un producto                  |
| POST   | `/products`                  | Crea un nuevo producto                  |
| POST   | `/chat`                      | Envía un mensaje al asistente           |
| GET    | `/chat/history/{session_id}` | Historial de una sesión                 |
| DELETE | `/chat/history/{session_id}` | Borra el historial completo de sesión   |

---

## Tests

```bash
# Ejecutar todos los tests con coverage
pytest

# Reporte HTML de cobertura (se genera en htmlcov/)
pytest --cov-report=html

# Solo tests del dominio (rápidos)
pytest tests/test_entities.py -v
```

La configuración de pytest está en `pyproject.toml`. Los tests cubren:

- Entidades del dominio y sus reglas de negocio.
- `ProductService` con repositorio SQL real (SQLite en memoria).
- `ChatService` con un doble de prueba `FakeAIService` que no llama a Gemini.
- Aislamiento entre sesiones de chat.
- Manejo de errores del proveedor de IA.

---

## Obtener API key de Gemini

1. Ve a https://aistudio.google.com/app/apikey
2. Inicia sesión con una cuenta de Google.
3. Haz clic en **Create API key**.
4. Copia la clave y pégala en tu archivo `.env`:

```
GEMINI_API_KEY=AIzaSy...
```

> **Nota:** La aplicación funciona sin API key en modo degradado: responderá con mensajes determinísticos indicando que está sin credenciales. Esto es útil para desarrollo o para ejecutar los tests sin costo.

---

## Estructura del proyecto

```
huellas-paisas/
├── src/
│   ├── config.py
│   ├── domain/
│   │   ├── entities.py         # Product, ChatMessage, ChatContext
│   │   ├── repositories.py     # IProductRepository, IChatRepository
│   │   └── exceptions.py       # DomainError y subclases
│   ├── application/
│   │   ├── dtos.py             # Pydantic v2
│   │   ├── product_service.py
│   │   └── chat_service.py     # Protocol IAService
│   └── infrastructure/
│       ├── api/
│       │   └── main.py         # FastAPI con lifespan
│       ├── db/
│       │   ├── database.py     # SQLAlchemy 2.0
│       │   ├── models.py
│       │   └── init_data.py    # 10 productos semilla
│       ├── repositories/
│       │   ├── product_repository.py
│       │   └── chat_repository.py
│       └── llm_providers/
│           └── gemini_service.py
├── tests/
│   ├── conftest.py
│   ├── test_entities.py
│   ├── test_product_service.py
│   └── test_chat_service.py
├── evidencias/                  # Screenshots para la entrega
├── data/                        # SQLite (creada en runtime)
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Decisiones de diseño

- **Pydantic v2 moderno**: se usa `field_validator` en lugar del obsoleto `@validator`, y `ConfigDict` en lugar de `class Config`.
- **SQLAlchemy 2.0**: se usa `DeclarativeBase` con `Mapped[...]` para tipado estático.
- **FastAPI con `lifespan`**: se evita el deprecated `@app.on_event("startup")`.
- **`Annotated[Service, Depends(...)]`**: para declaraciones de dependencias más limpias.
- **`Protocol` para el servicio de IA**: permite inyectar cualquier proveedor sin herencia explícita. Es trivial cambiar Gemini por Claude, OpenAI o un mock.
- **Manejadores de excepciones del dominio**: `ProductNotFoundError` → HTTP 404, `InvalidProductDataError` → 422, `ChatServiceError` → 503. La capa de aplicación nunca lanza `HTTPException`.
- **Modo degradado del LLM**: la app arranca y sirve endpoints aunque `GEMINI_API_KEY` no esté configurada. Esto facilita enormemente el desarrollo y los tests.
- **Middleware de timing**: cada respuesta incluye `X-Process-Time-ms` para observabilidad básica sin instrumentación pesada.

---

## Autor

**Hever Andre Alfonso Jimenez** — haalfonsoj@eafit.edu.co  
Universidad EAFIT, Taller de Construcción 2.

---

## Licencia

Uso académico. Adapta y reutiliza libremente en tus propios trabajos, pero conserva la atribución.
