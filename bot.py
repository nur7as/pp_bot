import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ContentType, InputMediaPhoto, FSInputFile
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
db  = Database("subscribers.db")


# ─── STATES ───────────────────────────────────────────────────────────────────
class WaitingName(StatesGroup):
    waiting_for_name = State()


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
    "🔗 <a href='{kaspi}'>Kaspi Pay арқылы төлеу →</a>\n\n"
    "<b>2-нұсқа — Басқа банк арқылы:</b>\n"
    f"<code>{CARD_NUM}</code>\n"
    f"{CARD_NAME}\n\n"
    "📸 Төлегеннен кейін скриншотты осы ботқа жіберіңіз\n\n"
    "⏱ Скриншотты жібергеннен кейін <b>5-15 минут ішінде</b> каналға сілтеме келеді!"
)


# ─── STARTUP: загрузка фото ───────────────────────────────────────────────────
PHOTO_IDS = []

async def upload_photos():
    global PHOTO_IDS
    stored = db.get_setting("photo_ids")
    if stored:
        PHOTO_IDS = stored.split(",")
        logging.info(f"Loaded {len(PHOTO_IDS)} photo IDs from DB")
        return

    photo_files = ["photo1.png", "photo2.png", "photo3.png"]
    ids = []
    for fname in photo_files:
        if os.path.exists(fname):
            msg = await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=FSInputFile(fname),
                caption=f"📸 Фото жүктелді: {fname}"
            )
            ids.append(msg.photo[-1].file_id)
            logging.info(f"Uploaded {fname}")

    if ids:
        PHOTO_IDS = ids
        db.save_setting("photo_ids", ",".join(ids))
        await bot.send_message(ADMIN_ID, f"✅ {len(ids)} сурет сәтті жүктелді!")


# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=START_TEXT,
        parse_mode="HTML",
        reply_markup=kb_main()
    )


# ─── BACK TO START ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "start")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
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

    if PHOTO_IDS:
        from aiogram.types import InputMediaPhoto as IMP
        media = [IMP(media=pid) for pid in PHOTO_IDS]
        await call.message.answer_media_group(media=media)

    await call.message.answer(
        text=ABOUT_TEXT,
        parse_mode="HTML",
        reply_markup=kb_about()
    )
    await call.answer()


# ─── BUY ──────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "buy")
async def cb_buy(call: CallbackQuery, state: FSMContext):
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
async def handle_screenshot(message: Message, state: FSMContext):
    user = message.from_user
    current_state = await state.get_state()

    # Если ждём имя — игнорируем фото
    if current_state == WaitingName.waiting_for_name:
        await message.answer("✏️ Алдымен аты-жөніңізді жазыңыз.")
        return

    if db.is_subscriber(user.id):
        await message.answer("✅ Сіз бұрыннан мүшесіз!")
        return

    if db.has_pending(user.id):
        await message.answer("⏳ Сіздің өтінішіңіз қаралуда. Күте тұрыңыз.")
        return

    db.add_pending(user.id)

    username = f"@{user.username}" if user.username else "жоқ"
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

    # Сохраняем pending approval и просим имя
    db.save_setting(f"pending_approve_{user_id}", "1")

    await bot.send_message(
        chat_id=user_id,
        text=(
            "✅ <b>Төлеміңіз расталды!</b>\n\n"
            "Каналға қосу үшін аты-жөніңізді жазыңыз 👇\n"
            "<i>(Мысалы: Айгерім Сейткали)</i>"
        ),
        parse_mode="HTML"
    )

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n⏳ <b>Аты-жөн күтілуде...</b>",
        parse_mode="HTML"
    )
    await call.answer("✅ Клиентке хабарлама жіберілді!")


# ─── WAITING FOR NAME ─────────────────────────────────────────────────────────
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, state: FSMContext):
    user = message.from_user
    user_id = user.id

    # Проверяем — ждём ли имя от этого пользователя
    pending = db.get_setting(f"pending_approve_{user_id}")
    if not pending:
        return

    full_name = message.text.strip()
    username = f"@{user.username}" if user.username else "жоқ"

    try:
        link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"user_{user_id}"
        )

        db.add_subscriber_with_name(user_id, full_name, username)
        db.remove_pending(user_id)
        db.delete_setting(f"pending_approve_{user_id}")

        await message.answer(
            f"🎉 <b>Төлеміңіз қабылданды! Рахмет сізге!</b>\n\n"
            f"Каналға кіру үшін төмендегі жеке сілтемеңізге өтіңіз:\n"
            f"👇 {link.invite_link}\n\n"
            f"⚠️ Бұл сілтеме тек сіз үшін және бір рет қана жұмыс істейді!\n\n"
            f"Каналда сізді көргенімізге қуаныштымыз 🥗\n"
            f"Сұрақтарыңыз болса — {ADMIN_USER}-ке жазыңыз!",
            parse_mode="HTML"
        )

        # Уведомляем админа
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"✅ <b>Қосылды!</b>\n\n"
                f"👤 Аты-жөні: <b>{full_name}</b>\n"
                f"📱 Username: {username}\n"
                f"🆔 ID: <code>{user_id}</code>"
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Қате болды: {e}")


# ─── REJECT ───────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    db.remove_pending(user_id)
    db.delete_setting(f"pending_approve_{user_id}")

    await bot.send_message(
        chat_id=user_id,
        text=(
            "❌ <b>Скриншот қабылданбады.</b>\n\n"
            "Себептері:\n"
            "• Скриншот анық емес\n"
            "• Сомасы дұрыс емес\n"
            "• Төлем расталмады\n\n"
            f"Қайта төлеп, скриншот жіберіңіз немесе {ADMIN_USER}-ке хабарласыңыз."
        ),
        parse_mode="HTML"
    )

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    await call.answer("❌ Отклонено")


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
        name = sub.get('full_name') or '—'
        username = sub.get('username') or '—'
        date = sub.get('added_at', '')
        text += f"{i}. <b>{name}</b> | {username} | {date}\n"

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
    await upload_photos()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
