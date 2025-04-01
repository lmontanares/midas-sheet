"""
Manejadores de mensajes y comandos para el bot de Telegram.
"""

import datetime
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from src.sheets.operations import SheetsOperations

# Categorías de gastos hardcoded en formato JSON
EXPENSE_CATEGORIES = {
    "HOME": [
        "Mortgage / Rent",
        "Electricity",
        "Gas / Oil",
        "Water / Sewer / Trash",
        "Phone",
        "Cable / Satellite",
        "Internet",
        "Furnishing / Appliances",
        "Lawn / Garden",
        "Maintenance / Improvements",
        "Other"
    ],
    "TRANSPORTATION": [
        "Uber",
        "Car Payments",
        "Auto Insurance",
        "Fuel",
        "Public Transporation",
        "Repairs / Maintenance",
        "Registration / License"
    ],
    "DAILY LIVING": [
        "Groceries",
        "Dining Out",
        "Clothing",
        "Cleaning",
        "Salon / Barber",
        "Pet Supplies"
    ],
    "ENTERTAINMENT": [
        "XXXX",
        "Concerts / Plays",
        "Sports",
        "Outdoor Recreation"
    ],
    "HEALTH": [
        "Health Insurance",
        "XXXX",
        "Doctors / Dentist Visits",
        "Medicine / Prescriptions",
        "Veterinarian",
        "Life Insurance"
    ],
    "VACATION / HOLIDAY": [
        "Airfare",
        "Accommodations",
        "Food",
        "Souvenirs",
        "Pet Boarding",
        "Rental Car"
    ]
}

# Categorías de ingresos (sin subcategorías)
INCOME_CATEGORIES = [
    "Salary / Wages",
    "Interest Income",
    "Dividends",
    "Refunds / Reimbursements",
    "Business",
    "Pension",
    "Misc."
]


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
        for category in EXPENSE_CATEGORIES.keys():
            # Formato del callback data: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    else:
        # Para ingresos, mostrar las categorías como categorías principales
        for category in INCOME_CATEGORIES:
            # Formato del callback data: "category|expense_type|category_name"
            callback_data = f"category|{expense_type}|{category}"
            buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    
    # Añadir botones para seleccionar tipo (gasto/ingreso)
    type_buttons = [
        InlineKeyboardButton("GASTOS", callback_data="selector|gasto"),
        InlineKeyboardButton("INGRESOS", callback_data="selector|ingreso")
    ]
    
    # Añadir los botones de tipo al principio
    buttons.insert(0, type_buttons)
    
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
    subcategories = EXPENSE_CATEGORIES.get(main_category, [])
    
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

    Pronto se agregarán más funciones...
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para el comando /agregar.
    Muestra botones con categorías para seleccionar.
    
    Args:
        update: Objeto Update de Telegram
        context: Contexto del manejador
    """
    user = update.effective_user
    
    try:
        # Crear y mostrar el teclado con las categorías
        keyboard = get_category_keyboard()
        await update.message.reply_text(
            "Selecciona una categoría para registrar un gasto:", 
            reply_markup=keyboard
        )
    
    except Exception as e:
        logger.error(f"Error al cargar las categorías: {e}")
        await update.message.reply_text("❌ Error al cargar las categorías")


async def register_transaction(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    expense_type: str,
    amount: float,
    category: str,
    subcategory: str,
    date: str
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
            date,                                  # Fecha 
            user.username or user.first_name,      # Usuario
            category,                              # Categoría principal
            subcategory,                           # Subcategoría
            amount,                                # Monto
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Timestamp
        ]
        
        # Añadir la fila a la hoja correspondiente
        sheets_ops.append_row(sheet_name, row_data)
        
        # Enviar confirmación al usuario
        sign = "-" if expense_type == "gasto" else "+"
        
        # Para ingresos, donde la categoría y subcategoría son iguales, solo mostrar una vez
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"
        
        await update.effective_message.reply_text(
            f"✅ {expense_type.capitalize()} registrado correctamente:\n"
            f"Fecha: {date}\n"
            f"Categoría: {category_display}\n"
            f"Monto: {sign}{amount:.2f}\n"
        )
        
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
            # Verificar si ya estamos mostrando este tipo
            current_message = query.message.text
            if f"registrar un {expense_type}" in current_message.lower():
                # Si es el mismo tipo, solo responder sin modificar el mensaje
                await query.answer(f"Ya estás en modo {expense_type}")
                return
                
            # Actualizar el mensaje con el nuevo teclado
            keyboard = get_category_keyboard(expense_type)
            await query.edit_message_text(
                f"Selecciona una categoría para registrar un {expense_type}:", 
                reply_markup=keyboard
            )
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
                    f"Has seleccionado *{category}* como {expense_type}.\n"
                    f"Ahora selecciona una subcategoría:",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
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
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            
            await query.edit_message_text(
                f"Has seleccionado *{category}* como {expense_type}.\n"
                f"Por favor, envía el monto (solo números, ej: 123.45):",
                parse_mode="Markdown"
            )
        
        return
    
    # Si es volver a categorías
    elif action == "back":
        expense_type = data[1]
        
        try:
            # Mostrar categorías principales nuevamente
            keyboard = get_category_keyboard(expense_type)
            await query.edit_message_text(
                f"Selecciona una categoría para registrar un {expense_type}:", 
                reply_markup=keyboard
            )
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
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        
        # Para ingresos, donde la categoría y subcategoría son iguales, ajustar el mensaje
        category_display = f"{category}" if category == subcategory else f"{category} - {subcategory}"
        
        await query.edit_message_text(
            f"Has seleccionado *{category_display}* como {expense_type}.\n"
            f"Por favor, envía el monto (solo números, ej: 123.45):",
            parse_mode="Markdown"
        )
        
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
    # Verificar si hay una transacción pendiente
    if "pending_transaction" not in context.user_data:
        await update.message.reply_text("❌ No hay ninguna transacción en proceso. Usa /agregar para comenzar.")
        return
    
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
    
    # Obtener datos de la transacción pendiente
    transaction = context.user_data["pending_transaction"]
    expense_type = transaction["expense_type"]
    category = transaction["category"]
    subcategory = transaction["subcategory"]
    date = transaction["date"]
    
    # Registrar la transacción
    await register_transaction(update, context, expense_type, amount, category, subcategory, date)
    
    # Limpiar datos temporales
    del context.user_data["pending_transaction"]


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
