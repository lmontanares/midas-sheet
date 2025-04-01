"""
Manejadores de mensajes y comandos para el bot de Telegram.
"""

import datetime

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.config.categories import category_manager
from src.sheets.operations import SheetsOperations


def get_category_keyboard(expense_type: str = "gasto") -> InlineKeyboardMarkup:
    """
    Crea un teclado de botones con las categorías según el tipo de transacción.

    Args:
        expense_type: Tipo de transacción (gasto o ingreso)

    Returns:
        Teclado de botones para Telegram
    """
    # Crear lista de botones
    buttons = []

    # Diferentes categorías según el tipo (gasto o ingreso)
    if expense_type == "gasto":
        # Para gastos, mostrar categorías principales
        for category in category_manager.get_expense_category_names():
            # Formato del callback data: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    else:
        # Para ingresos, mostrar las categorías como categorías principales
        for category in category_manager.income_categories:
            # Formato del callback data: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])

    # Añadir botón para volver al selector de tipo
    back_button = [InlineKeyboardButton("⬅️ Cambiar tipo", callback_data="back_to_selector")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


def get_subcategory_keyboard(main_category: str, expense_type: str) -> InlineKeyboardMarkup:
    """
    Crea un teclado de botones con las subcategorías de una categoría principal.

    Args:
        main_category: Nombre de la categoría principal seleccionada
        expense_type: Tipo de transacción (gasto o ingreso)

    Returns:
        Teclado de botones para Telegram
    """
    # Obtener subcategorías de la categoría principal
    subcategories = category_manager.get_subcategories(main_category)

    # Crear lista de botones para subcategorías
    buttons = []
    for subcat in subcategories:
        if subcat.strip():  # Asegurarse de que no esté vacía
            # Formato del callback data: "subcategory|expense_type|category|subcategory"
            callback_data = f"subcategory|{expense_type}|{main_category}|{subcat}"
            buttons.append([InlineKeyboardButton(subcat, callback_data=callback_data)])

    # Añadir botón para volver a categorías principales
    back_button = [InlineKeyboardButton("⬅️ Volver a Categorías", callback_data=f"back|{expense_type}")]
    buttons.append(back_button)

    return InlineKeyboardMarkup(buttons)


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
    /agregar - Muestra las categorías disponibles como botones para registrar una transacción
    /recargar - Recarga las categorías desde el archivo de configuración

    Pronto se agregarán más funciones...
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


def get_type_selector_keyboard() -> InlineKeyboardMarkup:
    """
    Crea un teclado simple para seleccionar el tipo de transacción (gasto o ingreso).

    Returns:
        Teclado de botones para Telegram
    """
    buttons = [[InlineKeyboardButton("GASTOS", callback_data="selector|gasto"), InlineKeyboardButton("INGRESOS", callback_data="selector|ingreso")]]
    return InlineKeyboardMarkup(buttons)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /agregar.
    Muestra botones para elegir entre gasto o ingreso.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    user = update.effective_user

    try:
        # Mostrar primero un selector entre gasto e ingreso
        keyboard = get_type_selector_keyboard()
        await update.message.reply_text("¿Qué tipo de transacción deseas registrar?", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error al mostrar el selector de tipo: {e}")
        await update.message.reply_text("❌ Error al iniciar el proceso de registro")


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /recargar.
    Recarga las categorías desde el archivo de configuración.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    user = update.effective_user

    try:
        # Recargar las categorías
        category_manager.reload_categories()

        # Obtener estadísticas para el mensaje de confirmación
        num_expense_cats = len(category_manager.get_expense_category_names())
        num_income_cats = len(category_manager.income_categories)
        num_total_subcats = sum(len(subcats) for subcats in category_manager.expense_categories.values())

        # Enviar confirmación al usuario
        message = f"✅ Categorías recargadas correctamente:\n"
        message += f"- Categorías de gastos: *{num_expense_cats}*\n"
        message += f"- Subcategorías totales: *{num_total_subcats}*\n"
        message += f"- Categorías de ingresos: *{num_income_cats}*"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Categorías recargadas por {user.username or user.first_name}")

    except Exception as e:
        logger.error(f"Error al recargar categorías: {e}")
        await update.message.reply_text(f"❌ Error al recargar las categorías: {str(e)}")


async def register_transaction(
    update: Update, context: ContextTypes.DEFAULT_TYPE, expense_type: str, amount: float, category: str, subcategory: str, date: str, comment: str
) -> None:
    """
    Registra una transacción en la hoja de cálculo.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
        expense_type: Tipo de transacción (gasto o ingreso)
        amount: Monto de la transacción
        category: Categoría principal de la transacción
        subcategory: Subcategoría de la transacción
        date: Fecha de la transacción en formato YYYY-MM-DD
    """
    user = update.effective_user
    sheets_ops: SheetsOperations = context.bot_data.get("sheets_operations")

    # Obtener la hoja de cálculo adecuada según el tipo de transacción
    sheet_name = "gastos" if expense_type == "gasto" else "ingresos"

    try:
        # Preparar la fila para añadir
        row_data = [
            date,  # Fecha
            user.username or user.first_name,  # Usuario
            category,  # Categoría principal
            subcategory,  # Subcategoría
            amount,  # Monto
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
            comment,  # Comentario
        ]

        # Añadir la fila a la hoja correspondiente
        sheets_ops.append_row(sheet_name, row_data)

        # Enviar confirmación al usuario
        sign = "-" if expense_type == "gasto" else "+"

        # Para ingresos, donde la categoría y subcategoría son iguales, solo mostrar una vez
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"

        # Crear mensaje de confirmación
        confirm_message = (
            f"✅ {expense_type.capitalize()} registrado correctamente:\nFecha: {date}\nCategoría: {category_display}\nMonto: {sign}{amount:.2f}"
        )

        # Añadir comentario al mensaje si existe
        if comment:
            confirm_message += f"\nComentario: {comment}"

        await update.effective_message.reply_text(confirm_message)

    except ValueError as e:
        await update.effective_message.reply_text(f"❌ Error: {str(e)}")
        logger.error(f"Error al agregar transacción: {e}")
    except Exception as e:
        await update.effective_message.reply_text("❌ Error al registrar la transacción")
        logger.exception(f"Error no controlado al agregar transacción: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja las interacciones con los botones.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    query = update.callback_query
    await query.answer()

    # Obtener los datos del callback
    data = query.data.split("|")
    action = data[0]

    # Si es un selector de tipo (gasto/ingreso)
    if action == "selector":
        expense_type = data[1]

        try:
            # Actualizar el mensaje con el nuevo teclado de categorías según el tipo seleccionado
            keyboard = get_category_keyboard(expense_type)
            await query.edit_message_text(f"Selecciona una categoría para registrar un {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            error_str = str(e)
            if "message is not modified" in error_str.lower():
                # Este error ocurre cuando tratamos de editar un mensaje con contenido idéntico
                # Solo lo registramos sin mostrar error al usuario
                logger.warning(f"Intento de editar mensaje con contenido idéntico: {error_str}")
            else:
                logger.error(f"Error al obtener categorías para botones: {e}")
                await query.edit_message_text("❌ Error al cargar las categorías")

        return

    # Si es una selección de categoría principal, mostrar subcategorías o solicitar monto
    elif action == "category":
        expense_type = data[1]
        category = data[2]

        # Comportamiento diferente para gastos e ingresos
        if expense_type == "gasto":
            try:
                # Crear teclado con subcategorías
                keyboard = get_subcategory_keyboard(category, expense_type)
                await query.edit_message_text(
                    f"Has seleccionado *{category}* como {expense_type}.\nAhora selecciona una subcategoría:",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Error al obtener subcategorías: {e}")
                await query.edit_message_text("❌ Error al cargar las subcategorías")
        else:
            # Para ingresos, no hay subcategorías, pasar directamente a solicitar monto
            # Guardar datos en user_data para el siguiente paso
            context.user_data["pending_transaction"] = {
                "expense_type": expense_type,
                "category": category,
                "subcategory": category,  # Para ingresos, la categoría y subcategoría son la misma
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "amount": None,  # Se llenará en el siguiente paso
                "comment": "",  # Se llenará en el paso final
            }
            # Establecer el estado como "waiting_amount"
            context.user_data["state"] = "waiting_amount"

            await query.edit_message_text(
                f"Has seleccionado *{category}* como {expense_type}.\nPor favor, envía el monto (solo números, ej: 123.45):", parse_mode="Markdown"
            )

        return

    # Si es volver a categorías
    elif action == "back":
        expense_type = data[1]

        try:
            # Mostrar categorías principales nuevamente
            keyboard = get_category_keyboard(expense_type)
            await query.edit_message_text(f"Selecciona una categoría para registrar un {expense_type}:", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error al volver a categorías: {e}")
            await query.edit_message_text("❌ Error al cargar las categorías")

        return

    # Si es una selección de subcategoría, solicitar el monto
    elif action == "subcategory":
        expense_type = data[1]
        category = data[2]
        subcategory = data[3]

        # Guardar datos en user_data para el siguiente paso
        context.user_data["pending_transaction"] = {
            "expense_type": expense_type,
            "category": category,
            "subcategory": subcategory,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "amount": None,  # Se llenará en el siguiente paso
            "comment": "",  # Se llenará en el paso final
        }
        # Establecer el estado como "waiting_amount"
        context.user_data["state"] = "waiting_amount"

        # Para ingresos, donde la categoría y subcategoría son iguales, ajustar el mensaje
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"

        await query.edit_message_text(
            f"Has seleccionado *{category_display}* como {expense_type}.\nPor favor, envía el monto (solo números, ej: 123.45):",
            parse_mode="Markdown",
        )

        return

    # Si es volver al selector de tipo
    elif action == "back_to_selector":
        try:
            # Mostrar selector de tipo nuevamente
            keyboard = get_type_selector_keyboard()
            await query.edit_message_text("¿Qué tipo de transacción deseas registrar?", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error al volver al selector de tipo: {e}")
            await query.edit_message_text("❌ Error al cargar el selector de tipo")

        return

    # Si es una respuesta a la pregunta sobre agregar comentario
    elif action == "comment":
        option = data[1]  # "yes" o "no"
        
        # Verificamos que exista una transacción pendiente
        if "pending_transaction" not in context.user_data:
            logger.warning(f"Se intentó agregar comentario pero no hay transacción pendiente. User: {update.effective_user.id}")
            await query.edit_message_text(
                "❌ Error: La transacción ha expirado. Por favor, usa /agregar para iniciar una nueva transacción."
            )
            return
        
        # Agregamos logging para depuración
        logger.info(f"Manejo de botón de comentario. Opción: {option}. User: {update.effective_user.id}")
        if option == "yes":            
            # El usuario quiere agregar un comentario
            context.user_data["state"] = "waiting_comment"
            # Extraer datos de la transacción para el mensaje
            transaction = context.user_data["pending_transaction"]
            expense_type = transaction["expense_type"]
            category = transaction["category"]
            amount = transaction["amount"]

            # Mostrar categoría (con subcategoría si es un gasto)
            if expense_type == "ingreso":
                category_display = category
            else:
                subcategory = transaction["subcategory"]
                category_display = f"{category} - {subcategory}"

            await query.edit_message_text(
                f"*{category_display}* - *{amount:.2f}*\n\nPor favor, escribe el comentario para esta transacción:", parse_mode="Markdown"
            )
        else:  # option == "no"
            # El usuario no quiere agregar comentario, registrar la transacción sin comentario
            transaction = context.user_data["pending_transaction"]
            expense_type = transaction["expense_type"]
            category = transaction["category"]
            subcategory = transaction["subcategory"]
            date = transaction["date"]
            amount = transaction["amount"]

            # Registrar la transacción sin comentario (cadena vacía)
            await register_transaction(update, context, expense_type, amount, category, subcategory, date, "")

            # Limpiar datos temporales
            del context.user_data["pending_transaction"]
            if "state" in context.user_data:
                del context.user_data["state"]

        return

    # Si llega aquí, es un comando desconocido
    await query.edit_message_text("❌ Acción no reconocida. Usa /agregar para comenzar nuevamente.")


async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja la entrada del monto después de seleccionar una categoría.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    # Verificar si hay una transacción pendiente y estamos esperando un monto
    if "pending_transaction" not in context.user_data or context.user_data.get("state") != "waiting_amount":
        # Si no estamos esperando un monto, ignoramos este mensaje (lo manejará otro handler)
        return

    # Logging para depuración
    logger.info(f"Procesando monto para transacción. User: {update.effective_user.id}")
    
    try:
        amount_text = update.message.text.strip()
        
        # Validar que sea un número
        try:
            amount = float(amount_text)
            if amount <= 0:
                await update.message.reply_text("⚠️ El monto debe ser un número positivo. Intenta de nuevo:")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Por favor, ingresa solo números (ej: 123.45). Intenta de nuevo:")
            return

        # Guardar el monto en la transacción pendiente
        context.user_data["pending_transaction"]["amount"] = amount
        
        # Cambiar el estado a "confirm_comment"
        context.user_data["state"] = "confirm_comment"
        
        # Preparar la información de la transacción para mostrar
        transaction = context.user_data["pending_transaction"]
        expense_type = transaction["expense_type"]
        category = transaction["category"]
        
        # Para ingresos, donde la categoría y subcategoría son iguales, ajustar el mensaje
        if expense_type == "ingreso":
            category_display = category
        else:
            subcategory = transaction["subcategory"]
            category_display = f"{category} - {subcategory}"
        
        # Crear botones para confirmar si desea agregar un comentario
        keyboard = [
            [InlineKeyboardButton("✅ Sí", callback_data="comment|yes"),
             InlineKeyboardButton("❌ No", callback_data="comment|no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Has seleccionado *{category_display}* como {expense_type} con monto *{amount:.2f}*.\n\n"
            f"¿Deseas agregar un comentario a esta transacción?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        # Si ocurre cualquier error, informar al usuario y registrar en el log
        logger.error(f"Error al procesar monto: {e}")
        await update.message.reply_text("❌ Error al procesar la transacción. Por favor, intenta nuevamente con /agregar.")


async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja la entrada del comentario y finaliza el registro de la transacción.

    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    # Verificar si hay una transacción pendiente y estamos esperando un comentario
    if "pending_transaction" not in context.user_data or context.user_data.get("state") != "waiting_comment":
        # Si no estamos esperando un comentario, ignoramos este mensaje (lo manejará otro handler)
        return
    
    # Agregamos logging para depuración
    logger.info(f"Procesando comentario para transacción. User: {update.effective_user.id}")
    
    try:
        # Obtener el comentario ingresado
        comment_text = update.message.text.strip()
        
        # Si el usuario escribe "sin comentario", guardar como cadena vacía
        if comment_text.lower() == "sin comentario":
            comment_text = ""
        
        # Obtener datos completos de la transacción pendiente
        transaction = context.user_data["pending_transaction"]
        expense_type = transaction["expense_type"]
        category = transaction["category"]
        subcategory = transaction["subcategory"]
        date = transaction["date"]
        amount = transaction["amount"]
        
        # Registrar la transacción con el comentario
        await register_transaction(update, context, expense_type, amount, category, subcategory, date, comment_text)
        
        # Limpiar datos temporales
        del context.user_data["pending_transaction"]
        if "state" in context.user_data:
            del context.user_data["state"]
    
    except Exception as e:
        # Si ocurre cualquier error, informar al usuario y registrar en el log
        logger.error(f"Error al procesar comentario: {e}")
        await update.message.reply_text("❌ Error al procesar la transacción. Por favor, intenta nuevamente con /agregar.")


async def register_bot_commands(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra los comandos del bot en Telegram.
    Este manejador se ejecuta al inicio del bot.

    Args:
        context: Contexto del manejador
    """
    from .commands import get_commands

    try:
        # Establecer los comandos en el menú del bot
        await context.bot.set_my_commands(get_commands())
        logger.info("Comandos del bot registrados correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comandos del bot: {e}")


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
