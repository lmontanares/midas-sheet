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

Para ejecutar las pruebas:

```bash
pytest
```

Para verificar la cobertura:

```bash
pytest --cov=src tests/
```

## Licencia

Este proyecto está licenciado bajo MIT License.
