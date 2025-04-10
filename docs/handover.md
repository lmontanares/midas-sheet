# Documento de Transferencia: Sistema de Gestión Financiera v3.0

## 1. Visión general del proyecto

### Propósito fundamental y objetivos principales
El Sistema de Gestión Financiera es una aplicación diseñada para facilitar el seguimiento y control de finanzas personales a través de un bot de Telegram integrado con Google Sheets. El objetivo principal es proporcionar una herramienta accesible que permita a los usuarios registrar y consultar sus ingresos y gastos de manera sencilla desde cualquier dispositivo con Telegram.

### Descripción de la funcionalidad central
El sistema consta de dos componentes principales que trabajan de forma integrada:
1. Un bot de Telegram que sirve como interfaz de usuario para registrar transacciones financieras y consultar información.
2. Un módulo de integración con Google Sheets que almacena y gestiona los datos financieros en la nube.

El usuario interactúa con el bot siguiendo un flujo específico para registrar transacciones:
1. El usuario se autentica con su cuenta de Google usando OAuth 2.0 (`/auth`)
2. Selecciona una de sus hojas de cálculo (`/list` y `/sheet`)
3. Inicia el registro de transacción con el comando `/agregar`
4. Elige tipo de transacción (ingreso o egreso)
5. Selecciona una categoría
6. Si seleccionó un egreso, selecciona una subcategoría (los ingresos no tienen subcategorías)
7. Ingresa el monto de la transacción
8. Decide si desea agregar un comentario opcional (con botones Sí/No)
9. Si eligió añadir comentario, lo escribe; si no, se registra sin comentario
10. El sistema registra la transacción en la hoja de cálculo correspondiente

### Problemas que resuelve y valor que aporta
- Simplifica el registro de gastos e ingresos sin necesidad de aplicaciones complejas
- Permite acceder y gestionar información financiera desde cualquier dispositivo con Telegram
- Centraliza los datos financieros en Google Sheets, facilitando análisis posteriores
- Elimina la necesidad de herramientas costosas o complejas de finanzas personales
- Proporciona una estructura jerárquica para categorizar gastos, facilitando análisis detallados
- Permite contextualizar transacciones mediante el campo de comentarios opcional
- Interfaz guiada mediante botones que simplifica la experiencia de usuario
- Permite a cada usuario trabajar con sus propias hojas de cálculo gracias a OAuth 2.0
- Protege la privacidad de los datos al no requerir compartir hojas con el bot

## 2. Ecosistema tecnológico

### Lenguajes de programación utilizados
- Python 3.9+ (aprovechando características modernas de tipado)

### Sistema de tipado (Type Hints)
El proyecto hace uso extensivo del sistema de tipado estático de Python 3.9+, aprovechando las características modernas:

- **Uso directo de tipos contenedores integrados** sin importaciones desde typing:
  ```python
  # Correcto - usando tipado moderno (Python 3.9+)
  users: list[str] = []
  config: dict[str, str] = {}
  ```

- **Operador de unión `|` para tipos múltiples**:
  ```python
  # Correcto - usando operador | (Python 3.9+)
  def process_amount(amount: str | float | int) -> float:
      # Implementación
  ```

- **Importación específica de `Any` cuando sea necesario**:
  ```python
  from typing import Any

  def get_metadata() -> dict[str, Any]:
      # Implementación
  ```

Todos los métodos y funciones públicas incluyen anotaciones de tipo completas, mejorando la documentación, facilitando el desarrollo y permitiendo la verificación estática de tipos.

### Frameworks, bibliotecas y dependencias principales
- **Bot de Telegram:**
  - python-telegram-bot (v20.6+): Framework para la creación del bot
- **Google Sheets:**
  - gspread: Biblioteca para interactuar con Google Sheets
  - google-auth: Autenticación base con servicios de Google
  - google-auth-oauthlib: Autenticación OAuth 2.0 con Google
  - google-auth-httplib2: Gestión de solicitudes HTTP autenticadas
- **Servidor OAuth:**
  - Flask: Servidor web ligero para manejar redirecciones OAuth
- **Configuración y Datos:**
  - pyyaml: Para manejo de archivos de configuración YAML
- **Utilidades:**
  - loguru: Sistema avanzado de logging
  - python-dotenv: Gestión de variables de entorno
  - pydantic: Validación de datos
  - pathlib: Manejo de rutas de archivos de forma moderna
