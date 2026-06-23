import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Config (из переменных окружения) ──────────────────────────────────────
BOT_TOKEN       = os.environ["BOT_TOKEN"]           # токен от @BotFather
SHEET_ID        = os.environ["SHEET_ID"]            # ID Google Таблицы
ADMIN_CHAT_ID   = os.environ.get("ADMIN_CHAT_ID")   # ваш Telegram ID (опционально)
CREDENTIALS_FILE = "credentials.json"               # ключ сервисного аккаунта

# ── Состояния диалога ─────────────────────────────────────────────────────
(
    Q1, Q2, Q3, Q4,        # О работе
    Q5, Q6, Q7,            # О платформе
    Q8, Q9                 # Пожелания
) = range(9)

# ── Вопросы и варианты ответов ────────────────────────────────────────────
QUESTIONS = {
    Q1: {
        "text": "👋 Привет! Меня зовут TIKUV — мы создаём платформу для швей.\n\nУделите 3–4 минуты? Ваше мнение очень важно. Все ответы анонимны.\n\n─────────────────\n*Вопрос 1 из 9*\nКак давно вы занимаетесь шитьём?",
        "options": [["Менее 1 года", "1–3 года"], ["3–7 лет", "Более 7 лет"]],
        "multi": False,
    },
    Q2: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 2 из 9*\nЧто вы шьёте чаще всего?\n\n_(Напишите номера через запятую, например: 1, 3)_\n\n1 — Женская одежда (платья, блузы)\n2 — Национальная одежда (чапан, атлас)\n3 — Свадебные и праздничные наряды\n4 — Детская одежда\n5 — Ремонт и подгонка одежды\n6 — Другое",
        "options": None,
        "multi": True,
        "choices": {
            "1": "Женская одежда",
            "2": "Национальная одежда",
            "3": "Свадебные наряды",
            "4": "Детская одежда",
            "5": "Ремонт и подгонка",
            "6": "Другое",
        }
    },
    Q3: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 3 из 9*\nКак вы сейчас находите клиентов?\n\n_(Можно несколько — напишите номера через запятую)_\n\n1 — Сарафанное радио\n2 — Instagram или TikTok\n3 — Telegram-группы\n4 — OLX или сайты объявлений\n5 — Постоянные клиенты\n6 — Другим способом",
        "options": None,
        "multi": True,
        "choices": {
            "1": "Сарафанное радио",
            "2": "Instagram / TikTok",
            "3": "Telegram-группы",
            "4": "OLX / объявления",
            "5": "Постоянные клиенты",
            "6": "Другое",
        }
    },
    Q4: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 4 из 9*\nБывают ли периоды, когда заказов мало или совсем нет?",
        "options": [
            ["Да, часто"],
            ["Иногда"],
            ["Редко"],
            ["Заказов всегда достаточно"],
        ],
        "multi": False,
    },
    Q5: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 5 из 9*\nПредставьте: есть платформа, где клиенты оставляют заказы на пошив или ремонт, а вы откликаетесь и берёте понравившиеся. Оплата — онлайн, защищённая.\n\n*Насколько вам интересна такая платформа?*\nОцените от 1 до 5 👇",
        "options": [["1 — Совсем не интересно", "2"], ["3", "4"], ["5 — Очень интересно"]],
        "multi": False,
    },
    Q6: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 6 из 9*\nЧто для вас важнее всего в такой платформе?\n\n_(Выберите до 3 — напишите номера через запятую)_\n\n1 — Много заказов\n2 — Гарантия оплаты\n3 — Сам выбираю заказы\n4 — Рейтинг и отзывы\n5 — Простота использования\n6 — Удобная связь с клиентом",
        "options": None,
        "multi": True,
        "max": 3,
        "choices": {
            "1": "Много заказов",
            "2": "Гарантия оплаты",
            "3": "Сам выбираю заказы",
            "4": "Рейтинг и отзывы",
            "5": "Простота",
            "6": "Удобная связь",
        }
    },
    Q7: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 7 из 9*\nКак вам удобнее получать оплату от клиентов?",
        "options": [
            ["UzCard или Humo"],
            ["Click или Payme"],
            ["Наличными"],
            ["Любым способом"],
        ],
        "multi": False,
    },
    Q8: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 8 из 9*\nЧто могло бы остановить вас от использования платформы?\n\n_(Можно несколько — напишите номера через запятую)_\n\n1 — Боюсь, что клиенты не заплатят\n2 — Сложно разобраться с технологиями\n3 — Нет времени на регистрацию\n4 — Не понимаю, как это работает\n5 — Ничего, готова попробовать",
        "options": None,
        "multi": True,
        "choices": {
            "1": "Боюсь неоплаты",
            "2": "Сложные технологии",
            "3": "Нет времени",
            "4": "Не понимаю как",
            "5": "Готова попробовать",
        }
    },
    Q9: {
        "text": "✅ Принято!\n\n─────────────────\n*Вопрос 9 из 9* (последний!)\nЕсли хотите — напишите одно пожелание: что сделало бы платформу идеальной для вас?\n\n_(Или отправьте «—» чтобы пропустить)_",
        "options": [["—"]],
        "multi": False,
    },
}

