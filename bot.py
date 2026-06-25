import os
import logging
import json
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

# ── Config ─────────────────────────────────────────────────────────────────
BOT_TOKEN     = os.environ["BOT_TOKEN"]
SHEET_ID      = os.environ["SHEET_ID"]
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# ── Состояния ──────────────────────────────────────────────────────────────
LANG, Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9 = range(10)

# ── Тексты на двух языках ──────────────────────────────────────────────────
T = {
    "ru": {
        "lang_prompt": "👋 Привет! Выберите язык / Tilni tanlang:",
        "intro": (
            "👋 Привет! Меня зовут TIKUV — мы создаём платформу для швей.\n\n"
            "Уделите 3–4 минуты? Ваше мнение очень важно. Все ответы анонимны.\n\n"
            "─────────────────\n"
            "*Вопрос 1 из 9*\nКак давно вы занимаетесь шитьём?"
        ),
        "accepted": "✅ Принято!\n\n─────────────────\n",
        "q1_opts": [["Менее 1 года", "1–3 года"], ["3–7 лет", "Более 7 лет"]],
        "q2": (
            "*Вопрос 2 из 9*\nЧто вы шьёте чаще всего?\n\n"
            "_(Напишите номера через запятую, например: 1, 3)_\n\n"
            "1 — Женская одежда (платья, блузы)\n"
            "2 — Национальная одежда (чапан, атлас)\n"
            "3 — Свадебные и праздничные наряды\n"
            "4 — Детская одежда\n"
            "5 — Ремонт и подгонка одежды\n"
            "6 — Другое"
        ),
        "q2_choices": {
            "1": "Женская одежда", "2": "Национальная одежда",
            "3": "Свадебные наряды", "4": "Детская одежда",
            "5": "Ремонт и подгонка", "6": "Другое",
        },
        "q3": (
            "*Вопрос 3 из 9*\nКак вы сейчас находите клиентов?\n\n"
            "_(Можно несколько — напишите номера через запятую)_\n\n"
            "1 — Сарафанное радио\n"
            "2 — Instagram или TikTok\n"
            "3 — Telegram-группы\n"
            "4 — OLX или сайты объявлений\n"
            "5 — Постоянные клиенты\n"
            "6 — Другим способом"
        ),
        "q3_choices": {
            "1": "Сарафанное радио", "2": "Instagram / TikTok",
            "3": "Telegram-группы", "4": "OLX / объявления",
            "5": "Постоянные клиенты", "6": "Другое",
        },
        "q4": "*Вопрос 4 из 9*\nБывают ли периоды, когда заказов мало или совсем нет?",
        "q4_opts": [["Да, часто"], ["Иногда"], ["Редко"], ["Заказов всегда достаточно"]],
        "q5": (
            "*Вопрос 5 из 9*\nПредставьте: есть платформа, где клиенты оставляют заказы "
            "на пошив или ремонт, а вы откликаетесь и берёте понравившиеся. Оплата — онлайн, защищённая.\n\n"
            "*Насколько вам интересна такая платформа?*\nОцените от 1 до 5 👇"
        ),
        "q5_opts": [["1 — Совсем не интересно", "2"], ["3", "4"], ["5 — Очень интересно"]],
        "q5_err": "Пожалуйста, выберите оценку от 1 до 5 👆",
        "q6": (
            "*Вопрос 6 из 9*\nЧто для вас важнее всего в такой платформе?\n\n"
            "_(Выберите до 3 — напишите номера через запятую)_\n\n"
            "1 — Много заказов\n"
            "2 — Гарантия оплаты\n"
            "3 — Сам выбираю заказы\n"
            "4 — Рейтинг и отзывы\n"
            "5 — Простота использования\n"
            "6 — Удобная связь с клиентом"
        ),
        "q6_choices": {
            "1": "Много заказов", "2": "Гарантия оплаты",
            "3": "Сам выбираю", "4": "Рейтинг и отзывы",
            "5": "Простота", "6": "Удобная связь",
        },
        "q7": "*Вопрос 7 из 9*\nКак вам удобнее получать оплату от клиентов?",
        "q7_opts": [["UzCard или Humo"], ["Click или Payme"], ["Наличными"], ["Любым способом"]],
        "q8": (
            "*Вопрос 8 из 9*\nЧто могло бы остановить вас от использования платформы?\n\n"
            "_(Можно несколько — напишите номера через запятую)_\n\n"
            "1 — Боюсь, что клиенты не заплатят\n"
            "2 — Сложно разобраться с технологиями\n"
            "3 — Нет времени на регистрацию\n"
            "4 — Не понимаю, как это работает\n"
            "5 — Ничего, готова попробовать"
        ),
        "q8_choices": {
            "1": "Боюсь неоплаты", "2": "Сложные технологии",
            "3": "Нет времени", "4": "Не понимаю как",
            "5": "Готова попробовать",
        },
        "q9": (
            "*Вопрос 9 из 9* (последний!)\n"
            "Если хотите — напишите одно пожелание: что сделало бы платформу идеальной для вас?\n\n"
            "_(Или отправьте «—» чтобы пропустить)_"
        ),
        "q9_opts": [["—"]],
        "skip": "—",
        "thanks_ok": (
            "🧵 *Спасибо большое!*\n\nВаши ответы сохранены. "
            "Вы помогаете нам создать платформу, удобную именно для швей.\n\n"
            "Когда запустимся — сообщим первой! 🎉"
        ),
        "thanks_err": "✅ Спасибо за ответы!\n_(Технический сбой при сохранении)_",
        "cancel": "Хорошо, остановились. Напишите /start чтобы начать заново.",
        "unknown": "Напишите /start чтобы начать опрос 🧵",
        "lang_label": "🇷🇺 Русский",
    },
    "uz": {
        "lang_prompt": "👋 Salom! Tilni tanlang / Выберите язык:",
        "intro": (
            "👋 Salom! Men TIKUV — tikuvchilar uchun platforma yaratmoqdamiz.\n\n"
            "3–4 daqiqa ajrata olasizmi? Fikringiz juda muhim. Barcha javoblar anonim.\n\n"
            "─────────────────\n"
            "*1-savol 9 tadan*\nQachondan beri tikuvchilik qilasiz?"
        ),
        "accepted": "✅ Qabul qilindi!\n\n─────────────────\n",
        "q1_opts": [["1 yildan kam", "1–3 yil"], ["3–7 yil", "7 yildan ko'p"]],
        "q2": (
            "*2-savol 9 tadan*\nKo'pincha nima tikasiz?\n\n"
            "_(Raqamlarni vergul bilan yozing, masalan: 1, 3)_\n\n"
            "1 — Ayollar kiyimi (ko'ylak, bluzka)\n"
            "2 — Milliy kiyimlar (chopon, atlas)\n"
            "3 — To'y va bayram kiyimlari\n"
            "4 — Bolalar kiyimi\n"
            "5 — Kiyim ta'mirlash\n"
            "6 — Boshqa"
        ),
        "q2_choices": {
            "1": "Ayollar kiyimi", "2": "Milliy kiyimlar",
            "3": "To'y kiyimlari", "4": "Bolalar kiyimi",
            "5": "Ta'mirlash", "6": "Boshqa",
        },
        "q3": (
            "*3-savol 9 tadan*\nHozir mijozlarni qanday topasiz?\n\n"
            "_(Bir nechta bo'lishi mumkin — raqamlarni vergul bilan yozing)_\n\n"
            "1 — Do'stlar orqali\n"
            "2 — Instagram yoki TikTok\n"
            "3 — Telegram guruhlari\n"
            "4 — OLX yoki e'lon saytlari\n"
            "5 — Doimiy mijozlar\n"
            "6 — Boshqa yo'l"
        ),
        "q3_choices": {
            "1": "Do'stlar orqali", "2": "Instagram / TikTok",
            "3": "Telegram guruhlar", "4": "OLX / e'lonlar",
            "5": "Doimiy mijozlar", "6": "Boshqa",
        },
        "q4": "*4-savol 9 tadan*\nBazan buyurtmalar kam yoki umuman bo'lmagan paytlar bo'ladimi?",
        "q4_opts": [["Ha, tez-tez"], ["Ba'zan"], ["Kamdan-kam"], ["Buyurtmalar doim yetarli"]],
        "q5": (
            "*5-savol 9 tadan*\nTasavvur qiling: mijozlar tikish yoki ta'mirlashga buyurtma "
            "beradigan platforma bor, siz esa yoqqan buyurtmani olasiz. To'lov — onlayn, xavfsiz.\n\n"
            "*Bunday platforma sizga qanchalik qiziqarli?*\n1 dan 5 gacha baho bering 👇"
        ),
        "q5_opts": [["1 — Umuman qiziq emas", "2"], ["3", "4"], ["5 — Juda qiziqarli"]],
        "q5_err": "Iltimos, 1 dan 5 gacha baho bering 👆",
        "q6": (
            "*6-savol 9 tadan*\nBunday platformada siz uchun eng muhimi nima?\n\n"
            "_(3 tagacha tanlang — raqamlarni vergul bilan yozing)_\n\n"
            "1 — Ko'p buyurtmalar\n"
            "2 — To'lov kafolati\n"
            "3 — O'zim buyurtma tanlash\n"
            "4 — Reyting va sharhlar\n"
            "5 — Foydalanish qulayligi\n"
            "6 — Mijoz bilan qulay aloqa"
        ),
        "q6_choices": {
            "1": "Ko'p buyurtmalar", "2": "To'lov kafolati",
            "3": "O'zim tanlash", "4": "Reyting va sharhlar",
            "5": "Qulaylik", "6": "Qulay aloqa",
        },
        "q7": "*7-savol 9 tadan*\nTo'lovni qanday olish qulay?",
        "q7_opts": [["UzCard yoki Humo"], ["Click yoki Payme"], ["Naqd pul"], ["Istalgan usulda"]],
        "q8": (
            "*8-savol 9 tadan*\nPlatformadan foydalanishga nima to'sqinlik qilishi mumkin?\n\n"
            "_(Bir nechta bo'lishi mumkin — raqamlarni vergul bilan yozing)_\n\n"
            "1 — Mijoz to'lamasidan qo'rqaman\n"
            "2 — Texnologiyalarni tushunish qiyin\n"
            "3 — Ro'yxatdan o'tishga vaqt yo'q\n"
            "4 — Qanday ishlashini tushunmayman\n"
            "5 — Hech narsa, sinab ko'rishga tayyorman"
        ),
        "q8_choices": {
            "1": "To'lamaslikdan qo'rqaman", "2": "Texnologiya qiyin",
            "3": "Vaqt yo'q", "4": "Tushunmayapman",
            "5": "Sinab ko'rishga tayyorman",
        },
        "q9": (
            "*9-savol 9 tadan* (oxirgisi!)\n"
            "Xohlasangiz — platforma siz uchun ideal bo'lishi uchun bir tilagingizni yozing.\n\n"
            "_(Yoki o'tkazib yuborish uchun «—» yuboring)_"
        ),
        "q9_opts": [["—"]],
        "skip": "—",
        "thanks_ok": (
            "🧵 *Katta rahmat!*\n\nJavoblaringiz saqlandi. "
            "Siz tikuvchilar uchun qulay platforma yaratishimizga yordam beryapsiz.\n\n"
            "Ishga tushganimizda — birinchi bo'lib xabar beramiz! 🎉"
        ),
        "thanks_err": "✅ Javoblaringiz uchun rahmat!\n_(Saqlashda texnik xato yuz berdi)_",
        "cancel": "Yaxshi, to'xtatdik. Qaytadan boshlash uchun /start yozing.",
        "unknown": "So'rovnomani boshlash uchun /start yozing 🧵",
        "lang_label": "🇺🇿 O'zbek",
    }
}

