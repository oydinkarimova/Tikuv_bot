import os, logging, json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN     = os.environ["BOT_TOKEN"]
SHEET_ID      = os.environ["SHEET_ID"]
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# ── Состояния ──────────────────────────────────────────────────────────────
(
    LANG, ROLE,
    S1, S2, S3, S4, S5, S6, S7, S8, S9,          # Швея (Seamstress)
    C1, C2, C3, C4, C5, C6, C7, C8, C9,          # Клиент (Customer)
) = range(21)

# ══════════════════════════════════════════════════════════════════════════════
# ТЕКСТЫ
# ══════════════════════════════════════════════════════════════════════════════
T = {

# ─────────────────────────────── РУССКИЙ ─────────────────────────────────────
"ru": {
  "flag": "🇷🇺", "sheet_lang": "Русский",
  "role_prompt": "Кто вы?",
  "role_opts": [["🧵 Я швея / мастер", "🛍 Я заказчик"]],
  "role_seamstress": "🧵",
  "role_customer":   "🛍",

  # ── ШВЕЯ ──
  "s_intro": (
    "Отлично! Вы выбрали роль *швеи / мастера*.\n\n"
    "Мы создаём TIKUV — платформу, где клиенты находят швей онлайн. "
    "Уделите 3–4 минуты? Все ответы анонимны.\n\n"
    "─────────────────\n*Вопрос 1 из 9*\nКак давно вы занимаетесь шитьём?"
  ),
  "s_ok": "✅ Принято!\n\n─────────────────\n",
  "s1_opts": [["Менее 1 года","1–3 года"],["3–7 лет","Более 7 лет"]],
  "s2": (
    "*Вопрос 2 из 9*\nЧто вы шьёте чаще всего?\n"
    "_(Номера через запятую, напр.: 1, 3)_\n\n"
    "1 — Женская одежда\n2 — Национальная одежда\n3 — Свадебные наряды\n"
    "4 — Детская одежда\n5 — Ремонт и подгонка\n6 — Другое"
  ),
  "s2_ch": {"1":"Женская одежда","2":"Национальная одежда","3":"Свадебные наряды","4":"Детская одежда","5":"Ремонт/подгонка","6":"Другое"},
  "s3": (
    "*Вопрос 3 из 9*\nСколько заказов в среднем вы выполняете в месяц?"
  ),
  "s3_opts": [["1–5 заказов","6–15 заказов"],["16–30 заказов","Более 30"]],
  "s4": "*Вопрос 4 из 9*\nКак вы сейчас находите клиентов?\n_(Номера через запятую)_\n\n1 — Сарафанное радио\n2 — Instagram / TikTok\n3 — Telegram-группы\n4 — OLX / объявления\n5 — Постоянные клиенты\n6 — Другое",
  "s4_ch": {"1":"Сарафанное радио","2":"Instagram/TikTok","3":"Telegram","4":"OLX/объявления","5":"Постоянные клиенты","6":"Другое"},
  "s5": "*Вопрос 5 из 9*\nБывают ли периоды, когда заказов мало или нет?",
  "s5_opts": [["Да, часто"],["Иногда"],["Редко"],["Заказов всегда хватает"]],
  "s6": "*Вопрос 6 из 9*\nКакой ваш примерный доход от шитья в месяц (в долларах)?",
  "s6_opts": [["До $100","$100–250"],["$250–500","$500–1000"],["Более $1000"]],
  "s7": (
    "*Вопрос 7 из 9*\nЕсть платформа: клиенты оставляют заказы онлайн, вы выбираете подходящие, "
    "оплата защищена эскроу.\n\n*Насколько вам интересна такая платформа?*\nОцените 1–5 👇"
  ),
  "s7_opts": [["1 — Совсем не интересно","2"],["3","4"],["5 — Очень интересно"]],
  "s7_err": "Пожалуйста, выберите от 1 до 5 👆",
  "s8": "*Вопрос 8 из 9*\nЧто важнее всего для вас в такой платформе?\n_(До 3 вариантов — номера через запятую)_\n\n1 — Много заказов\n2 — Гарантия оплаты\n3 — Я сам выбираю заказы\n4 — Рейтинг и отзывы\n5 — Удобный интерфейс\n6 — Связь с клиентом",
  "s8_ch": {"1":"Много заказов","2":"Гарантия оплаты","3":"Сам выбираю","4":"Рейтинг/отзывы","5":"Удобство","6":"Связь с клиентом"},
  "s9": "*Вопрос 9 из 9*\nЧто могло бы остановить вас от использования платформы?\n_(Номера через запятую)_\n\n1 — Боюсь, что клиент не заплатит\n2 — Сложные технологии\n3 — Нет времени на регистрацию\n4 — Не понимаю как работает\n5 — Ничего — готова попробовать",
  "s9_ch": {"1":"Страх неоплаты","2":"Сложные технологии","3":"Нет времени","4":"Не понимаю","5":"Готова попробовать"},
  "s_thanks_ok": "🧵 *Спасибо большое!*\n\nВаши ответы сохранены и помогут нам создать удобную платформу для швей.\n\nКогда запустимся — вы узнаете первой! 🎉",
  "s_thanks_err": "✅ Спасибо! _(Ошибка при сохранении)_",

  # ── КЛИЕНТ ──
  "c_intro": (
    "Отлично! Вы выбрали роль *заказчика*.\n\n"
    "Мы создаём TIKUV — платформу, где легко найти швею онлайн. "
    "Уделите 3–4 минуты? Все ответы анонимны.\n\n"
    "─────────────────\n*Вопрос 1 из 9*\nКак часто вы заказываете пошив или ремонт одежды?"
  ),
  "c_ok": "✅ Принято!\n\n─────────────────\n",
  "c1_opts": [["Несколько раз в год","Раз в месяц"],["Раз в неделю","Никогда не заказывал(а)"]],
  "c2": "*Вопрос 2 из 9*\nЧто вы чаще всего заказываете?\n_(Номера через запятую)_\n\n1 — Пошив платья / костюма\n2 — Национальная одежда\n3 — Свадебный наряд\n4 — Ремонт и подгонка\n5 — Детская одежда\n6 — Другое",
  "c2_ch": {"1":"Пошив платья/костюма","2":"Национальная одежда","3":"Свадебный наряд","4":"Ремонт/подгонка","5":"Детская одежда","6":"Другое"},
  "c3": "*Вопрос 3 из 9*\nКак вы обычно ищете швею?",
  "c3_opts": [["Через знакомых"],["Instagram / TikTok"],["Telegram-группы"],["OLX / объявления"],["Затрудняюсь найти"]],
  "c4": "*Вопрос 4 из 9*\nСколько времени обычно уходит на поиск подходящей швеи?",
  "c4_opts": [["Несколько часов"],["1–3 дня"],["Неделя и больше"],["Не могу найти вообще"]],
  "c5": "*Вопрос 5 из 9*\nСколько вы обычно тратите на один заказ пошива или ремонта?",
  "c5_opts": [["До $10","$10–30"],["$30–80","$80–200"],["Более $200"]],
  "c6": "*Вопрос 6 из 9*\nС какими проблемами вы сталкивались при заказе пошива?\n_(Номера через запятую)_\n\n1 — Трудно найти мастера\n2 — Не уверен(а) в качестве\n3 — Нарушение сроков\n4 — Споры по оплате\n5 — Результат не совпал с ожиданиями\n6 — Проблем не было",
  "c6_ch": {"1":"Трудно найти","2":"Неуверенность в качестве","3":"Нарушение сроков","4":"Споры по оплате","5":"Не соответствует ожиданиям","6":"Проблем не было"},
  "c7": "*Вопрос 7 из 9*\nЕсть платформа: вы оставляете заказ онлайн, швеи откликаются, вы выбираете по рейтингу. Оплата защищена.\n\n*Насколько вам интересна такая платформа?*\nОцените 1–5 👇",
  "c7_opts": [["1 — Совсем не интересно","2"],["3","4"],["5 — Очень интересно"]],
  "c7_err": "Пожалуйста, выберите от 1 до 5 👆",
  "c8": "*Вопрос 8 из 9*\nЧто важнее всего для вас в такой платформе?\n_(До 3 вариантов — номера через запятую)_\n\n1 — Быстро найти мастера\n2 — Гарантия качества\n3 — Защищённая оплата\n4 — Отзывы и рейтинг швей\n5 — Удобное общение\n6 — Разумные цены",
  "c8_ch": {"1":"Быстрый поиск","2":"Гарантия качества","3":"Защита оплаты","4":"Отзывы/рейтинг","5":"Удобное общение","6":"Разумные цены"},
  "c9": "*Вопрос 9 из 9*\nЧто могло бы остановить вас от использования платформы?\n_(Номера через запятую)_\n\n1 — Не доверяю онлайн-оплате\n2 — Не уверен(а) в качестве мастеров\n3 — Предпочитаю искать через знакомых\n4 — Ничего — готов(а) попробовать",
  "c9_ch": {"1":"Не доверяю оплате","2":"Сомневаюсь в качестве","3":"Предпочитаю знакомых","4":"Готов попробовать"},
  "c_thanks_ok": "🛍 *Спасибо большое!*\n\nВаши ответы сохранены и помогут нам создать сервис, удобный для заказчиков.\n\nКогда запустимся — вы узнаете первым! 🎉",
  "c_thanks_err": "✅ Спасибо! _(Ошибка при сохранении)_",

  "cancel": "Остановились. Напишите /start чтобы начать заново.",
  "unknown": "Напишите /start чтобы начать опрос 🧵",
},

# ─────────────────────────────── O'ZBEK (LOTIN) ───────────────────────────────
"uz": {
  "flag": "🇺🇿", "sheet_lang": "O'zbek (lotin)",
  "role_prompt": "Siz kimsiz?",
  "role_opts": [["🧵 Men tikuvchiman","🛍 Men buyurtmachiman"]],
  "role_seamstress": "🧵",
  "role_customer":   "🛍",

  "s_intro": (
    "Ajoyib! Siz *tikuvchi / usta* rolingizni tanladingiz.\n\n"
    "Biz TIKUV — tikuvchilar uchun onlayn platforma yaratmoqdamiz. "
    "3–4 daqiqa ajrata olasizmi? Barcha javoblar anonim.\n\n"
    "─────────────────\n*1-savol 9 tadan*\nQachondan beri tikuvchilik qilasiz?"
  ),
  "s_ok": "✅ Qabul qilindi!\n\n─────────────────\n",
  "s1_opts": [["1 yildan kam","1–3 yil"],["3–7 yil","7 yildan ko'p"]],
  "s2": "*2-savol 9 tadan*\nKo'pincha nima tikasiz?\n_(Raqamlarni vergul bilan, mas.: 1, 3)_\n\n1 — Ayollar kiyimi\n2 — Milliy kiyimlar\n3 — To'y kiyimlari\n4 — Bolalar kiyimi\n5 — Ta'mirlash\n6 — Boshqa",
  "s2_ch": {"1":"Ayollar kiyimi","2":"Milliy kiyimlar","3":"To'y kiyimlari","4":"Bolalar kiyimi","5":"Ta'mirlash","6":"Boshqa"},
  "s3": "*3-savol 9 tadan*\nOyiga o'rtacha nechta buyurtma bajarasiz?",
  "s3_opts": [["1–5","6–15"],["16–30","30 dan ko'p"]],
  "s4": "*4-savol 9 tadan*\nHozir mijozlarni qanday topasiz?\n_(Raqamlarni vergul bilan)_\n\n1 — Do'stlar orqali\n2 — Instagram / TikTok\n3 — Telegram guruhlari\n4 — OLX / e'lonlar\n5 — Doimiy mijozlar\n6 — Boshqa",
  "s4_ch": {"1":"Do'stlar orqali","2":"Instagram/TikTok","3":"Telegram","4":"OLX/e'lonlar","5":"Doimiy mijozlar","6":"Boshqa"},
  "s5": "*5-savol 9 tadan*\nBazan buyurtmalar kam yoki yo'q paytlar bo'ladimi?",
  "s5_opts": [["Ha, tez-tez"],["Ba'zan"],["Kamdan-kam"],["Doim yetarli"]],
  "s6": "*6-savol 9 tadan*\nTikuvchilikdan oylik daromadingiz taxminan qancha (dollarda)?",
  "s6_opts": [["$100 gacha","$100–250"],["$250–500","$500–1000"],["$1000 dan ko'p"]],
  "s7": "*7-savol 9 tadan*\nMijozlar onlayn buyurtma beradi, siz mosini tanlab olasiz, to'lov xavfsiz.\n\n*Bunday platforma sizga qanchalik qiziqarli?*\n1 dan 5 gacha 👇",
  "s7_opts": [["1 — Umuman qiziq emas","2"],["3","4"],["5 — Juda qiziqarli"]],
  "s7_err": "Iltimos, 1 dan 5 gacha baho bering 👆",
  "s8": "*8-savol 9 tadan*\nPlatformada siz uchun eng muhimi nima?\n_(3 tagacha — raqamlarni vergul bilan)_\n\n1 — Ko'p buyurtmalar\n2 — To'lov kafolati\n3 — O'zim tanlash\n4 — Reyting va sharhlar\n5 — Qulay interfeys\n6 — Mijoz bilan aloqa",
  "s8_ch": {"1":"Ko'p buyurtmalar","2":"To'lov kafolati","3":"O'zim tanlash","4":"Reyting/sharhlar","5":"Qulaylik","6":"Mijoz bilan aloqa"},
  "s9": "*9-savol 9 tadan*\nPlatformadan foydalanishga nima to'sqinlik qilishi mumkin?\n_(Raqamlarni vergul bilan)_\n\n1 — Mijoz to'lamasidan qo'rqaman\n2 — Texnologiya murakkab\n3 — Ro'yxatdan o'tishga vaqt yo'q\n4 — Tushunmayapman\n5 — Hech narsa — tayyorman",
  "s9_ch": {"1":"To'lamaslikdan qo'rqaman","2":"Texnologiya murakkab","3":"Vaqt yo'q","4":"Tushunmayapman","5":"Tayyorman"},
  "s_thanks_ok": "🧵 *Katta rahmat!*\n\nJavoblaringiz saqlandi va tikuvchilar uchun qulay platforma yaratishimizga yordam beradi.\n\nIshga tushganimizda birinchi bo'lib xabar beramiz! 🎉",
  "s_thanks_err": "✅ Rahmat! _(Saqlashda xato)_",

  "c_intro": (
    "Ajoyib! Siz *buyurtmachi* rolingizni tanladingiz.\n\n"
    "Biz TIKUV — onlayn tikuvchi topish platformasini yaratmoqdamiz. "
    "3–4 daqiqa ajrata olasizmi? Barcha javoblar anonim.\n\n"
    "─────────────────\n*1-savol 9 tadan*\nQanchalik tez-tez kiyim tikish yoki ta'mirlashga buyurtma berasiz?"
  ),
  "c_ok": "✅ Qabul qilindi!\n\n─────────────────\n",
  "c1_opts": [["Yiliga bir necha marta","Oyda bir marta"],["Haftada bir marta","Hech buyurtma bermaganman"]],
  "c2": "*2-savol 9 tadan*\nKo'pincha nima buyurtma berasiz?\n_(Raqamlarni vergul bilan)_\n\n1 — Ko'ylak/kostyum tikish\n2 — Milliy kiyim\n3 — To'y kiyimi\n4 — Ta'mirlash\n5 — Bolalar kiyimi\n6 — Boshqa",
  "c2_ch": {"1":"Ko'ylak/kostyum","2":"Milliy kiyim","3":"To'y kiyimi","4":"Ta'mirlash","5":"Bolalar kiyimi","6":"Boshqa"},
  "c3": "*3-savol 9 tadan*\nOdatda tikuvchini qanday qidirasiz?",
  "c3_opts": [["Tanishlar orqali"],["Instagram / TikTok"],["Telegram guruhlari"],["OLX / e'lonlar"],["Topa olmayman"]],
  "c4": "*4-savol 9 tadan*\nMos tikuvchini topish qancha vaqt oladi?",
  "c4_opts": [["Bir necha soat"],["1–3 kun"],["Bir hafta va ko'proq"],["Umuman topa olmayman"]],
  "c5": "*5-savol 9 tadan*\nBitta buyurtmaga odatda qancha sarflaysiz?",
  "c5_opts": [["$10 gacha","$10–30"],["$30–80","$80–200"],["$200 dan ko'p"]],
  "c6": "*6-savol 9 tadan*\nKiyim buyurtma berishda qanday muammolarga duch kelgansiz?\n_(Raqamlarni vergul bilan)_\n\n1 — Usta topish qiyin\n2 — Sifatiga ishonmayman\n3 — Muddatni buzish\n4 — To'lov bo'yicha nizolar\n5 — Natija kutgandan farqli\n6 — Muammo bo'lmagan",
  "c6_ch": {"1":"Usta topish qiyin","2":"Sifatga ishonmaslik","3":"Muddatni buzish","4":"To'lov nizolari","5":"Kutilmagan natija","6":"Muammo yo'q"},
  "c7": "*7-savol 9 tadan*\nSiz onlayn buyurtma berasiz, tikuvchilar javob beradi, siz reytingga qarab tanlaysiz. To'lov xavfsiz.\n\n*Bunday platforma sizga qanchalik qiziqarli?*\n1 dan 5 gacha 👇",
  "c7_opts": [["1 — Umuman qiziq emas","2"],["3","4"],["5 — Juda qiziqarli"]],
  "c7_err": "Iltimos, 1 dan 5 gacha baho bering 👆",
  "c8": "*8-savol 9 tadan*\nPlatformada siz uchun eng muhimi nima?\n_(3 tagacha — raqamlarni vergul bilan)_\n\n1 — Tezda usta topish\n2 — Sifat kafolati\n3 — To'lov himoyasi\n4 — Sharhlar va reyting\n5 — Qulay muloqot\n6 — Qulay narxlar",
  "c8_ch": {"1":"Tezda topish","2":"Sifat kafolati","3":"To'lov himoyasi","4":"Sharhlar/reyting","5":"Qulay muloqot","6":"Qulay narxlar"},
  "c9": "*9-savol 9 tadan*\nPlatformadan foydalanishga nima to'sqinlik qilishi mumkin?\n_(Raqamlarni vergul bilan)_\n\n1 — Onlayn to'lovga ishonmayman\n2 — Ustalar sifatiga shubha\n3 — Tanishlar orqali topishni afzal ko'raman\n4 — Hech narsa — tayyorman",
  "c9_ch": {"1":"Onlayn to'lovga ishonmayman","2":"Sifatga shubha","3":"Tanishlarni afzal ko'raman","4":"Tayyorman"},
  "c_thanks_ok": "🛍 *Katta rahmat!*\n\nJavoblaringiz saqlandi va buyurtmachilar uchun qulay xizmat yaratishimizga yordam beradi.\n\nIshga tushganimizda birinchi bo'lib xabar beramiz! 🎉",
  "c_thanks_err": "✅ Rahmat! _(Saqlashda xato)_",

  "cancel": "To'xtatdik. Qaytadan boshlash uchun /start yozing.",
  "unknown": "So'rovnomani boshlash uchun /start yozing 🧵",
},

# ─────────────────────────────── ЎЗБЕК (КИРИЛЛ) ──────────────────────────────
"uz_cyr": {
  "flag": "🇺🇿", "sheet_lang": "O'zbek (kirill)",
  "role_prompt": "Сиз кимсиз?",
  "role_opts": [["🧵 Мен тикувчиман","🛍 Мен буюртмачиман"]],
  "role_seamstress": "🧵",
  "role_customer":   "🛍",

  "s_intro": (
    "Ажойиб! Сиз *тикувчи / уста* ролини танладингиз.\n\n"
    "Биз TIKUV — тикувчилар учун онлайн платформа яратмоқдамиз. "
    "3–4 дақиқа ажрата оласизми? Барча жавоблар аноним.\n\n"
    "─────────────────\n*1-савол 9 тадан*\nҚачондан бери тикувчилик қиласиз?"
  ),
  "s_ok": "✅ Қабул қилинди!\n\n─────────────────\n",
  "s1_opts": [["1 йилдан кам","1–3 йил"],["3–7 йил","7 йилдан кўп"]],
  "s2": "*2-савол 9 тадан*\nКўпинча нима тикасиз?\n_(Рақамларни вергул билан)_\n\n1 — Аёллар кийими\n2 — Миллий кийимлар\n3 — Тўй кийимлари\n4 — Болалар кийими\n5 — Таъмирлаш\n6 — Бошқа",
  "s2_ch": {"1":"Аёллар кийими","2":"Миллий кийимлар","3":"Тўй кийимлари","4":"Болалар кийими","5":"Таъмирлаш","6":"Бошқа"},
  "s3": "*3-савол 9 тадан*\nОйига ўртача нечта буюртма бажарасиз?",
  "s3_opts": [["1–5","6–15"],["16–30","30 дан кўп"]],
  "s4": "*4-савол 9 тадан*\nҲозир мижозларни қандай топасиз?\n_(Рақамларни вергул билан)_\n\n1 — Дўстлар орқали\n2 — Instagram / TikTok\n3 — Telegram гуруҳлари\n4 — OLX / эълонлар\n5 — Доимий мижозлар\n6 — Бошқа",
  "s4_ch": {"1":"Дўстлар орқали","2":"Instagram/TikTok","3":"Telegram","4":"OLX/эълонлар","5":"Доимий мижозлар","6":"Бошқа"},
  "s5": "*5-савол 9 тадан*\nБаъзан буюртмалар кам ёки йўқ пайтлар бўладими?",
  "s5_opts": [["Ҳа, тез-тез"],["Баъзан"],["Камдан-кам"],["Доим етарли"]],
  "s6": "*6-савол 9 тадан*\nТикувчиликдан ойлик даромадингиз тахминан қанча (долларда)?",
  "s6_opts": [["$100 гача","$100–250"],["$250–500","$500–1000"],["$1000 дан кўп"]],
  "s7": "*7-савол 9 тадан*\nМижозлар онлайн буюртма беради, сиз мосини танлаб оласиз, тўлов хавфсиз.\n\n*Бундай платформа сизга қанчалик қизиқарли?*\n1 дан 5 гача 👇",
  "s7_opts": [["1 — Умуман қизиқ эмас","2"],["3","4"],["5 — Жуда қизиқарли"]],
  "s7_err": "Илтимос, 1 дан 5 гача баҳо беринг 👆",
  "s8": "*8-савол 9 тадан*\nПлатформада сиз учун энг муҳими нима?\n_(3 тагача — рақамларни вергул билан)_\n\n1 — Кўп буюртмалар\n2 — Тўлов кафолати\n3 — Ўзим танлаш\n4 — Рейтинг ва шарҳлар\n5 — Қулай интерфейс\n6 — Мижоз билан алоқа",
  "s8_ch": {"1":"Кўп буюртмалар","2":"Тўлов кафолати","3":"Ўзим танлаш","4":"Рейтинг/шарҳлар","5":"Қулайлик","6":"Мижоз билан алоқа"},
  "s9": "*9-савол 9 тадан*\nПлатформадан фойдаланишга нима тўсқинлик қилиши мумкин?\n_(Рақамларни вергул билан)_\n\n1 — Мижоз тўламаслигидан қўрқаман\n2 — Технология мураккаб\n3 — Рўйхатдан ўтишга вақт йўқ\n4 — Тушунмаяпман\n5 — Ҳеч нарса — тайёрман",
  "s9_ch": {"1":"Тўламасликдан қўрқаман","2":"Технология мураккаб","3":"Вақт йўқ","4":"Тушунмаяпман","5":"Тайёрман"},
  "s_thanks_ok": "🧵 *Катта раҳмат!*\n\nЖавобларингиз сақланди ва тикувчилар учун қулай платформа яратишимизга ёрдам беради.\n\nИшга тушганимизда биринчи бўлиб хабар берамиз! 🎉",
  "s_thanks_err": "✅ Раҳмат! _(Сақлашда хато)_",

  "c_intro": (
    "Ажойиб! Сиз *буюртмачи* ролини танладингиз.\n\n"
    "Биз TIKUV — онлайн тикувчи топиш платформасини яратмоқдамиз. "
    "3–4 дақиқа ажрата оласизми? Барча жавоблар аноним.\n\n"
    "─────────────────\n*1-савол 9 тадан*\nКийим тикиш ёки таъмирлашга қанчалик тез-тез буюртма берасиз?"
  ),
  "c_ok": "✅ Қабул қилинди!\n\n─────────────────\n",
  "c1_opts": [["Йилига бир неча марта","Ойда бир марта"],["Ҳафтада бир марта","Ҳеч буюртма бермаганман"]],
  "c2": "*2-савол 9 тадан*\nКўпинча нима буюртма берасиз?\n_(Рақамларни вергул билан)_\n\n1 — Кўйлак/костюм\n2 — Миллий кийим\n3 — Тўй кийими\n4 — Таъмирлаш\n5 — Болалар кийими\n6 — Бошқа",
  "c2_ch": {"1":"Кўйлак/костюм","2":"Миллий кийим","3":"Тўй кийими","4":"Таъмирлаш","5":"Болалар кийими","6":"Бошқа"},
  "c3": "*3-савол 9 тадан*\nОдатда тикувчини қандай қидирасиз?",
  "c3_opts": [["Танишлар орқали"],["Instagram / TikTok"],["Telegram гуруҳлари"],["OLX / эълонлар"],["Топа олмайман"]],
  "c4": "*4-савол 9 тадан*\nМос тикувчини топиш қанча вақт олади?",
  "c4_opts": [["Бир неча соат"],["1–3 кун"],["Бир ҳафта ва кўпроқ"],["Умуман топа олмайман"]],
  "c5": "*5-савол 9 тадан*\nБитта буюртмага одатда қанча сарфлайсиз?",
  "c5_opts": [["$10 гача","$10–30"],["$30–80","$80–200"],["$200 дан кўп"]],
  "c6": "*6-савол 9 тадан*\nКийим буюртма беришда қандай муаммоларга дуч келгансиз?\n_(Рақамларни вергул билан)_\n\n1 — Уста топиш қийин\n2 — Сифатига ишонмайман\n3 — Муддатни бузиш\n4 — Тўлов бўйича низолар\n5 — Натижа кутгандан фарқли\n6 — Муаммо бўлмаган",
  "c6_ch": {"1":"Уста топиш қийин","2":"Сифатга ишонмаслик","3":"Муддатни бузиш","4":"Тўлов низолари","5":"Кутилмаган натижа","6":"Муаммо йўқ"},
  "c7": "*7-савол 9 тадан*\nСиз онлайн буюртма берасиз, тикувчилар жавоб беради, рейтингга қараб танлайсиз. Тўлов хавфсиз.\n\n*Бундай платформа сизга қанчалик қизиқарли?*\n1 дан 5 гача 👇",
  "c7_opts": [["1 — Умуман қизиқ эмас","2"],["3","4"],["5 — Жуда қизиқарли"]],
  "c7_err": "Илтимос, 1 дан 5 гача баҳо беринг 👆",
  "c8": "*8-савол 9 тадан*\nПлатформада сиз учун энг муҳими нима?\n_(3 тагача — рақамларни вергул билан)_\n\n1 — Тезда уста топиш\n2 — Сифат кафолати\n3 — Тўлов ҳимояси\n4 — Шарҳлар ва рейтинг\n5 — Қулай мулоқот\n6 — Қулай нархлар",
  "c8_ch": {"1":"Тезда топиш","2":"Сифат кафолати","3":"Тўлов ҳимояси","4":"Шарҳлар/рейтинг","5":"Қулай мулоқот","6":"Қулай нархлар"},
  "c9": "*9-савол 9 тадан*\nПлатформадан фойдаланишга нима тўсқинлик қилиши мумкин?\n_(Рақамларни вергул билан)_\n\n1 — Онлайн тўловга ишонмайман\n2 — Усталар сифатига шубҳа\n3 — Танишлар орқали топишни афзал кўраман\n4 — Ҳеч нарса — тайёрман",
  "c9_ch": {"1":"Онлайн тўловга ишонмайман","2":"Сифатга шубҳа","3":"Танишларни афзал кўраман","4":"Тайёрман"},
  "c_thanks_ok": "🛍 *Катта раҳмат!*\n\nЖавобларингиз сақланди ва буюртмачилар учун қулай хизмат яратишимизга ёрдам беради.\n\nИшга тушганимизда биринчи бўлиб хабар берамиз! 🎉",
  "c_thanks_err": "✅ Раҳмат! _(Сақлашда хато)_",

  "cancel": "Тўхтатдик. Қайтадан бошлаш учун /start ёзинг.",
  "unknown": "Сўровномани бошлаш учун /start ёзинг 🧵",
},

# ─────────────────────────────── ENGLISH ─────────────────────────────────────
"en": {
  "flag": "🇬🇧", "sheet_lang": "English",
  "role_prompt": "Who are you?",
  "role_opts": [["🧵 I'm a seamstress / tailor","🛍 I'm a customer"]],
  "role_seamstress": "🧵",
  "role_customer":   "🛍",

  "s_intro": (
    "Great! You selected the *seamstress / tailor* role.\n\n"
    "We're building TIKUV — a platform where clients find seamstresses online. "
    "Could you spare 3–4 minutes? All answers are anonymous.\n\n"
    "─────────────────\n*Question 1 of 9*\nHow long have you been sewing?"
  ),
  "s_ok": "✅ Got it!\n\n─────────────────\n",
  "s1_opts": [["Less than 1 year","1–3 years"],["3–7 years","More than 7 years"]],
  "s2": "*Question 2 of 9*\nWhat do you sew most often?\n_(Enter numbers separated by commas, e.g.: 1, 3)_\n\n1 — Women's clothing\n2 — National clothing\n3 — Wedding outfits\n4 — Children's clothing\n5 — Repairs & alterations\n6 — Other",
  "s2_ch": {"1":"Women's clothing","2":"National clothing","3":"Wedding outfits","4":"Children's clothing","5":"Repairs","6":"Other"},
  "s3": "*Question 3 of 9*\nHow many orders do you complete per month on average?",
  "s3_opts": [["1–5","6–15"],["16–30","More than 30"]],
  "s4": "*Question 4 of 9*\nHow do you currently find clients?\n_(Numbers separated by commas)_\n\n1 — Word of mouth\n2 — Instagram / TikTok\n3 — Telegram groups\n4 — OLX / classifieds\n5 — Regular clients\n6 — Other",
  "s4_ch": {"1":"Word of mouth","2":"Instagram/TikTok","3":"Telegram","4":"OLX/classifieds","5":"Regular clients","6":"Other"},
  "s5": "*Question 5 of 9*\nDo you have periods when orders are scarce or absent?",
  "s5_opts": [["Yes, often"],["Sometimes"],["Rarely"],["Always have enough"]],
  "s6": "*Question 6 of 9*\nWhat is your approximate monthly income from sewing (in USD)?",
  "s6_opts": [["Under $100","$100–250"],["$250–500","$500–1000"],["Over $1000"]],
  "s7": "*Question 7 of 9*\nImagine: clients post orders online, you pick the ones you like, payment is protected by escrow.\n\n*How interested are you in such a platform?*\nRate 1–5 👇",
  "s7_opts": [["1 — Not interested at all","2"],["3","4"],["5 — Very interested"]],
  "s7_err": "Please rate from 1 to 5 👆",
  "s8": "*Question 8 of 9*\nWhat matters most to you in such a platform?\n_(Up to 3 — numbers separated by commas)_\n\n1 — Lots of orders\n2 — Payment guarantee\n3 — I choose my orders\n4 — Ratings & reviews\n5 — Easy interface\n6 — Chat with clients",
  "s8_ch": {"1":"Lots of orders","2":"Payment guarantee","3":"Choose own orders","4":"Ratings/reviews","5":"Easy interface","6":"Chat with clients"},
  "s9": "*Question 9 of 9*\nWhat could stop you from using the platform?\n_(Numbers separated by commas)_\n\n1 — Worried clients won't pay\n2 — Technology is complicated\n3 — No time to register\n4 — Don't understand how it works\n5 — Nothing — ready to try",
  "s9_ch": {"1":"Worried about non-payment","2":"Tech complicated","3":"No time","4":"Don't understand","5":"Ready to try"},
  "s_thanks_ok": "🧵 *Thank you so much!*\n\nYour answers are saved and will help us build the perfect platform for seamstresses.\n\nWe'll let you know when we launch! 🎉",
  "s_thanks_err": "✅ Thank you! _(Error saving answers)_",

  "c_intro": (
    "Great! You selected the *customer* role.\n\n"
    "We're building TIKUV — a platform to easily find seamstresses online. "
    "Could you spare 3–4 minutes? All answers are anonymous.\n\n"
    "─────────────────\n*Question 1 of 9*\nHow often do you order sewing or clothing repair?"
  ),
  "c_ok": "✅ Got it!\n\n─────────────────\n",
  "c1_opts": [["A few times a year","Once a month"],["Once a week","Never ordered before"]],
  "c2": "*Question 2 of 9*\nWhat do you most often order?\n_(Numbers separated by commas)_\n\n1 — Dress / suit sewing\n2 — National clothing\n3 — Wedding outfit\n4 — Repairs & alterations\n5 — Children's clothing\n6 — Other",
  "c2_ch": {"1":"Dress/suit","2":"National clothing","3":"Wedding outfit","4":"Repairs","5":"Children's clothing","6":"Other"},
  "c3": "*Question 3 of 9*\nHow do you usually find a seamstress?",
  "c3_opts": [["Through friends/family"],["Instagram / TikTok"],["Telegram groups"],["OLX / classifieds"],["I struggle to find one"]],
  "c4": "*Question 4 of 9*\nHow long does it usually take to find a suitable seamstress?",
  "c4_opts": [["A few hours"],["1–3 days"],["A week or more"],["I can't find one at all"]],
  "c5": "*Question 5 of 9*\nHow much do you usually spend per order?",
  "c5_opts": [["Under $10","$10–30"],["$30–80","$80–200"],["Over $200"]],
  "c6": "*Question 6 of 9*\nWhat problems have you faced when ordering sewing?\n_(Numbers separated by commas)_\n\n1 — Hard to find a seamstress\n2 — Unsure about quality\n3 — Deadlines not met\n4 — Payment disputes\n5 — Result didn't match expectations\n6 — No problems",
  "c6_ch": {"1":"Hard to find","2":"Quality concerns","3":"Deadlines missed","4":"Payment disputes","5":"Didn't match expectations","6":"No problems"},
  "c7": "*Question 7 of 9*\nYou post an order online, seamstresses respond, you choose by rating. Payment is protected.\n\n*How interested are you in such a platform?*\nRate 1–5 👇",
  "c7_opts": [["1 — Not interested at all","2"],["3","4"],["5 — Very interested"]],
  "c7_err": "Please rate from 1 to 5 👆",
  "c8": "*Question 8 of 9*\nWhat matters most to you in such a platform?\n_(Up to 3 — numbers separated by commas)_\n\n1 — Find a seamstress quickly\n2 — Quality guarantee\n3 — Payment protection\n4 — Reviews & ratings\n5 — Easy communication\n6 — Reasonable prices",
  "c8_ch": {"1":"Quick search","2":"Quality guarantee","3":"Payment protection","4":"Reviews/ratings","5":"Easy communication","6":"Reasonable prices"},
  "c9": "*Question 9 of 9*\nWhat could stop you from using the platform?\n_(Numbers separated by commas)_\n\n1 — Don't trust online payments\n2 — Doubt seamstress quality\n3 — Prefer finding through friends\n4 — Nothing — ready to try",
  "c9_ch": {"1":"Don't trust payments","2":"Quality doubts","3":"Prefer word of mouth","4":"Ready to try"},
  "c_thanks_ok": "🛍 *Thank you so much!*\n\nYour answers are saved and will help us build the best service for customers.\n\nWe'll let you know when we launch! 🎉",
  "c_thanks_err": "✅ Thank you! _(Error saving answers)_",

  "cancel": "Stopped. Type /start to begin again.",
  "unknown": "Type /start to begin the survey 🧵",
},
} # end T