- **Testing:**
  - pytest: Framework principal de pruebas
  - pytest-asyncio: Soporte para pruebas asíncronas
  - pytest-cov: Medición de cobertura de código
  - pytest-mock: Creación de mocks con integración nativa en pytest

### Herramientas de desarrollo y entorno de trabajo
- Gestor de paquetes: uv (alternativa moderna a pip)
- Control de versiones: Git
- Entorno virtual: Recomendado para aislamiento de dependencias
- Pruebas: pytest con los plugins mencionados anteriormente

## 3. Arquitectura y estructura

### Diagrama conceptual de la arquitectura
La arquitectura sigue un patrón modular con separación clara de responsabilidades y autenticación OAuth:

```
                  ┌─────────────┐
                  │Google OAuth │
                  │   Server    │
                  └──────┬──────┘
                         │
                         │ (Autenticación)
                         ▼
Usuario (Telegram) → Bot de Telegram → Módulo OAuth → Módulo Google Sheets → Hojas del usuario
        ↑                   ↓               ↓                  ↓
        └───────────────────┴───────────────┴──────────────────┘
                   (Respuestas y visualizaciones)
```

El flujo de información comienza cuando el usuario envía comandos al bot a través de Telegram. El usuario primero se autentica mediante OAuth 2.0, lo que permite al bot acceder a sus propias hojas de cálculo de Google. El bot procesa estos comandos y, según sea necesario, interactúa con el módulo de Google Sheets para leer o escribir datos en las hojas del usuario. Finalmente, el bot envía respuestas al usuario basadas en el resultado de estas operaciones.

### Estructura de componentes/módulos
```
/finanzas/
│
├── src/                  # Código fuente
│   ├── auth/             # Autenticación OAuth 2.0
│   │   ├── __init__.py   # Inicialización del módulo
│   │   └── oauth.py      # Gestor de autenticación OAuth
│   │
│   ├── bot/              # Lógica del bot de Telegram
│   │   ├── __init__.py   # Inicialización del módulo
│   │   ├── bot.py        # Configuración principal del bot
│   │   ├── handlers.py   # Manejadores de mensajes y comandos
│   │   ├── commands.py   # Definiciones de comandos
│   │   └── handlers/     # Manejadores específicos
│   │       ├── __init__.py # Inicialización del módulo
│   │       └── auth_handlers.py # Manejadores de autenticación
│   │
│   ├── config/           # Configuraciones externas
│   │   ├── __init__.py   # Inicialización del módulo
│   │   ├── categories.py # Gestor de categorías
│   │   └── categories.yaml # Archivo de configuración de categorías
│   │
│   ├── server/           # Servidor para OAuth
│   │   ├── __init__.py   # Inicialización del módulo
│   │   └── oauth_server.py # Servidor para redirecciones OAuth
│   │
│   ├── sheets/           # Integración con Google Sheets
│   │   ├── __init__.py   # Inicialización del módulo
│   │   ├── client.py     # Cliente para conectar con Google Sheets
│   │   └── operations.py # Operaciones con las hojas de cálculo
│   │
│   └── utils/            # Utilidades comunes
│       ├── __init__.py   # Inicialización del módulo
│       ├── config.py     # Configuración y variables de entorno
│       └── logger.py     # Configuración de logging
│
├── tests/                # Pruebas automatizadas
│   ├── test_bot.py       # Pruebas para el bot de Telegram
│   ├── test_commands.py  # Pruebas para los comandos del bot
│   ├── test_handlers.py  # Pruebas para los manejadores del bot
│   ├── test_sheets.py    # Pruebas para la integración con Google Sheets
│   ├── test_auth.py      # Pruebas para la autenticación OAuth
│   ├── conftest.py       # Fixtures compartidos para pruebas
│   └── README.md         # Documentación de pruebas
│
├── tokens/               # Directorio para tokens OAuth
├── docs/                 # Documentación del proyecto
│   └── handover.md       # Documento de transferencia
│
├── main.py               # Punto de entrada de la aplicación
├── pyproject.toml        # Configuración del proyecto Python
├── pytest.ini            # Configuración de pytest
├── .env                  # Variables de entorno (local)
├── .env.example          # Ejemplo de variables de entorno
├── oauth_credentials.json # Credenciales OAuth de Google API
└── README.md             # Documentación principal
```