# ── Google Sheets ──────────────────────────────────────────────────────────
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    if sheet.row_count == 0 or not sheet.row_values(1):
        headers = [
            "Дата", "User ID", "Язык",
            "1. Стаж", "2. Что шьёт", "3. Как ищет клиентов",
            "4. Нехватка заказов", "5. Интерес (1-5)",
            "6. Важно в платформе", "7. Способ оплаты",
            "8. Что остановит", "9. Пожелание"
        ]
        sheet.append_row(headers)
    return sheet


def save_to_sheet(user_id: int, lang: str, answers: dict):
    try:
        sheet = get_sheet()
        row = [
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            str(user_id),
            "Русский" if lang == "ru" else "O'zbek",
            answers.get(Q1, ""), answers.get(Q2, ""),
            answers.get(Q3, ""), answers.get(Q4, ""),
            answers.get(Q5, ""), answers.get(Q6, ""),
            answers.get(Q7, ""), answers.get(Q8, ""),
            answers.get(Q9, ""),
        ]
        sheet.append_row(row)
        logger.info(f"Saved answers for user {user_id} ({lang})")
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
    nums = [x.strip() for x in text.replace(",", " ").split() if x.strip()]
    nums = nums[:max_sel]
    selected = [choices[n] for n in nums if n in choices]
    return ", ".join(selected) if selected else text