LANG_KEYBOARD = [["🇷🇺 Русский","🇺🇿 O'zbek (lotin)"],["🇺🇿 Ўзбек (кирилл)","🇬🇧 English"]]
LANG_MAP = {
    "🇷🇺 Русский":        "ru",
    "🇺🇿 O'zbek (lotin)": "uz",
    "🇺🇿 Ўзбек (кирилл)": "uz_cyr",
    "🇬🇧 English":        "en",
}

# ── Google Sheets ──────────────────────────────────────────────────────────
def get_sheet(role: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    wb = client.open_by_key(SHEET_ID)
    sheet_name = "Швеи" if role == "seamstress" else "Клиенты"
    try:
        sheet = wb.worksheet(sheet_name)
    except:
        sheet = wb.add_worksheet(title=sheet_name, rows=1000, cols=20)
        if role == "seamstress":
            sheet.append_row(["Дата","User ID","Язык",
                "1.Стаж","2.Что шьёт","3.Заказов/мес",
                "4.Как ищет клиентов","5.Нехватка заказов","6.Доход",
                "7.Интерес (1-5)","8.Важно","9.Опасения"])
        else:
            sheet.append_row(["Дата","User ID","Язык",
                "1.Частота заказов","2.Что заказывает","3.Как ищет швею",
                "4.Время поиска","5.Бюджет на заказ","6.Проблемы",
                "7.Интерес (1-5)","8.Важно","9.Опасения"])
    return sheet

def save(user_id, lang_key, role, answers, keys):
    try:
        sheet = get_sheet(role)
        row = [datetime.now().strftime("%d.%m.%Y %H:%M"), str(user_id), T[lang_key]["sheet_lang"]]
        row += [answers.get(k,"") for k in keys]
        sheet.append_row(row)
        return True
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        return False

# ── Helpers ───────────────────────────────────────────────────────────────
def kb(opts):
    return ReplyKeyboardRemove() if opts is None else ReplyKeyboardMarkup(opts, resize_keyboard=True, one_time_keyboard=True)

def pm(text, choices, max_sel=99):
    nums = [x.strip() for x in text.replace(","," ").split() if x.strip()]
    sel = [choices[n] for n in nums[:max_sel] if n in choices]
    return ", ".join(sel) if sel else text

def lk(ctx): return ctx.user_data.get("lang","ru")
def t(ctx, key): return T[lk(ctx)][key]
def is_s(ctx): return ctx.user_data.get("role") == "seamstress"

# ── START & LANG ──────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text(
        "👋 Выберите язык / Choose language / Tilni tanlang:",
        reply_markup=kb(LANG_KEYBOARD)
    )
    return LANG