### Patrones de diseño implementados
- **Patrón Cliente**: Encapsulación del acceso a Google Sheets en una clase cliente (`GoogleSheetsClient`)
- **Patrón Factory**: Creación de manejadores para el bot de Telegram (en `commands.py`)
- **Patrón Gestor de Configuración**: Implementado con la clase `CategoryManager` que centraliza el acceso a las configuraciones de categorías
- **Patrón Estado**: Implementado para el flujo de conversación usando el diccionario `user_data` con estados definidos para manejar la transición entre pasos del flujo
- **Patrón Proxy/Delegación**: Implementado en `OAuthManager` para manejar la autenticación con Google
- **Propiedades (@property)**: Para el acceso controlado a la configuración (en `config.py` y `categories.py`)
- **Inyección de dependencias**: Las clases reciben sus dependencias en el constructor (por ejemplo, `TelegramBot` recibe `SheetsOperations` y `OAuthManager`)
- **Callback asíncronos**: Uso de `post_init` para registro de comandos del bot de forma asíncrona
- **Servidor multi-hilos**: Implementación del servidor OAuth en un hilo separado para no bloquear el bot
- **Patrón Observer**: Implementado para la comunicación entre el servidor OAuth y el bot mediante callbacks
- **Nombres en inglés con documentación en español**: Convención adoptada donde los nombres de clases, funciones y variables están en inglés, pero los comentarios y documentación están en español

## 4. Estado actual del desarrollo

### Características implementadas y funcionalidades completas
- Estructura básica completa del proyecto con organización modular
- Configuración inicial para el bot de Telegram implementada
- **Sistema de autenticación OAuth 2.0 completo:**
  - Flujo de autorización con redirección a Google
  - Gestión de tokens por usuario
  - Refresco automático de tokens expirados
  - Revocación de acceso
- **Nuevos comandos implementados:**
  - `/auth`: Inicia el proceso de autenticación OAuth
  - `/list`: Lista las hojas de cálculo disponibles del usuario
  - `/sheet`: Selecciona una hoja de cálculo específica
  - `/logout`: Cierra sesión y revoca acceso
- Manejadores para comandos `/start`, `/help`, `/agregar` y `/recargar`
- Servidor web para manejar redirecciones OAuth implementado
- Implementación completa del comando `/agregar` con flujo interactivo mediante botones:
  - Selección clara del tipo de transacción (ingreso/egreso) como primer paso
  - Selección de categorías mediante botones
  - Selección de subcategorías para gastos
  - Entrada de montos
  - Opción para añadir comentarios opcional mediante botones (Sí/No)
  - Registro en hojas de cálculo con todos los campos
- Sistema de categorías configurables desde archivo YAML externo
- Autenticación multi-usuario con OAuth 2.0:
  - Cada usuario accede a sus propias hojas de cálculo
  - Los datos se almacenan en hojas específicas del usuario
  - Manejo de múltiples sesiones de usuario simultáneas
- Capacidad para recargar las categorías en tiempo de ejecución sin reiniciar el bot
- Integración con Google Sheets para almacenar las transacciones en hojas específicas del usuario
- Uso de `pathlib.Path` para manejo moderno de rutas de archivos
- Sistema de estados para gestionar flujos de conversación con robustez
- Sistema avanzado de manejo de errores y recuperación
- **Sistema de tipado estático completo:**
  - Anotaciones de tipo en todas las interfaces públicas
  - Uso de características modernas de tipado de Python 3.9+
  - Documentación de tipos detallada
- **Sistema de pruebas completo:**
  - Pruebas unitarias para los componentes del bot
  - Pruebas para la integración con Google Sheets
  - Pruebas para la autenticación OAuth
  - Pruebas para el servidor de redirección
  - Mocks para APIs externas (Telegram, Google)

### Progreso y logros hasta la fecha
- Implementación completa del sistema de autenticación OAuth 2.0
- Migración desde autenticación por cuenta de servicio a OAuth 2.0
- Soporte para múltiples usuarios con acceso a sus propias hojas
- Integración de un servidor web para manejar redirecciones OAuth
- Implementación de flujo completo de autorización y selección de hojas
- Gestión segura de tokens por usuario
- Refresco automático de tokens expirados
- Navegación intuitiva entre diferentes hojas de cálculo
- Mejora en la seguridad al no requerir compartir hojas con una cuenta de servicio
- Mejoras en el mensaje de inicio para guiar al usuario en el proceso de autenticación
- Implementación de verificaciones de autenticación en todas las operaciones relevantes
- Mejoras significativas en el manejo de errores relacionados con autenticación
- Las hojas "gastos" e "ingresos" incluyen columnas para categoría, subcategoría y comentario
- Comando `/help` actualizado con los nuevos comandos disponibles
- Implementación completa del sistema de tipado estático moderno