def lang(ctx) -> str:
    return ctx.user_data.get("lang", "ru")


def t(ctx, key: str) -> str:
    return T[lang(ctx)][key]

# ── Handlers ──────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Привет! Выберите язык / Tilni tanlang:",
        reply_markup=make_keyboard([["🇷🇺 Русский", "🇺🇿 O'zbek"]])
    )
    return LANG


async def handle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if "O'zbek" in text or "Uzbek" in text or "uz" in text.lower():
        context.user_data["lang"] = "uz"
    else:
        context.user_data["lang"] = "ru"

    await update.message.reply_text(
        t(context, "intro"),
        parse_mode="Markdown",
        reply_markup=make_keyboard(t(context, "q1_opts"))
    )
    return Q1


async def handle_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q1] = update.message.text
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q2"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return Q2


async def handle_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q2] = parse_multi(update.message.text, t(context, "q2_choices"))
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q3"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return Q3


async def handle_q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q3] = parse_multi(update.message.text, t(context, "q3_choices"))
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q4"),
        parse_mode="Markdown",
        reply_markup=make_keyboard(t(context, "q4_opts"))
    )
    return Q4


async def handle_q4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q4] = update.message.text
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q5"),
        parse_mode="Markdown",
        reply_markup=make_keyboard(t(context, "q5_opts"))
    )
    return Q5


