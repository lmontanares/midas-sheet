# Documento de Transferencia: Sistema de Gestión Financiera v2.0

## 1. Visión general del proyecto

### Propósito fundamental y objetivos principales
El Sistema de Gestión Financiera es una aplicación diseñada para facilitar el seguimiento y control de finanzas personales a través de un bot de Telegram integrado con Google Sheets. El objetivo principal es proporcionar una herramienta accesible que permita a los usuarios registrar y consultar sus ingresos y gastos de manera sencilla desde cualquier dispositivo con Telegram.

### Descripción de la funcionalidad central
El sistema consta de dos componentes principales que trabajan de forma integrada:
1. Un bot de Telegram que sirve como interfaz de usuario para registrar transacciones financieras y consultar información.
2. Un módulo de integración con Google Sheets que almacena y gestiona los datos financieros en la nube.

El usuario interactúa con el bot siguiendo un flujo específico para registrar transacciones:
1. El usuario envía el comando `/agregar`
2. Elige tipo de transacción (ingreso o egreso)
3. Selecciona una categoría
4. Si seleccionó un egreso, selecciona una subcategoría (los ingresos no tienen subcategorías)
5. Ingresa el monto de la transacción
6. El sistema registra la transacción en la hoja de cálculo correspondiente

### Problemas que resuelve y valor que aporta
- Simplifica el registro de gastos e ingresos sin necesidad de aplicaciones complejas
- Permite acceder y gestionar información financiera desde cualquier dispositivo con Telegram
- Centraliza los datos financieros en Google Sheets, facilitando análisis posteriores
- Elimina la necesidad de herramientas costosas o complejas de finanzas personales
- Proporciona una estructura jerárquica para categorizar gastos, facilitando análisis detallados

## 2. Ecosistema tecnológico

### Lenguajes de programación utilizados
- Python 3.9+ (aprovechando características modernas de tipado)

### Frameworks, bibliotecas y dependencias principales
- **Bot de Telegram:**
  - python-telegram-bot (v20.6+): Framework para la creación del bot
- **Google Sheets:**
  - gspread: Biblioteca para interactuar con Google Sheets
  - google-auth: Autenticación con servicios de Google
- **Utilidades:**
  - loguru: Sistema avanzado de logging
  - python-dotenv: Gestión de variables de entorno
  - pydantic: Validación de datos
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
La arquitectura sigue un patrón modular con separación clara de responsabilidades:

```
Usuario (Telegram) → Bot de Telegram → Módulo de Google Sheets → Hoja de cálculo
        ↑                   ↓                     ↓
        └───────────────────┴─────────────────────┘
            (Respuestas y visualizaciones)
```

El flujo de información comienza cuando el usuario envía comandos al bot a través de Telegram. El bot procesa estos comandos y, según sea necesario, interactúa con el módulo de Google Sheets para leer o escribir datos en la hoja de cálculo. Finalmente, el bot envía respuestas al usuario basadas en el resultado de estas operaciones.

### Estructura de componentes/módulos
```
/finanzas/
│
├── src/                  # Código fuente
│   ├── bot/              # Lógica del bot de Telegram
│   │   ├── bot.py        # Configuración principal del bot
│   │   ├── handlers.py   # Manejadores de mensajes y comandos
│   │   └── commands.py   # Definiciones de comandos
│   │
│   ├── sheets/           # Integración con Google Sheets
│   │   ├── client.py     # Cliente para conectar con Google Sheets
│   │   └── operations.py # Operaciones con las hojas de cálculo
│   │
│   └── utils/            # Utilidades comunes
│       ├── config.py     # Configuración y variables de entorno
│       └── logger.py     # Configuración de logging
│
├── tests/                # Pruebas automatizadas
│   ├── test_bot.py       # Pruebas para el bot de Telegram
│   ├── test_commands.py  # Pruebas para los comandos del bot
│   ├── test_handlers.py  # Pruebas para los manejadores del bot
│   ├── test_sheets.py    # Pruebas para la integración con Google Sheets
│   ├── conftest.py       # Fixtures compartidos para pruebas
│   └── README.md         # Documentación de pruebas
│
├── main.py               # Punto de entrada de la aplicación
├── pyproject.toml        # Configuración del proyecto Python
├── pytest.ini            # Configuración de pytest
├── .env                  # Variables de entorno (local)
├── .env.example          # Ejemplo de variables de entorno
├── credentials.json      # Credenciales de Google API
└── README.md             # Documentación principal
```