### Documentación técnica existente
- Docstrings detallados en clases y métodos principales
- README.md actualizado con instrucciones para OAuth 2.0
- Documentación de pruebas en tests/README.md
- Estructura del proyecto bien organizada y documentada
- Archivo YAML con documentación clara sobre las categorías
- Documento de transferencia detallado actualizado con la implementación OAuth (este documento)

## 5. Desafíos y consideraciones técnicas

### Problemas conocidos o limitaciones
- No hay comandos para consultar o visualizar las transacciones registradas
- No hay validación avanzada para los valores ingresados por los usuarios
- No hay mecanismos para la edición o eliminación de transacciones erróneas
- El manejo asíncrono entre Python y python-telegram-bot puede ser complejo:
  - Se ha implementado una solución utilizando post_init callbacks para el registro de comandos
  - Pueden surgir advertencias relacionadas con coroutines no esperadas, que no afectan la funcionalidad
- Potenciales errores en el manejo de comentarios cuando el estado de la conversación se pierde
- El servidor OAuth requiere acceso a puertos en el servidor para redirecciones
- En entornos de producción, se requiere un dominio público con HTTPS para las redirecciones OAuth
- Los tokens OAuth se almacenan en archivos sin cifrado, lo que podría representar un riesgo de seguridad

### Deuda técnica acumulada
- La estructura para modelos y servicios está creada pero sin implementación completa
- No hay validación de datos exhaustiva para las entradas financieras
- Las cargas asíncronas para múltiples componentes no están implementadas de manera óptima
- No hay documentación de usuario final completa
- Faltan pruebas para algunos escenarios específicos con las nuevas funcionalidades OAuth:
  - Pruebas de integración completa del flujo OAuth
  - Pruebas para el manejo de tokens expirados
  - Pruebas para la comunicación entre servidor OAuth y bot
- El manejo de cierre del servidor OAuth podría mejorarse para garantizar una terminación limpia
- No hay verificación estática de tipos configurada en el flujo de CI/CD

### Optimizaciones pendientes
- Implementar cifrado para los tokens almacenados
- Implementar expiración de sesiones para usuarios inactivos
- Mejorar la gestión de errores específicos de OAuth
- Implementar caching para reducir llamadas a la API de Google
- Mejorar el manejo de errores para situaciones específicas
- Implementar validación de datos avanzada para las entradas financieras
- Integrar herramientas automáticas de análisis de código (linters, formatters)
- Añadir verificación estática de tipos con mypy
- Mejorar el manejo asíncrono de operaciones para evitar advertencias
- Mejorar la comunicación entre el servidor OAuth y el bot:
  - Implementar mecanismo más robusto para comunicar códigos de autorización
  - Manejar timeouts en el proceso de autorización

## 6. Hoja de ruta

### Próximos pasos inmediatos
1. Implementar cifrado para los tokens almacenados en disco
2. Mejorar el manejo de errores específicos para OAuth
3. Implementar comando para consultar transacciones recientes incluyendo comentarios
4. Implementar comando para visualizar resúmenes (ej: gastos por categoría) por usuario
5. Mejorar la validación de datos de entrada en todos los campos
6. Añadir funcionalidad para editar o eliminar transacciones
7. Implementar pruebas para las nuevas funcionalidades OAuth
8. Configurar verificación estática de tipos con mypy
9. Mejorar documentación de usuario final para el proceso de autenticación

### Características planificadas a medio/largo plazo
1. Implementar reportes y análisis financieros más avanzados por usuario
2. Agregar funcionalidades de presupuestos y alertas
3. Integrar gráficos y visualizaciones a través de Telegram
4. Permitir exportación de datos en diferentes formatos
5. Implementar análisis inteligente de patrones de gasto
6. Permitir compartir hojas entre múltiples usuarios (colaboración)
7. Búsquedas por texto en comentarios y filtrado de transacciones
8. Implementar notificaciones programadas y recordatorios
9. Añadir soporte para múltiples monedas y conversión automática

