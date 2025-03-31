# Sistema de Gestión Financiera

Este proyecto implementa un sistema de gestión financiera que consta de dos componentes principales:

1. Un bot de Telegram para interactuar con los usuarios
2. Un módulo de integración con Google Sheets para almacenar y gestionar datos financieros

## Requisitos

- Python 3.9 o superior
- Token de bot de Telegram (obtenido a través de [@BotFather](https://t.me/botfather))
- Credenciales de la API de Google (archivo JSON)
- Hoja de cálculo de Google Sheets con los permisos adecuados

## Instalación

### 1. Clonar el repositorio

```bash
git clone <repositorio>
cd finanzas
```

### 2. Crear y activar entorno virtual

Con el gestor de paquetes `uv`:

```bash
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
uv pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copiar el archivo de ejemplo y completar con los valores reales:

```bash
cp .env.example .env
```

Editar el archivo `.env` con:
- Token del bot de Telegram
- Ruta al archivo de credenciales de Google
- ID de la hoja de cálculo de Google Sheets

## Estructura del proyecto

```
/finanzas
│
├── src/                  # Código fuente
│   ├── bot/              # Lógica del bot de Telegram
│   ├── sheets/           # Integración con Google Sheets
│   └── utils/            # Utilidades comunes
│
├── tests/                # Pruebas automatizadas
│   ├── test_bot.py       # Pruebas para el bot de Telegram
│   ├── test_commands.py  # Pruebas para los comandos del bot
│   ├── test_handlers.py  # Pruebas para los manejadores del bot
│   ├── test_sheets.py    # Pruebas para la integración con Google Sheets
│   └── README.md         # Documentación de pruebas
│
├── main.py               # Punto de entrada principal
├── requirements.txt      # Dependencias del proyecto
└── README.md             # Documentación
```

## Uso

Para iniciar la aplicación:

```bash
python main.py
```

## Tests

### Ejecutar las pruebas

Para ejecutar todas las pruebas:

```bash
pytest
```

Para ejecutar pruebas específicas:

```bash
pytest tests/test_bot.py  # Solo pruebas del bot
pytest tests/test_sheets.py  # Solo pruebas de Google Sheets
```

### Cobertura de código

Para verificar la cobertura:

```bash
pytest --cov=src tests/
```

Para generar un informe detallado de cobertura en HTML:

```bash
pytest --cov=src --cov-report=html tests/
```

### Requisitos para pruebas

Las pruebas requieren:
- pytest
- pytest-asyncio (para pruebas asíncronas)
- pytest-cov (para medir cobertura)

## Licencia

Este proyecto está licenciado bajo MIT License.
