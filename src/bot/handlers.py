"""
Manejadores de mensajes y comandos para el bot de Telegram.
"""

import datetime

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from src.sheets.operations import SheetsOperations


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /start.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    user = update.effective_user
    await update.message.reply_text(f"¡Hola {user.first_name}! Soy el bot de gestión financiera.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /help.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    help_text = """
    *Comandos disponibles:*
    /start - Inicia el bot
    /help - Muestra este mensaje de ayuda
    /agregar <tipo> <monto> <categoría> [fecha] - Agrega una transacción financiera
        Ejemplo: /agregar gasto 50.50 comida
        Ejemplo: /agregar ingreso 1000 salario 2023-10-15

    Pronto se agregarán más funciones...
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /agregar.
    Permite añadir una transacción financiera a la hoja de cálculo.

    Formato: /agregar <tipo> <monto> <categoría> [fecha]

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador con los argumentos del comando
    """
    user = update.effective_user
    args = context.args

    # Obtener el objeto SheetsOperations del contexto del bot
    sheets_ops: SheetsOperations | None = context.bot_data.get("sheets_operations")

    if not sheets_ops:
        await update.message.reply_text("❗ Error: No se pudo acceder a la hoja de cálculo")
        logger.error("SheetsOperations no disponible en bot_data")
        return

    # Verificar que hay suficientes argumentos
    if not args or len(args) < 3:
        await update.message.reply_text(
            "⚠️ Formato incorrecto. Usa: /agregar <tipo> <monto> <categoría> [fecha]\n"
            "Ejemplo: /agregar gasto 50.50 comida\n"
            "Ejemplo: /agregar ingreso 1000 salario 2023-10-15"
        )
        return

    # Extraer los argumentos
    tipo = args[0].lower()
    if tipo not in ["gasto", "ingreso"]:
        await update.message.reply_text("⚠️ El tipo debe ser 'gasto' o 'ingreso'")
        return

    # Validar y convertir el monto
    try:
        monto = float(args[1])
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser un número positivo")
            return
    except ValueError:
        await update.message.reply_text("⚠️ El monto debe ser un número válido")
        return

    # Verificar que la categoría sea válida (debe existir en la columna G de la hoja "General")
    categoria = args[2]
    try:
        # Obtener lista de categorías válidas
        categorias_validas = sheets_ops.get_column_values("General", "G")

        # Excluir el encabezado si existe
        if categorias_validas and categorias_validas[0].lower() == "categorías":
            categorias_validas = categorias_validas[1:]

        if categorias_validas and categoria not in categorias_validas:
            # Mostrar categorías disponibles
            categorias_texto = ", ".join(categorias_validas)
            await update.message.reply_text(f"⚠️ La categoría '{categoria}' no es válida.\n\nCategorías disponibles: {categorias_texto}")
            return
    except Exception as e:
        logger.warning(f"No se pudieron verificar las categorías válidas: {e}")
        # Continuamos sin validar la categoría si hay error

    # Procesar la fecha (opcional)
    fecha = datetime.datetime.now().strftime("%Y-%m-%d")
    if len(args) >= 4:
        try:
            fecha_input = args[3]
            datetime.datetime.strptime(fecha_input, "%Y-%m-%d")
            fecha = fecha_input
        except ValueError:
            await update.message.reply_text("⚠️ Formato de fecha incorrecto. Usa YYYY-MM-DD\nSe usará la fecha actual.")

    # Obtener la hoja de cálculo adecuada según el tipo de transacción
    sheet_name = "gastos" if tipo == "gasto" else "ingresos"

    # Insertar los datos en la hoja de cálculo
    try:
        # Preparar la fila para añadir
        row_data = [
            fecha,  # Fecha
            user.username or user.first_name,  # Usuario
            categoria,  # Categoría
            monto,  # Monto
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
        ]

        # Añadir la fila a la hoja correspondiente
        sheets_ops.append_row(sheet_name, row_data)

        # Enviar confirmación al usuario
        signo = "-" if tipo == "gasto" else "+"
        await update.message.reply_text(
            f"✅ {tipo.capitalize()} registrado correctamente:\nFecha: {fecha}\nCategoría: {categoria}\nMonto: {signo}{monto:.2f}\n"
        )

    except ValueError as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error al agregar transacción: {e}")
    except Exception as e:
        await update.message.reply_text("❌ Error al registrar la transacción")
        logger.exception(f"Error no controlado al agregar transacción: {e}")


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador global de errores.

    Args:
        update: Objeto Update de Telegram o None
        context: Contexto con información del error
    """
    logger.exception(f"Error: {context.error} - Update: {update}")

    if update and update.effective_message:
        await update.effective_message.reply_text("Ha ocurrido un error. Por favor, intenta nuevamente más tarde.")
