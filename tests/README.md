# Pruebas del Sistema de Gestión Financiera

Este directorio contiene las pruebas automatizadas para el Sistema de Gestión Financiera, con enfoque en los componentes del bot de Telegram y la integración con Google Sheets.

## Estructura de las pruebas

Las pruebas están organizadas en varios archivos según los componentes del sistema:

- **test_bot.py**: Pruebas para la clase `TelegramBot` y sus funcionalidades
- **test_commands.py**: Pruebas para los comandos definidos del bot
- **test_handlers.py**: Pruebas detalladas para los manejadores de comandos
- **test_sheets.py**: Pruebas para la integración con Google Sheets
- **conftest.py**: Fixtures compartidos para todas las pruebas

## Requisitos

Para ejecutar las pruebas, necesitas tener instalado:

- Python 3.9+
- pytest
- pytest-asyncio (para probar código asíncrono)
- pytest-cov (para medir la cobertura de código)
- pytest-mock (para crear mocks fácilmente)

Puedes instalar estos requisitos con:

```bash
uv pip install pytest pytest-asyncio pytest-cov pytest-mock
```

## Ejecutar las pruebas

Para ejecutar todas las pruebas:

```bash
pytest
```

Para ejecutar las pruebas con cobertura de código:

```bash
pytest --cov=src
```

Para ejecutar un archivo de pruebas específico:

```bash
pytest tests/test_bot.py
```

Para ejecutar una prueba específica:

```bash
pytest tests/test_bot.py::test_bot_initialization
```

## Enfoque de pruebas

Este proyecto usa pytest como framework de pruebas principal, junto con pytest-mock para la creación de mocks:

1. **Estructura de pruebas**: Usando funciones de pytest en lugar de clases TestCase de unittest
2. **Mocks**: Usando `pytest-mock` a través del fixture `mocker` para simular objetos y comportamientos
3. **Fixtures**: Usando el sistema de fixtures de pytest para configuración reutilizable
4. **Pruebas asíncronas**: Con pytest-asyncio para probar código asíncrono

### Ventajas de usar pytest-mock

- **Integración perfecta con pytest**: El fixture `mocker` se integra de forma nativa
- **Sintaxis más limpia**: No es necesario usar decoradores como `@patch`
- **Alcance automático**: Los mocks se limitan al alcance de la prueba
- **Métodos útiles**: Incluye `mocker.patch`, `mocker.Mock`, `mocker.AsyncMock` y otros
- **Mejores mensajes de error**: Mensajes más claros y específicos al fallar las pruebas

## Mocking de APIs externas

### Bot de Telegram

Para evitar errores de "Invalid Token" al probar el bot de Telegram:

```python
# Ejemplo con pytest-mock
def test_bot_setup(mocker):
    # Crear objetos simulados
    mock_app = mocker.Mock()
    mock_app.bot = mocker.Mock()
    mock_app.bot.set_my_commands = mocker.AsyncMock()
    
    # Crear un mock para ApplicationBuilder
    mock_builder = mocker.Mock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app
    
    # Usar mocker.patch para reemplazar ApplicationBuilder
    mocker.patch("telegram.ext.ApplicationBuilder", return_value=mock_builder)
    
    # Ejecutar código que usa ApplicationBuilder
    # sin conectarse a la API real
```

### Google Sheets

Para las pruebas de la integración con Google Sheets:

```python
# Ejemplo con pytest-mock
def test_client_authentication(mocker):
    # Arrange
    mock_client = mocker.Mock()
    mock_credentials = mocker.Mock()
    
    # Mock para Credentials.from_service_account_file
    mock_creds = mocker.patch("google.oauth2.service_account.Credentials.from_service_account_file")
    mock_creds.return_value = mock_credentials
    
    # Mock para gspread.authorize
    mock_authorize = mocker.patch("gspread.authorize")
    mock_authorize.return_value = mock_client
```

## Comparación: pytest-mock vs unittest.mock

| Característica | pytest-mock | unittest.mock |
|----------------|-------------|---------------|
| Integración con pytest | Nativa (fixture) | Requiere importación |
| Sintaxis | Más concisa | Más verbosa (decoradores) |
| Alcance | Automático (por test) | Manual (requiere context manager o decorador) |
| Métodos de aserción | Incluye assert_called_once | Incluye assert_called_once |
| Métodos asíncronos | Soporta AsyncMock | Soporta AsyncMock |
| Mensajes de error | Más claros | Menos informativos |

## Cobertura de código

El objetivo es mantener una cobertura de código de al menos 80% para todos los componentes.

Las áreas prioritarias son:
- La lógica de manejo de comandos
- La integración con Google Sheets
- El manejo de errores

## Ampliación de pruebas

Al agregar nuevas funcionalidades al bot, asegúrate de:

1. Crear nuevas pruebas para cada nueva función o método
2. Actualizar las pruebas existentes si cambias el comportamiento actual
3. Mantener la cobertura de código por encima del 80%
4. Ejecutar todas las pruebas antes de enviar cambios al repositorio

## Solución de problemas comunes

### Error: "fixture 'mocker' not found"

Este error ocurre cuando pytest-mock no está instalado. La solución es:
- Ejecutar `pip install pytest-mock` o `uv pip install pytest-mock`

### Error: "InvalidToken: Not Found"

Este error ocurre cuando las pruebas intentan usar un token real para conectarse a la API de Telegram. La solución es:
- Usar `mocker.patch` para reemplazar `ApplicationBuilder`
- Proporcionar un mock completo para el objeto `Application`
- Asegurarse de que todos los métodos asíncronos tengan `mocker.AsyncMock`

### Error: "PytestUnhandledCoroutineWarning"

Este error ocurre cuando pytest no puede manejar funciones asíncronas. La solución es:
- Instalar `pytest-asyncio`
- Agregar el decorador `@pytest.mark.asyncio` a las pruebas asíncronas
- Configurar `asyncio_mode = auto` en `pytest.ini`

## Mejoras futuras

Áreas para mejorar en las pruebas:

- Agregar pruebas de integración end-to-end
- Implementar pruebas para comandos financieros específicos
- Crear fixtures más avanzados para datos financieros de ejemplo
- Automatizar las pruebas en un pipeline de CI/CD
