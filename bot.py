import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ContentType
)
from aiogram.fsm.storage.memory import MemoryStorage

from database import Database

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN")
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))        # числовой ID админа
CHANNEL_ID  = int(os.getenv("CHANNEL_ID", "0"))      # -1001003358660639
KASPI_LINK  = os.getenv("KASPI_LINK", "")
PRICE       = 7000

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
db  = Database("subscribers.db")


# ─── KEYBOARDS ────────────────────────────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить доступ — 7 000 ₸", callback_data="buy")],
        [InlineKeyboardButton(text="❓ Что внутри канала?",       callback_data="about")],
    ])

def kb_paid(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить",  callback_data=f"approve:{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")],
    ])

def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="start")],
    ])


# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer_photo(
        photo="https://i.imgur.com/placeholder.jpg",   # замени на свою фотографию
        caption=(
            "👋 Сәлем! Мен — <b>ПП Рецепты</b> каналының боты.\n\n"
            "🥗 Біздің каналда:\n"
            "• Дәмді және пайдалы рецепттер\n"
            "• Арықтауға арналған тамақтану жоспары\n"
            "• Перизаттың жеке кеңестері\n"
            "• Жаңа рецепттер апта сайын\n\n"
            f"💳 Баға: <b>{PRICE:,} ₸</b> — <b>мәңгілік қол жеткізу</b>\n\n"
            "Төменде таңдаңыз 👇"
        ),
        parse_mode="HTML",
        reply_markup=kb_main()
    )


# ─── ABOUT ────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery):
    await call.message.edit_caption(
        caption=(
            "📖 <b>Каналда не бар?</b>\n\n"
            "✅ 200+ ПП рецепт (с КБЖУ)\n"
            "✅ Апта сайын жаңа рецепттер\n"
            "✅ Нәтижелі арықтау жоспары\n"
            "✅ Перизаттың жеке кеңестері\n"
            "✅ Жауаптар мен сұрақтарға қолдау\n\n"
            "👥 Каналда 1000+ белсенді мүше\n\n"
            f"💳 Бір рет төлейсің — <b>мәңгілік қол жеткізу</b>\n"
            f"Баға: <b>{PRICE:,} ₸</b>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Сатып алу", callback_data="buy")],
            [InlineKeyboardButton(text="◀️ Артқа",     callback_data="start")],
        ])
    )
    await call.answer()


# ─── BACK TO START ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "start")
async def cb_back(call: CallbackQuery):
    await call.message.edit_caption(
        caption=(
            "👋 Сәлем! Мен — <b>ПП Рецепты</b> каналының боты.\n\n"
            "🥗 Біздің каналда:\n"
            "• Дәмді және пайдалы рецепттер\n"
            "• Арықтауға арналған тамақтану жоспары\n"
            "• Перизаттың жеке кеңестері\n"
            "• Жаңа рецепттер апта сайын\n\n"
            f"💳 Баға: <b>{PRICE:,} ₸</b> — <b>мәңгілік қол жеткізу</b>\n\n"
            "Төменде таңдаңыз 👇"
        ),
        parse_mode="HTML",
        reply_markup=kb_main()
    )
    await call.answer()


# ─── BUY ──────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "buy")
async def cb_buy(call: CallbackQuery):
    # проверить — уже подписчик?
    if db.is_subscriber(call.from_user.id):
        await call.answer("✅ Сіз бұрыннан мүшесіз!", show_alert=True)
        return

    await call.message.edit_caption(
        caption=(
            "💳 <b>Төлем жасау:</b>\n\n"
            f"1️⃣ Төмендегі Kaspi Pay сілтемесіне өтіңіз\n"
            f"2️⃣ <b>{PRICE:,} ₸</b> төлеңіз\n"
            f"3️⃣ Төлем скриншотын осы ботқа жіберіңіз\n\n"
            f"🔗 <a href='{KASPI_LINK}'>Kaspi Pay арқылы төлеу →</a>\n\n"
            "📸 Төлегеннен кейін скриншотты осы чатқа жіберіңіз"
        ),
        parse_mode="HTML",
        reply_markup=kb_cancel()
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

    # Уведомление админу
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
        # Генерируем одноразовую invite-ссылку
        link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"user_{user_id}"
        )

        db.add_subscriber(user_id)
        db.remove_pending(user_id)

        # Отправляем ссылку клиенту
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Төлеміңіз қабылданды!</b>\n\n"
                "Төмендегі сілтеме арқылы каналға кіріңіз:\n"
                f"👇 {link.invite_link}\n\n"
                "⚠️ Бұл сілтеме бір рет қана жұмыс істейді — тек сіз үшін!\n\n"
                "Қош келдіңіз! 🥗"
            ),
            parse_mode="HTML"
        )

        # Обновляем сообщение у админа
        await call.message.edit_caption(
            caption=call.message.caption + f"\n\n✅ <b>ОДОБРЕНО</b> — сілтеме жіберілді",
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
        text=(
            "❌ <b>Скриншот қабылданбады.</b>\n\n"
            "Себептері:\n"
            "• Скриншот анық емес\n"
            "• Сомасы дұрыс емес\n"
            "• Төлем расталмады\n\n"
            "Қайта төлеп, скриншот жіберіңіз немесе @nurtas_issabek-ке хабарласыңыз."
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