### Cronograma tentativo
Información no disponible: No se ha establecido un cronograma formal para el desarrollo.

## 7. Decisiones clave

### Elecciones arquitectónicas importantes y sus justificaciones
1. **Migración de service_account a OAuth 2.0**: Permite a cada usuario utilizar sus propias hojas, mejorando la privacidad y evitando la necesidad de compartir hojas con una cuenta de servicio.
2. **Servidor Flask para redirecciones OAuth**: Proporciona una forma simple y eficiente de manejar el callback de redirección de OAuth, ejecutándose en un hilo separado para no bloquear el bot.
3. **Gestor OAuth centralizado**: Encapsula toda la lógica de autenticación en una clase dedicada, facilitando la gestión de tokens y credenciales.
4. **Almacenamiento de tokens por usuario**: Permite mantener múltiples sesiones de usuario simultáneas y persistentes entre reinicios del bot.
5. **Uso de python-telegram-bot**: Proporciona una API moderna y asíncrona para interactuar con la API de Telegram.
6. **Uso de gspread con OAuth**: Ofrece una interfaz sencilla para acceder a hojas específicas del usuario.
7. **Estructura modular**: Facilita la extensión y mantenimiento del código, con clara separación de responsabilidades.
8. **Sistema de tipado moderno (Python 3.9+)**: Mejora la legibilidad, documentación y verificación de código con menor sobrecarga visual.
9. **Loguru para logging**: Proporciona una interfaz más amigable y potente que el módulo logging estándar.
10. **Pytest y pytest-mock para pruebas**: Framework moderno con mejor soporte para fixtures y mocking que unittest.
11. **Sistema de estados para conversación**: Permite un flujo robusto y recuperable, facilitando la gestión de la conversación por etapas.
12. **Verificación preventiva de datos**: Validación de la existencia de datos antes de procesarlos para evitar errores por pérdida de estado.

### Compensaciones (trade-offs) técnicos realizados
1. **Complejidad vs. Flexibilidad**: La implementación de OAuth 2.0 aumenta la complejidad del sistema, pero ofrece mayor flexibilidad y seguridad para los usuarios.
2. **Servidor local vs. Servicio externo**: Se optó por implementar un servidor local para OAuth, lo que simplifica el desarrollo pero requiere consideraciones adicionales para producción.
3. **Almacenamiento de tokens en archivos vs. Base de datos**: Se eligió almacenar tokens en archivos por simplicidad, sacrificando algunas características de seguridad y escalabilidad.
4. **Telegram como interfaz principal**: Se optó por Telegram por su accesibilidad y simplicidad, aunque limita algunas opciones de UI avanzadas.
5. **Google Sheets como base de datos**: Se eligió por su facilidad de uso y visualización, aunque no tiene las capacidades de un sistema de base de datos completo.
6. **Pruebas con pytest-mock vs unittest.mock**: Se eligió pytest-mock por su mejor integración con pytest y sintaxis más limpia, aunque requiere una dependencia adicional.
7. **Flujo guiado vs. entrada libre**: Se implementó un flujo guiado por pasos usando botones, lo que mejora la experiencia de usuario pero requiere más complejidad en el código.
8. **Manejadores específicos vs. manejadores generales**: Se implementaron manejadores específicos para OAuth, lo que mejora la organización del código pero aumenta la complejidad de la estructura.
9. **Robustez vs. rendimiento**: Se implementaron múltiples verificaciones y logging para garantizar la robustez, aceptando un ligero impacto en el rendimiento.
10. **Tipado moderno vs. compatibilidad con versiones antiguas**: Se eligió el tipado moderno (Python 3.9+) por su claridad y concisión, sacrificando la compatibilidad con versiones anteriores de Python.

### Lecciones aprendidas durante el desarrollo
- La autenticación OAuth 2.0 requiere una cuidadosa planificación del flujo de usuario.
- La comunicación entre un servidor web y un bot de Telegram requiere mecanismos de sincronización.
- El manejo de tokens requiere consideraciones de seguridad importantes.
- La gestión de estados de usuario es crucial para mantener la coherencia de la aplicación.
- La correcta estructura y modularización desde el inicio facilita la extensión del proyecto.
- La implementación de flujos interactivos con botones mejora significativamente la experiencia de usuario.
- El registro detallado de eventos (logging) es indispensable para identificar problemas en producción.
- La verificación de autenticación debe realizarse en cada punto donde se accede a recursos protegidos.
- El manejo correcto de errores de autenticación mejora significativamente la experiencia de usuario.
- Cada usuario puede tener diferentes necesidades y estructuras de hojas de cálculo.
- Las anotaciones de tipo modernas mejoran significativamente la documentación del código y reducen errores.
- La consistencia en el estilo de tipado es importante para la mantenibilidad del código.

