# Documento de Transferencia: Sistema de Gestión Financiera

## 1. Visión general del proyecto

### Propósito fundamental y objetivos principales
El Sistema de Gestión Financiera es una aplicación diseñada para facilitar el seguimiento y control de finanzas personales a través de un bot de Telegram integrado con Google Sheets. El objetivo principal es proporcionar una herramienta accesible que permita a los usuarios registrar y consultar sus ingresos y gastos de manera sencilla desde cualquier dispositivo con Telegram.

### Descripción de la funcionalidad central
El sistema consta de dos componentes principales que trabajan de forma integrada:
1. Un bot de Telegram que sirve como interfaz de usuario para registrar transacciones financieras y consultar información.
2. Un módulo de integración con Google Sheets que almacena y gestiona los datos financieros en la nube.

### Problemas que resuelve y valor que aporta
- Simplifica el registro de gastos e ingresos sin necesidad de aplicaciones complejas
- Permite acceder y gestionar información financiera desde cualquier dispositivo con Telegram
- Centraliza los datos financieros en Google Sheets, facilitando análisis posteriores
- Elimina la necesidad de herramientas costosas o complejas de finanzas personales

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
├── requirements.txt      # Dependencias del proyecto
├── requirements-dev.txt  # Dependencias de desarrollo y pruebas
├── run_tests.sh          # Script para ejecutar pruebas
├── setup_tests.sh        # Script para configurar entorno de pruebas
├── pytest.ini            # Configuración de pytest
└── README.md             # Documentación principal
```

### Patrones de diseño implementados
- **Patrón Cliente**: Encapsulación del acceso a Google Sheets en una clase cliente
- **Patrón Factory**: Creación de manejadores para el bot de Telegram
- **Propiedades (@property)**: Para el acceso controlado a la configuración
- **Inyección de dependencias**: Las clases reciben sus dependencias en el constructor

## 4. Estado actual del desarrollo

### Características implementadas y funcionalidades completas
- Estructura básica completa del proyecto con organización modular
- Configuración inicial para el bot de Telegram implementada
- Manejadores básicos para comandos `/start` y `/help`
- Configuración inicial para la integración con Google Sheets
- Sistema de logging con Loguru implementado
- **Sistema de pruebas completo**:
  - Pruebas unitarias para los componentes del bot
  - Pruebas para la integración con Google Sheets
  - Mocks para APIs externas (Telegram, Google Sheets)
  - Fixtures compartidos para facilitar las pruebas
  - Scripts para ejecución de pruebas
  - Documentación detallada de pruebas
  - Alta cobertura de código (>95%)

### Progreso y logros hasta la fecha
- Esqueleto completo del proyecto con estructura modular
- Implementación básica de la autenticación con Google Sheets
- Configuración base para el bot de Telegram
- Gestión de configuración mediante variables de entorno
- Implementación de un sistema de pruebas robusto y completo
- Mocking correcto de APIs externas para evitar errores en pruebas
- Documentación completa del sistema de pruebas

### Documentación técnica existente
- Docstrings en clases y métodos principales
- README.md con instrucciones de instalación y uso
- Documentación detallada de pruebas en tests/README.md
- Scripts documentados para ejecución y configuración
- Estructura del proyecto bien organizada y documentada

## 5. Desafíos y consideraciones técnicas

### Problemas conocidos o limitaciones
- El proyecto está en fase de esqueleto, sin implementación completa de funcionalidades financieras
- No hay mecanismos de manejo avanzado de errores implementados
- Falta la implementación de la lógica de negocio para finanzas
- No existen comandos específicos para registro de transacciones financieras

### Deuda técnica acumulada
- Información incompleta: Al estar en fase inicial, no se ha acumulado deuda técnica significativa.
- Las pruebas están implementadas con un enfoque "test-first", por lo que presentan una buena base para el desarrollo futuro.

### Optimizaciones pendientes
- Implementar caching para reducir llamadas a la API de Google
- Mejorar el manejo de errores para situaciones específicas
- Implementar validación de datos avanzada para las entradas financieras
- Integrar herramientas automáticas de análisis de código (linters, formatters)

## 6. Hoja de ruta

### Próximos pasos inmediatos
1. Implementar la lógica básica para registrar gastos e ingresos
2. Desarrollar la funcionalidad para categorizar transacciones
3. Crear visualizaciones simples de resúmenes financieros
4. Implementar persistencia de datos en Google Sheets
5. Crear nuevos comandos en el bot para funcionalidades financieras específicas

### Características planificadas a medio/largo plazo
1. Implementar reportes y análisis financieros
2. Agregar funcionalidades de presupuestos y alertas
3. Integrar gráficos y visualizaciones avanzadas
4. Permitir exportación de datos en diferentes formatos
5. Implementar análisis inteligente de patrones de gasto

### Cronograma tentativo
Información no disponible: No se ha establecido un cronograma formal para el desarrollo.

## 7. Decisiones clave

### Elecciones arquitectónicas importantes y sus justificaciones
1. **Uso de python-telegram-bot**: Proporciona una API moderna y asíncrona para interactuar con la API de Telegram.
2. **Uso de gspread**: Ofrece una interfaz más sencilla y directa que la API oficial de Google Sheets.
3. **Estructura modular**: Facilita la extensión y mantenimiento del código.
4. **Loguru para logging**: Proporciona una interfaz más amigable y potente que el módulo logging estándar.
5. **Pytest y pytest-mock para pruebas**: Framework moderno con mejor soporte para fixtures y mocking que unittest.

### Compensaciones (trade-offs) técnicos realizados
1. **Simplicidad vs. Funcionalidad completa**: Se priorizó crear una estructura clara y simple sobre implementar todas las funcionalidades posibles.
2. **Telegram como interfaz principal**: Se optó por Telegram como interfaz principal por su accesibilidad y simplicidad, aunque limita algunas opciones de UI avanzadas.
3. **Google Sheets como base de datos**: Se eligió por su facilidad de uso y visualización, aunque no tiene las capacidades de un sistema de base de datos completo.
4. **Pruebas con pytest-mock vs unittest.mock**: Se eligió pytest-mock por su mejor integración con pytest y sintaxis más limpia, aunque requiere una dependencia adicional.

### Lecciones aprendidas durante el desarrollo
- La importancia de implementar un enfoque de testing robusto desde el inicio del proyecto.
- El uso correcto de mocks es crucial para evitar problemas con APIs externas durante las pruebas.
- La correcta estructura y modularización desde el inicio facilita la extensión del proyecto.
- La documentación detallada de las pruebas facilita la comprensión del comportamiento esperado del sistema.

## 8. Recursos adicionales

### Enlaces a repositorios, documentación o diagramas
Información no disponible: No se han proporcionado enlaces a repositorios externos o documentación adicional.

### Contactos clave para consultas
Información no disponible: No se han especificado contactos para este proyecto.

### Información sobre entornos de prueba/producción
El proyecto está configurado para ejecutarse en un entorno local de desarrollo. No hay configuración específica para entornos de prueba o producción en esta etapa. Las pruebas se ejecutan utilizando pytest y pueden ser iniciadas con los scripts proporcionados:
- `./setup_tests.sh`: Configura el entorno para pruebas
- `./run_tests.sh`: Ejecuta las pruebas con diferentes opciones

## Instrucciones para continuar el desarrollo

1. Clonar el repositorio (o acceder a la carpeta `/home/somebody/dev/finanzas`)
2. Crear un entorno virtual: `uv venv .venv`
3. Activar el entorno: `.venv/bin/activate` (Linux/Mac) o `.venv\Scripts\activate` (Windows)
4. Instalar dependencias: `uv pip install -r requirements.txt`
5. Para desarrollo, instalar dependencias adicionales: `uv pip install -r requirements-dev.txt`
6. Configurar variables de entorno copiando `.env.example` a `.env` y completando los valores
7. Ejecutar pruebas: `./run_tests.sh` o `pytest`
8. Ejecutar la aplicación: `python main.py`

Las áreas prioritarias para continuar el desarrollo son:
1. Implementar la lógica de negocio en el bot para capturar datos financieros
2. Desarrollar las operaciones CRUD en el módulo de Google Sheets
3. Expandir las pruebas unitarias para nuevos componentes implementados
4. Crear nuevos comandos específicos para funcionalidades financieras