async def handle_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["lang"] = LANG_MAP.get(update.message.text.strip(), "ru")
    await update.message.reply_text(
        t(ctx,"role_prompt"), reply_markup=kb(t(ctx,"role_opts"))
    )
    return ROLE

async def handle_role(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if t(ctx,"role_seamstress") in text:
        ctx.user_data["role"] = "seamstress"
        await update.message.reply_text(t(ctx,"s_intro"), parse_mode="Markdown",
                                        reply_markup=kb(t(ctx,"s1_opts")))
        return S1
    else:
        ctx.user_data["role"] = "customer"
        await update.message.reply_text(t(ctx,"c_intro"), parse_mode="Markdown",
                                        reply_markup=kb(t(ctx,"c1_opts")))
        return C1

# ── ШВЕЯ — вопросы ────────────────────────────────────────────────────────
async def s1(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S1] = update.message.text
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s2"), parse_mode="Markdown", reply_markup=kb(None))
    return S2

async def s2(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S2] = pm(update.message.text, t(ctx,"s2_ch"))
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s3"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"s3_opts")))
    return S3

async def s3(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S3] = update.message.text
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s4"), parse_mode="Markdown", reply_markup=kb(None))
    return S4

async def s4(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S4] = pm(update.message.text, t(ctx,"s4_ch"))
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s5"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"s5_opts")))
    return S5

async def s5(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S5] = update.message.text
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s6"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"s6_opts")))
    return S6

async def s6(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S6] = update.message.text
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s7"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"s7_opts")))
    return S7

async def s7(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    d = update.message.text.strip()[:1]
    if d not in "12345":
        await update.message.reply_text(t(ctx,"s7_err"), reply_markup=kb(t(ctx,"s7_opts")))
        return S7
    ctx.user_data[S7] = d
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s8"), parse_mode="Markdown", reply_markup=kb(None))
    return S8

async def s8(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S8] = pm(update.message.text, t(ctx,"s8_ch"), max_sel=3)
    await update.message.reply_text(t(ctx,"s_ok")+t(ctx,"s9"), parse_mode="Markdown", reply_markup=kb(None))
    return S9

async def s9(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[S9] = pm(update.message.text, t(ctx,"s9_ch"))
    uid = update.effective_user.id
    ok = save(uid, lk(ctx), "seamstress", ctx.user_data, [S1,S2,S3,S4,S5,S6,S7,S8,S9])
    await update.message.reply_text(
        t(ctx,"s_thanks_ok") if ok else t(ctx,"s_thanks_err"),
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    await notify_admin(ctx, uid, "🧵 Швея")
    ctx.user_data.clear()
    return ConversationHandler.END

# ── КЛИЕНТ — вопросы ──────────────────────────────────────────────────────
async def c1(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C1] = update.message.text
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c2"), parse_mode="Markdown", reply_markup=kb(None))
    return C2

async def c2(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C2] = pm(update.message.text, t(ctx,"c2_ch"))
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c3"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"c3_opts")))
    return C3

async def c3(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C3] = update.message.text
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c4"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"c4_opts")))
    return C4

async def c4(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C4] = update.message.text
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c5"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"c5_opts")))
    return C5

async def c5(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C5] = update.message.text
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c6"), parse_mode="Markdown", reply_markup=kb(None))
    return C6

async def c6(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C6] = pm(update.message.text, t(ctx,"c6_ch"))
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c7"), parse_mode="Markdown",
                                    reply_markup=kb(t(ctx,"c7_opts")))
    return C7

async def c7(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    d = update.message.text.strip()[:1]
    if d not in "12345":
        await update.message.reply_text(t(ctx,"c7_err"), reply_markup=kb(t(ctx,"c7_opts")))
        return C7
    ctx.user_data[C7] = d
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c8"), parse_mode="Markdown", reply_markup=kb(None))
    return C8

async def c8(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C8] = pm(update.message.text, t(ctx,"c8_ch"), max_sel=3)
    await update.message.reply_text(t(ctx,"c_ok")+t(ctx,"c9"), parse_mode="Markdown", reply_markup=kb(None))
    return C9

async def c9(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data[C9] = pm(update.message.text, t(ctx,"c9_ch"))
    uid = update.effective_user.id
    ok = save(uid, lk(ctx), "customer", ctx.user_data, [C1,C2,C3,C4,C5,C6,C7,C8,C9])
    await update.message.reply_text(
        t(ctx,"c_thanks_ok") if ok else t(ctx,"c_thanks_err"),
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    await notify_admin(ctx, uid, "🛍 Клиент")
    ctx.user_data.clear()
    return ConversationHandler.END

# ── Admin notify ──────────────────────────────────────────────────────────
async def notify_admin(ctx, uid, role_label):
    if not ADMIN_CHAT_ID:
        return
    try:
        lang_key = ctx.user_data.get("lang","ru")
        flag = T.get(lang_key,{}).get("flag","")
        sheet_lang = T.get(lang_key,{}).get("sheet_lang","")
        keys = [S1,S2,S3,S4,S5,S6,S7,S8,S9] if "Швея" in role_label else [C1,C2,C3,C4,C5,C6,C7,C8,C9]
        lines = "\n".join(f"{i+1}️⃣ {ctx.user_data.get(k,'—')}" for i,k in enumerate(keys))
        msg = f"📋 *{role_label}* {flag} {sheet_lang}\n👤 `{uid}` · {datetime.now().strftime('%d.%m %H:%M')}\n\n{lines}"
        await ctx.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin notify error: {e}")

# ── Cancel & unknown ──────────────────────────────────────────────────────
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(t(ctx,"cancel"), reply_markup=ReplyKeyboardRemove())
    ctx.user_data.clear()
    return ConversationHandler.END

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(ctx,"unknown"))

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lang)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_role)],
            S1:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s1)],
            S2:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s2)],
            S3:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s3)],
            S4:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s4)],
            S5:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s5)],
            S6:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s6)],
            S7:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s7)],
            S8:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s8)],
            S9:   [MessageHandler(filters.TEXT & ~filters.COMMAND, s9)],
            C1:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c1)],
            C2:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c2)],
            C3:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c3)],
            C4:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c4)],
            C5:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c5)],
            C6:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c6)],
            C7:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c7)],
            C8:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c8)],
            C9:   [MessageHandler(filters.TEXT & ~filters.COMMAND, c9)],
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