### Patrones de diseño implementados
- **Patrón Cliente**: Encapsulación del acceso a Google Sheets en una clase cliente (`GoogleSheetsClient`)
- **Patrón Factory**: Creación de manejadores para el bot de Telegram (en `commands.py`)
- **Propiedades (@property)**: Para el acceso controlado a la configuración (en `config.py`)
- **Inyección de dependencias**: Las clases reciben sus dependencias en el constructor (por ejemplo, `TelegramBot` recibe `SheetsOperations`)
- **Nombres en inglés con documentación en español**: Convención adoptada donde los nombres de clases, funciones y variables están en inglés, pero los comentarios y documentación están en español

## 4. Estado actual del desarrollo

### Características implementadas y funcionalidades completas
- Estructura básica completa del proyecto con organización modular
- Configuración inicial para el bot de Telegram implementada
- Manejadores para comandos `/start`, `/help`, y `/agregar`
- Configuración inicial para la integración con Google Sheets
- Sistema de logging con Loguru implementado
- Implementación completa del comando `/agregar` con flujo interactivo mediante botones
- Categorías predefinidas hardcodeadas en el código:
  - Categorías de gastos con estructura jerárquica (categorías y subcategorías)
  - Categorías de ingresos simples sin subcategorías
- Integración con Google Sheets para almacenar las transacciones
- **Sistema de pruebas completo**:
  - Pruebas unitarias para los componentes del bot
  - Pruebas para la integración con Google Sheets
  - Mocks para APIs externas (Telegram, Google Sheets)
  - Fixtures compartidos para facilitar las pruebas
  - Alta cobertura de código (>95%)

### Progreso y logros hasta la fecha
- Implementación completa del esqueleto del proyecto con estructura modular
- Implementación básica de la autenticación con Google Sheets
- Configuración funcional del bot de Telegram
- Gestión de configuración mediante variables de entorno
- Implementación del mecanismo de logging con rotación de archivos
- Implementación del comando `/agregar` con soporte para:
  - Selección de tipo de transacción (ingreso/egreso)
  - Selección de categorías mediante botones
  - Selección de subcategorías para gastos
  - Entrada de montos
  - Registro en hojas de cálculo
- Las categorías y subcategorías están ahora hardcodeadas en el código en lugar de obtenerse de la hoja de cálculo
- Las hojas "gastos" e "ingresos" incluyen ahora columnas para categoría y subcategoría

### Documentación técnica existente
- Docstrings detallados en clases y métodos principales
- README.md con instrucciones de instalación y uso
- Documentación de pruebas en tests/README.md
- Estructura del proyecto bien organizada y documentada

## 5. Desafíos y consideraciones técnicas

### Problemas conocidos o limitaciones
- Las categorías y subcategorías están hardcodeadas en el código y no se pueden modificar fácilmente
- No hay comandos para consultar o visualizar las transacciones registradas
- No hay manejo de múltiples usuarios (no hay autenticación ni autorización)
- No hay validación avanzada para los valores ingresados por los usuarios
- No hay mecanismos para la edición o eliminación de transacciones erróneas

### Deuda técnica acumulada
- La estructura para modelos y servicios está creada pero sin implementación completa
- No hay validación de datos exhaustiva para las entradas financieras
- Las categorías hardcodeadas dificultan su mantenimiento y actualización
- No hay documentación de usuario final
- Faltan pruebas para algunos escenarios específicos con las nuevas funcionalidades

### Optimizaciones pendientes
- Implementar caching para reducir llamadas a la API de Google
- Mejorar el manejo de errores para situaciones específicas
- Implementar validación de datos avanzada para las entradas financieras
- Integrar herramientas automáticas de análisis de código (linters, formatters)
- Permitir la configuración de categorías desde un archivo externo o desde la interfaz de usuario

## 6. Hoja de ruta

### Próximos pasos inmediatos
1. Implementar comando para consultar transacciones recientes
2. Implementar comando para visualizar resúmenes (ej: gastos por categoría)
3. Mejorar la validación de datos de entrada
4. Añadir funcionalidad para editar o eliminar transacciones
5. Permitir la personalización de categorías sin modificar el código

### Características planificadas a medio/largo plazo
1. Implementar reportes y análisis financieros más avanzados
2. Agregar funcionalidades de presupuestos y alertas
3. Integrar gráficos y visualizaciones a través de Telegram
4. Permitir exportación de datos en diferentes formatos
5. Implementar análisis inteligente de patrones de gasto
6. Soporte para múltiples usuarios y perfiles

### Cronograma tentativo
Información no disponible: No se ha establecido un cronograma formal para el desarrollo.

## 7. Decisiones clave

