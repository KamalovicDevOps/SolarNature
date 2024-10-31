from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

# Conversation stages
LANGUAGE_SELECTION, CHOOSING, ENTERING_USAGE, FINAL_OPTIONS = range(4)

# Pricing Tiers for Individual Customers
INDIVIDUAL_TIERS = [
    (0, 200, 450),                                 # 0 - 200 kWh at 450 so'm
    (201, 1000, 900),                              # 201 - 1000 kWh at 900 so'm
    (1001, 5000, 1350),                            # 1001 - 5000 kWh at 1350 so'm
    (5001, 10000, 1575),                           # 5001 - 10000 kWh at 1575 so'm
    (10001, float('inf'), 1800),                   # Above 10000 kWh at 1800 so'm
]
LEGAL_RATE = 900

# SFES constants
SFES_ANNUAL_ENERGY = 1500    # 1 kW of SFES produces 1500 kWh per year
SFES_AREA_PER_KW = 10        # 1 kW of SFES requires 10 m² of space
SFES_COST_PER_KW = 6_000_000 # 1 kW of SFES costs 6,000,000 so'm

async def start(update: Update, context: CallbackContext) -> int:
    # Language selection buttons
    language_keyboard = [["🇷🇺 Русский язык", "🇺🇿 O'zbek tili"]]
    await update.message.reply_text(
        "Tilni tanlang. Выберите язык.",
        reply_markup=ReplyKeyboardMarkup(language_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANGUAGE_SELECTION

async def choose_language(update: Update, context: CallbackContext) -> int:
    selected_language = update.message.text
    if "Русский" in selected_language:
        context.user_data['language'] = 'ru'
    elif "O'zbek" in selected_language:
        context.user_data['language'] = 'uz'
    
    return await display_main_menu(update, context)

async def display_main_menu(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('language') == 'ru':
        reply_keyboard = [["🏠 Физическое лицо", "🏢 Юридическое лицо"]]
        message = "Выберите подходящий раздел."
    else:
        reply_keyboard = [["🏠 Jismoniy shaxs", "🏢 Yuridik shaxs"]]
        message = "Iltimos, o'zingizga mos keladigan bo'limni tanlang."

    await update.message.reply_text(
        message,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSING

async def handle_choice(update: Update, context: CallbackContext) -> int:
    context.user_data['choice'] = update.message.text
    if context.user_data.get('language') == 'ru':
        prompt = "Введите месячное потребление ✏️: (кВт)"
    else:
        prompt = "Bir oylik istemolingizni kiriting ✏️: (kWt)"
    
    await update.message.reply_text(prompt)
    return ENTERING_USAGE

def parse_usage(input_text):
    """Convert formatted numbers to a float"""
    return float(input_text.replace(",", "").replace(".", ""))

async def handle_usage(update: Update, context: CallbackContext) -> int:
    usage_text = update.message.text
    try:
        usage = parse_usage(usage_text)
    except ValueError:
        if context.user_data.get('language') == 'ru':
            error_message = "Неверные данные, попробуйте снова.🔄"
        else:
            error_message = "Xato ma'lumot kiritilgan, qaytadan urunib ko'ring.🔄"
        await update.message.reply_text(error_message)
        return ENTERING_USAGE

    # Convert monthly usage to yearly usage
    annual_usage = usage * 12

    choice = context.user_data['choice']
    if choice in ["🏠 Физическое лицо", "🏠 Jismoniy shaxs"]:
        cost = calculate_individual_cost(usage)
    else:
        cost = usage * LEGAL_RATE

    # SFES calculations
    sfes_power_needed = annual_usage / SFES_ANNUAL_ENERGY
    sfes_area_needed = sfes_power_needed * SFES_AREA_PER_KW
    sfes_total_cost = sfes_power_needed * SFES_COST_PER_KW

    if context.user_data.get('language') == 'ru':
        response = (
            f"{choice} Потребление электроэнергии за 1 месяц: *{cost:,.0f}* сум.\n"
            f"Необходимая мощность СФЭС: *{sfes_power_needed:.0f}* кВт\n"
            f"Требуемая площадь: *{sfes_area_needed:.0f}* м²\n"
            f"Примерные стоимость: *{sfes_total_cost:,.0f}* сум"
        )
        reply_keyboard = [["Пересчитать 🔄", "Я хочу купить 💰"]]
        prompt = "Выберите дальнейшее действие:"
    else:
        response = (
            f"{choice}ning 1 oylik elektor energiya istemoli: *{cost:,.0f}* so'm.\n"
            f"Sizga kerakli СФЭС quvvati: *{sfes_power_needed:.0f}* kWt\n"
            f"Kerakli yer maydoni: *{sfes_area_needed:.0f}* m²\n"
            f"Tahminiy narx: *{sfes_total_cost:,.0f}* so'm"
        )
        reply_keyboard = [["Qayta hisoblash 🔄", "Men sotib olmoqchiman 💰"]]
        prompt = "Davom etishni tanlang:"

    await update.message.reply_text(response, parse_mode="Markdown")
    await update.message.reply_text(
        prompt,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return FINAL_OPTIONS

def calculate_individual_cost(usage):
    total_cost = 0
    for lower_bound, upper_bound, rate in INDIVIDUAL_TIERS:
        if usage > upper_bound:
            total_cost += (upper_bound - lower_bound + 1) * rate
        else:
            total_cost += (usage - lower_bound + 1) * rate
            break
    return total_cost

async def final_options(update: Update, context: CallbackContext) -> int:
    if update.message.text in ["Пересчитать 🔄", "Qayta hisoblash 🔄"]:
        return await display_main_menu(update, context)
    elif update.message.text in ["Я хочу купить 💰", "Men sotib olmoqchiman 💰"]:
        if context.user_data.get('language') == 'ru':
            await update.message.reply_text("Зарегистрируйтесь по ссылке на Google Forms. Наши специалисты скоро с вами свяжутся 😊: [https://forms.gle/Tszp1DBT3vw4SB8A7]")
        else:
            await update.message.reply_text("Google Forms havolasi orqali ro'yxatdan o'ting. Mutahassislarimiz siz bilan yaqin orada bog'lanishadi 😊: [https://forms.gle/Tszp1DBT3vw4SB8A7]")
        return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('language') == 'ru':
        await update.message.reply_text("Процесс отменен.")
    else:
        await update.message.reply_text("Jarayon bekor qilindi.")
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token("5398155131:AAExWC7d0Mo57l9KLILk4xmOO0RHH15wVW0").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_language)],
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
            ENTERING_USAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_usage)],
            FINAL_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_options)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