## 8. Recursos adicionales

### Enlaces a repositorios, documentación o diagramas
Información no disponible: No se han proporcionado enlaces a repositorios externos o documentación adicional.

### Contactos clave para consultas
Información no disponible: No se han especificado contactos para este proyecto.

### Información sobre entornos de prueba/producción
El proyecto está configurado para ejecutarse en un entorno local de desarrollo. Para un entorno de producción, se recomienda:
- Configurar un dominio público con HTTPS para las redirecciones OAuth
- Registrar el dominio público en Google Cloud Platform
- Implementar medidas de seguridad adicionales para los tokens almacenados
- Configurar un sistema de monitoreo para el servidor OAuth y el bot

Las pruebas se ejecutan utilizando pytest y pueden ser iniciadas con:
- `pytest`: Ejecuta las pruebas
- `pytest --cov=src`: Ejecuta las pruebas con informe de cobertura

Se recomienda implementar verificación estática de tipos con:
- `mypy src/`: Verifica tipos estáticos en el código

## Instrucciones para continuar el desarrollo

1. Clonar el repositorio (o acceder a la carpeta `/home/somebody/dev/finanzas`)
2. Crear un entorno virtual: `uv venv .venv`
3. Activar el entorno: `.venv/bin/activate` (Linux/Mac) o `.venv\Scripts\activate` (Windows)
4. Instalar dependencias: `uv pip install -r requirements.txt`
5. Para desarrollo, instalar dependencias adicionales: `uv pip install -r requirements-dev.txt`
6. Configurar variables de entorno copiando `.env.example` a `.env` y completando los valores
7. Configurar OAuth en Google Cloud Platform:
   - Crear un proyecto si no existe
   - Habilitar APIs de Google Sheets y Google Drive
   - Crear credenciales OAuth 2.0 para aplicación web
   - Añadir URI de redirección: `http://localhost:8000/oauth2callback`
   - Descargar el JSON de credenciales y guardarlo como `oauth_credentials.json`
8. Ejecutar pruebas: `pytest` o `pytest --cov=src`
9. Ejecutar la aplicación: `python main.py`

## Cambios recientes importantes

Las modificaciones más significativas en la última versión (v3.0) incluyen:

1. **Implementación completa de autenticación OAuth 2.0:**
   - Reemplazo del sistema de autenticación basado en service_account
   - Implementación del gestor de autenticación OAuth
   - Creación de servidor para redirecciones OAuth
   - Soporte para múltiples usuarios con sus propias hojas

2. **Nuevos comandos para gestión de hojas:**
   - `/auth`: Iniciar proceso de autenticación
   - `/list`: Listar hojas disponibles del usuario
   - `/sheet`: Seleccionar hoja activa
   - `/logout`: Cerrar sesión y revocar acceso

3. **Mejoras en la estructura del proyecto:**
   - Nuevo módulo `auth` para autenticación OAuth
   - Nuevo módulo `server` para servidor de redirecciones
   - Reorganización de manejadores en submódulo `handlers`

4. **Mejoras en la gestión de usuarios:**
   - Soporte para múltiples usuarios simultáneos
   - Almacenamiento y gestión de tokens por usuario
   - Verificación de autenticación en operaciones críticas

5. **Actualizaciones en la configuración:**
   - Nuevas variables de entorno para OAuth
   - Soporte para configuración de servidor de redirección
   - Actualización de documentación y ejemplos

6. **Sistema de tipado mejorado:**
   - Adopción completa de características de tipado de Python 3.9+
   - Uso de operador de unión `|` para tipos múltiples
   - Simplificación del código usando tipos integrados directamente
   - Documentación detallada del enfoque de tipado

Estas modificaciones transforman significativamente el sistema, convirtiéndolo en una solución multi-usuario donde cada persona puede interactuar con sus propias hojas de cálculo, mejorando la privacidad y flexibilidad del servicio, además de mejorar la calidad del código a través de un sistema de tipado moderno y consistente.