### Elecciones arquitectónicas importantes y sus justificaciones
1. **Uso de python-telegram-bot**: Proporciona una API moderna y asíncrona para interactuar con la API de Telegram.
2. **Uso de gspread**: Ofrece una interfaz más sencilla y directa que la API oficial de Google Sheets.
3. **Estructura modular**: Facilita la extensión y mantenimiento del código, con clara separación de responsabilidades.
4. **Loguru para logging**: Proporciona una interfaz más amigable y potente que el módulo logging estándar.
5. **Pytest y pytest-mock para pruebas**: Framework moderno con mejor soporte para fixtures y mocking que unittest.
6. **Separación en models, services, bot, sheets**: Facilita la evolución independiente de cada componente.
7. **Categorías hardcodeadas**: Se decidió incluir las categorías directamente en el código para simplificar el desarrollo inicial, con planes de hacerlas configurables en el futuro.
8. **Nombres en inglés, documentación en español**: Para seguir las mejores prácticas de desarrollo (nombres en inglés) mientras se mantiene la accesibilidad para desarrolladores hispanohablantes.

### Compensaciones (trade-offs) técnicos realizados
1. **Simplicidad vs. Funcionalidad completa**: Se priorizó crear una estructura clara y simple sobre implementar todas las funcionalidades posibles.
2. **Telegram como interfaz principal**: Se optó por Telegram como interfaz principal por su accesibilidad y simplicidad, aunque limita algunas opciones de UI avanzadas.
3. **Google Sheets como base de datos**: Se eligió por su facilidad de uso y visualización, aunque no tiene las capacidades de un sistema de base de datos completo.
4. **Pruebas con pytest-mock vs unittest.mock**: Se eligió pytest-mock por su mejor integración con pytest y sintaxis más limpia, aunque requiere una dependencia adicional.
5. **Categorías hardcodeadas vs. configurables**: Se optó por definir las categorías en el código para acelerar el desarrollo inicial, sacrificando la flexibilidad.
6. **Flujo guiado vs. entrada libre**: Se implementó un flujo guiado por pasos usando botones, lo que mejora la experiencia de usuario pero requiere más complejidad en el código.

### Lecciones aprendidas durante el desarrollo
- La importancia de implementar un enfoque de testing robusto desde el inicio del proyecto.
- El uso correcto de mocks es crucial para evitar problemas con APIs externas durante las pruebas.
- La correcta estructura y modularización desde el inicio facilita la extensión del proyecto.
- La documentación detallada de las pruebas facilita la comprensión del comportamiento esperado del sistema.
- La implementación de flujos interactivos con botones mejora significativamente la experiencia de usuario.
- Definir un formato claro para los callback data es esencial para manejar las interacciones con botones.

## 8. Recursos adicionales

### Enlaces a repositorios, documentación o diagramas
Información no disponible: No se han proporcionado enlaces a repositorios externos o documentación adicional.

### Contactos clave para consultas
Información no disponible: No se han especificado contactos para este proyecto.

### Información sobre entornos de prueba/producción
El proyecto está configurado para ejecutarse en un entorno local de desarrollo. No hay configuración específica para entornos de prueba o producción en esta etapa. Las pruebas se ejecutan utilizando pytest y pueden ser iniciadas con:
- `pytest`: Ejecuta las pruebas
- `pytest --cov=src`: Ejecuta las pruebas con informe de cobertura

## Instrucciones para continuar el desarrollo

1. Clonar el repositorio (o acceder a la carpeta `/home/somebody/dev/finanzas`)
2. Crear un entorno virtual: `uv venv .venv`
3. Activar el entorno: `.venv/bin/activate` (Linux/Mac) o `.venv\Scripts\activate` (Windows)
4. Instalar dependencias: `uv pip install -r requirements.txt`
5. Para desarrollo, instalar dependencias adicionales: `uv pip install -r requirements-dev.txt`
6. Configurar variables de entorno copiando `.env.example` a `.env` y completando los valores
7. Ejecutar pruebas: `pytest` o `pytest --cov=src`
8. Ejecutar la aplicación: `python main.py`

## Cambios recientes importantes

Las modificaciones más significativas en la última versión incluyen:

1. **Implementación del comando `/agregar`**:
   - Flujo completo de registro de transacciones con interfaz interactiva mediante botones
   - Soporte para selección de categorías y subcategorías

2. **Categorías predefinidas**:
   - Las categorías de gastos están organizadas jerárquicamente (con subcategorías)
   - Las categorías de ingresos no tienen subcategorías
   - Se han hardcodeado directamente en el código para simplificar la implementación inicial

3. **Estructura de datos**:
   - Las hojas "gastos" e "ingresos" tienen columnas para categoría y subcategoría
   - El formato de datos incluye: Fecha, Usuario, Categoría, Subcategoría, Monto, Timestamp

4. **Flujo de interacción**:
   - Se implementó un flujo específico: comando → tipo → categoría → subcategoría (solo para gastos) → monto
   - Uso de InlineKeyboardMarkup para crear botones interactivos

5. **Convención de nomenclatura**:
   - Se adoptó la convención de usar nombres en inglés para variables, funciones y clases
   - La documentación y comentarios se mantienen en español