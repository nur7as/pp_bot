import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ContentType, InputMediaPhoto
)
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
KASPI_LINK = os.getenv("KASPI_LINK", "")
PRICE      = 7000
CARD_NUM   = "5269 8800 1480 4728"
CARD_NAME  = "Нуртас И."
ADMIN_USER = "@nurtas_issabek"

# Скриншоты канала (file_id заполнится при первом запуске)
# Пока используем прямые ссылки — после первого запуска замените на file_id
CHANNEL_PHOTOS = os.getenv("CHANNEL_PHOTOS", "").split(",") if os.getenv("CHANNEL_PHOTOS") else []

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
db  = Database("subscribers.db")


# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Төлем жасау — 7 000 ₸", callback_data="buy")],
        [InlineKeyboardButton(text="🥗 Канал ішінде не бар?",   callback_data="about")],
    ])

def kb_about():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Төлем жасау — 7 000 ₸", callback_data="buy")],
        [InlineKeyboardButton(text="◀️ Артқа",                  callback_data="start")],
    ])

def kb_paid(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить",  callback_data=f"approve:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")],
    ])

def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Артқа", callback_data="start")],
    ])


# ─── TEXTS ────────────────────────────────────────────────────────────────────
START_TEXT = (
    "Сәлеметсіз бе 🤗\n\n"
    "Cізді өзімнің дайын күндік/апталық/айлық рацион мен пайдалы тамақтар рецепті сақталған каналыма шақырамын 🥗\n\n"
    "<b>КАНАЛ КІМГЕ АРНАЛҒАН?</b>\n"
    "• Артық салмақтан сапалы түрде \"срыв\" болмай арылғысы келетіндерге\n"
    "• Дұрыс, КБЖУ балансын сақтап тамақтанғысы келетіндерге\n"
    "• Уақытыңызды алмайтын, ақшаңыз артық жұмсалмайтын дайын, дәмді әрі пайдалы тағамдардың тұруын қалайтындарға\n"
    "• Дұрыс салмақ қосқысы келетіндерге\n\n"
    "✅ Каналда дайын рациондар рецепттері мен видео обзорлары, КБЖУ, пайдалы ақпараттар бар\n\n"
    "💫 Канал сізде <b>шексіз</b> қалады — бір рет төлейсіз, мәңгі пайдаланасыз\n\n"
    "<b>Бағасы: 7 000 ₸</b>\n\n"
    "👇 Төменде таңдаңыз"
)

ABOUT_TEXT = (
    "<b>Каналда не бар? 🥗</b>\n\n"
    "💪🏻 КБЖУ және калория дефициті/профициті — қалай есептейміз, салмақ тастауға/қосуға қалай пайдаланамыз\n\n"
    "🍽 Күннің 3 уақытына арналған дайын рациондар — қолжетімді өнімдерден, рецептімен және видео обзормен\n\n"
    "🧇 ПП тәттілер рецепттері — дәмді, бірақ пайдалы\n\n"
    "🛒 Апталық/айлық азық-түліктер тізімі — не алу керек, қалай жоспарлау керек\n\n"
    "✔️ Әр рецепттің толық есептелген КБЖУ\n\n"
    "💡 Қосымша: пайдалы ақпараттар, лайфхактар, жаттығулар тізімі\n\n"
    "━━━━━━━━━━━━━━━\n"
    "💫 Бір рет төлейсіз — шексіз қол жеткізу\n"
    "<b>Бағасы: 7 000 ₸</b>"
)

BUY_TEXT = (
    "💳 <b>Төлем жасау — 7 000 ₸</b>\n\n"
    "<b>1-нұсқа — Kaspi Pay:</b>\n"
    f"🔗 <a href='{{kaspi}}'>Kaspi Pay арқылы төлеу →</a>\n\n"
    "<b>2-нұсқа — Басқа банк арқылы:</b>\n"
    f"<code>{CARD_NUM}</code>\n"
    f"{CARD_NAME}\n\n"
    "📸 Төлегеннен кейін скриншотты осы ботқа жіберіңіз\n\n"
    "⏱ Скриншотты жібергеннен кейін <b>5-15 минут ішінде</b> каналға сілтеме келеді!"
)

APPROVE_TEXT = (
    "🎉 <b>Төлеміңіз қабылданды! Рахмет сізге!</b>\n\n"
    "Каналға кіру үшін төмендегі жеке сілтемеңізге өтіңіз:\n"
    "👇 {link}\n\n"
    "⚠️ Бұл сілтеме тек сіз үшін және бір рет қана жұмыс істейді!\n\n"
    "Каналда сізді көргенімізге қуаныштымыз 🥗\n"
    f"Сұрақтарыңыз болса — {ADMIN_USER}-ке жазыңыз!"
)

REJECT_TEXT = (
    "❌ <b>Скриншот қабылданбады.</b>\n\n"
    "Себептері:\n"
    "• Скриншот анық емес\n"
    "• Сомасы дұрыс емес\n"
    "• Төлем расталмады\n\n"
    f"Қайта төлеп, скриншот жіберіңіз немесе {ADMIN_USER}-ке хабарласыңыз."
)


# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        text=START_TEXT,
        parse_mode="HTML",
        reply_markup=kb_main()
    )


# ─── BACK TO START ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "start")
async def cb_back(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        text=START_TEXT,
        parse_mode="HTML",
        reply_markup=kb_main()
    )
    await call.answer()


# ─── ABOUT ────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    await call.message.delete()

    # Отправляем скриншоты канала если есть
    if CHANNEL_PHOTOS and CHANNEL_PHOTOS[0]:
        media = [InputMediaPhoto(media=photo_id) for photo_id in CHANNEL_PHOTOS if photo_id]
        if media:
            await call.message.answer_media_group(media=media)

    await call.message.answer(
        text=ABOUT_TEXT,
        parse_mode="HTML",
        reply_markup=kb_about()
    )
    await call.answer()


# ─── BUY ──────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "buy")
async def cb_buy(call: CallbackQuery):
    if db.is_subscriber(call.from_user.id):
        await call.answer("✅ Сіз бұрыннан мүшесіз!", show_alert=True)
        return

    await call.message.delete()
    await call.message.answer(
        text=BUY_TEXT.format(kaspi=KASPI_LINK),
        parse_mode="HTML",
        reply_markup=kb_cancel(),
        disable_web_page_preview=True
    )
    await call.answer()


# ─── SCREENSHOT ───────────────────────────────────────────────────────────────
@dp.message(F.content_type == ContentType.PHOTO)
async def handle_screenshot(message: Message):
    user = message.from_user

    if db.is_subscriber(user.id):
        await message.answer("✅ Сіз бұрыннан мүшесіз!")
        return

    if db.has_pending(user.id):
        await message.answer("⏳ Сіздің өтінішіңіз қаралуда. Күте тұрыңыз.")
        return

    db.add_pending(user.id)

    username = f"@{user.username}" if user.username else f"id:{user.id}"
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=(
            f"💰 <b>Жаңа төлем!</b>\n\n"
            f"👤 Аты: {name}\n"
            f"📱 Username: {username}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📅 Уақыт: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Скриншотты тексеріп, шешім қабылдаңыз:"
        ),
        parse_mode="HTML",
        reply_markup=kb_paid(user.id)
    )

    await message.answer(
        "✅ Скриншот жіберілді!\n\n"
        "⏳ Әкімші тексергеннен кейін сізге хабарлама келеді.\n"
        "Әдетте 5-15 минут ішінде."
    )


# ─── APPROVE ──────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])

    try:
        link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"user_{user_id}"
        )

        db.add_subscriber(user_id)
        db.remove_pending(user_id)

        await bot.send_message(
            chat_id=user_id,
            text=APPROVE_TEXT.format(link=link.invite_link),
            parse_mode="HTML"
        )

        await call.message.edit_caption(
            caption=call.message.caption + "\n\n✅ <b>ОДОБРЕНО</b> — сілтеме жіберілді",
            parse_mode="HTML"
        )

    except Exception as e:
        await call.message.answer(f"❌ Қате: {e}")

    await call.answer("✅ Одобрено!")


# ─── REJECT ───────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    db.remove_pending(user_id)

    await bot.send_message(
        chat_id=user_id,
        text=REJECT_TEXT,
        parse_mode="HTML"
    )

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    await call.answer("❌ Отклонено")


# ─── /getid (admin only) ─────────────────────────────────────────────────────
@dp.message(Command("getid"))
async def cmd_getid(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "📸 Енді маған сурет жібер — мен оның file_id-ін көрсетемін.\n"
        "3 суретті бірінен соң бірін жібер."
    )


@dp.message(F.photo & F.from_user.id == ADMIN_ID & F.text.is_(None))
async def get_photo_id(message: Message):
    # Показываем file_id только если последняя команда была /getid
    file_id = message.photo[-1].file_id
    await message.answer(
        f"✅ File ID:\n<code>{file_id}</code>\n\n"
        f"Осыны көшіріп, Railway-дегі CHANNEL_PHOTOS-қа қос.",
        parse_mode="HTML"
    )


# ─── /users (admin only) ──────────────────────────────────────────────────────
@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    subscribers = db.get_all_subscribers()

    if not subscribers:
        await message.answer("📭 Әзірше мүшелер жоқ.")
        return

    text = f"👥 <b>Барлық мүшелер: {len(subscribers)}</b>\n\n"
    for i, sub in enumerate(subscribers, 1):
        text += f"{i}. ID: <code>{sub['user_id']}</code> — {sub['added_at']}\n"

    await message.answer(text, parse_mode="HTML")


# ─── /stats (admin only) ─────────────────────────────────────────────────────
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    count = db.get_subscriber_count()
    pending = db.get_pending_count()
    revenue = count * PRICE

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"✅ Барлық мүшелер: <b>{count}</b>\n"
        f"⏳ Күтудегі өтініштер: <b>{pending}</b>\n"
        f"💰 Жалпы кіріс: <b>{revenue:,} ₸</b>",
        parse_mode="HTML"
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