async def handle_q5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    digit = text[0] if text else ""
    if digit not in "12345":
        await update.message.reply_text(
            t(context, "q5_err"),
            reply_markup=make_keyboard(t(context, "q5_opts"))
        )
        return Q5
    context.user_data[Q5] = digit
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q6"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return Q6


async def handle_q6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q6] = parse_multi(update.message.text, t(context, "q6_choices"), max_sel=3)
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q7"),
        parse_mode="Markdown",
        reply_markup=make_keyboard(t(context, "q7_opts"))
    )
    return Q7


async def handle_q7(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q7] = update.message.text
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q8"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return Q8


async def handle_q8(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Q8] = parse_multi(update.message.text, t(context, "q8_choices"))
    await update.message.reply_text(
        t(context, "accepted") + t(context, "q9"),
        parse_mode="Markdown",
        reply_markup=make_keyboard(t(context, "q9_opts"))
    )
    return Q9


async def handle_q9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data[Q9] = "" if text == "—" else text

    user_id = update.effective_user.id
    current_lang = lang(context)
    ok = save_to_sheet(user_id, current_lang, context.user_data)

    await update.message.reply_text(
        t(context, "thanks_ok") if ok else t(context, "thanks_err"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    if ADMIN_CHAT_ID:
        try:
            flag = "🇷🇺" if current_lang == "ru" else "🇺🇿"
            summary = (
                f"📋 *Новый опрос завершён* {flag}\n"
                f"👤 User: `{user_id}`\n"
                f"⏱ {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"1️⃣ {context.user_data.get(Q1, '—')}\n"
                f"2️⃣ {context.user_data.get(Q2, '—')}\n"
                f"3️⃣ {context.user_data.get(Q3, '—')}\n"
                f"4️⃣ {context.user_data.get(Q4, '—')}\n"
                f"5️⃣ {context.user_data.get(Q5, '—')}\n"
                f"6️⃣ {context.user_data.get(Q6, '—')}\n"
                f"7️⃣ {context.user_data.get(Q7, '—')}\n"
                f"8️⃣ {context.user_data.get(Q8, '—')}\n"
                f"9️⃣ {context.user_data.get(Q9, '—')}"
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
        t(context, "cancel"),
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(context, "unknown"))

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lang)],
            Q1:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q1)],
            Q2:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q2)],
            Q3:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q3)],
            Q4:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q4)],
            Q5:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q5)],
            Q6:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q6)],
            Q7:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q7)],
            Q8:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q8)],
            Q9:   [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_q9)],
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