# ── Google Sheets ──────────────────────────────────────────────────────────
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    # Добавить заголовки если таблица пустая
    if sheet.row_count == 0 or not sheet.row_values(1):
        headers = [
            "Дата", "User ID",
            "1. Стаж", "2. Что шьёт", "3. Как ищет клиентов",
            "4. Нехватка заказов", "5. Интерес к платформе (1-5)",
            "6. Важно в платформе", "7. Способ оплаты",
            "8. Что остановит", "9. Пожелание"
        ]
        sheet.append_row(headers)
    return sheet


def save_to_sheet(user_id: int, answers: dict):
    try:
        sheet = get_sheet()
        row = [
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            str(user_id),
            answers.get(Q1, ""),
            answers.get(Q2, ""),
            answers.get(Q3, ""),
            answers.get(Q4, ""),
            answers.get(Q5, ""),
            answers.get(Q6, ""),
            answers.get(Q7, ""),
            answers.get(Q8, ""),
            answers.get(Q9, ""),
        ]
        sheet.append_row(row)
        logger.info(f"Saved answers for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        return False

# ── Helpers ───────────────────────────────────────────────────────────────
def make_keyboard(options):
    if options is None:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(options, resize_keyboard=True, one_time_keyboard=True)


def parse_multi(text: str, choices: dict, max_sel: int = 99) -> str:
    """Парсит '1, 3, 5' → 'Женская одежда, Ремонт и подгонка, Другое'"""
    nums = [x.strip() for x in text.replace(",", " ").split() if x.strip()]
    nums = nums[:max_sel]
    selected = [choices[n] for n in nums if n in choices]
    return ", ".join(selected) if selected else text


def progress(step: int) -> str:
    filled = "█" * step
    empty  = "░" * (9 - step)
    return f"{filled}{empty} {step}/9"

# ── Handlers ──────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    q = QUESTIONS[Q1]
    await update.message.reply_text(
        q["text"],
        parse_mode="Markdown",
        reply_markup=make_keyboard(q["options"])
    )
    return Q1


async def handle_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q1] = update.message.text
    q = QUESTIONS[Q2]
    await update.message.reply_text(q["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(q["options"]))
    return Q2


async def handle_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = QUESTIONS[Q2]
    context.user_data[Q2] = parse_multi(update.message.text, q["choices"])
    nq = QUESTIONS[Q3]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q3


async def handle_q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = QUESTIONS[Q3]
    context.user_data[Q3] = parse_multi(update.message.text, q["choices"])
    nq = QUESTIONS[Q4]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q4


async def handle_q4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q4] = update.message.text
    nq = QUESTIONS[Q5]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q5


async def handle_q5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Принимаем только цифру 1-5
    text = update.message.text.strip()
    digit = text[0] if text else ""
    if digit not in "12345":
        await update.message.reply_text("Пожалуйста, выберите оценку от 1 до 5 👆",
                                        reply_markup=make_keyboard(QUESTIONS[Q5]["options"]))
        return Q5
    context.user_data[Q5] = digit
    nq = QUESTIONS[Q6]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q6


async def handle_q6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = QUESTIONS[Q6]
    context.user_data[Q6] = parse_multi(update.message.text, q["choices"], max_sel=3)
    nq = QUESTIONS[Q7]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q7


async def handle_q7(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q7] = update.message.text
    nq = QUESTIONS[Q8]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q8


async def handle_q8(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = QUESTIONS[Q8]
    context.user_data[Q8] = parse_multi(update.message.text, q["choices"])
    nq = QUESTIONS[Q9]
    await update.message.reply_text(nq["text"], parse_mode="Markdown",
                                    reply_markup=make_keyboard(nq["options"]))
    return Q9


async def handle_q9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data[Q9] = "" if text == "—" else text

    # Сохраняем в Google Sheets
    user_id = update.effective_user.id
    ok = save_to_sheet(user_id, context.user_data)

    if ok:
        await update.message.reply_text(
            "🧵 *Спасибо большое!*\n\nВаши ответы сохранены. Вы помогаете нам создать платформу, удобную именно для швей.\n\nКогда запустимся — сообщим первой! 🎉",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "✅ Спасибо за ответы!\n_(Технический сбой при сохранении — но мы всё зафиксировали)_",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

    # Уведомление администратору
    if ADMIN_CHAT_ID:
        try:
            summary = (
                f"📋 *Новый опрос завершён*\n"
                f"👤 User: `{user_id}`\n"
                f"⏱ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"1️⃣ Стаж: {context.user_data.get(Q1, '—')}\n"
                f"2️⃣ Что шьёт: {context.user_data.get(Q2, '—')}\n"
                f"3️⃣ Ищет клиентов: {context.user_data.get(Q3, '—')}\n"
                f"4️⃣ Нехватка заказов: {context.user_data.get(Q4, '—')}\n"
                f"5️⃣ Интерес (1-5): {context.user_data.get(Q5, '—')}\n"
                f"6️⃣ Важно: {context.user_data.get(Q6, '—')}\n"
                f"7️⃣ Оплата: {context.user_data.get(Q7, '—')}\n"
                f"8️⃣ Опасения: {context.user_data.get(Q8, '—')}\n"
                f"9️⃣ Пожелание: {context.user_data.get(Q9, '—')}"
            )
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=summary,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Хорошо, остановились. Напишите /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишите /start чтобы начать опрос 🧵"
    )

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q1)],
            Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q2)],
            Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q3)],
            Q4: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q4)],
            Q5: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q5)],
            Q6: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q6)],
            Q7: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q7)],
            Q8: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q8)],
            Q9: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q9)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("🧵 TIKUV bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
