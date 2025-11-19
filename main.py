import asyncio
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import threading

# Получаем порт от Render или используем по умолчанию
PORT = int(os.environ.get('PORT', 8080))

# Запуск веб-сервера для Render
async def health_check(request):
    return web.Response(text="Bot is alive")

def run_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    web.run_app(app, host='0.0.0.0', port=PORT)

def start_web_server():
    thread = threading.Thread(target=run_web_server)
    thread.daemon = True
    thread.start()
    print(f"🌐 Web server started on port {PORT}")

# Ваш основной код бота
TOKEN = os.getenv('BOT_TOKEN', '7721643935:AAF2_grhfwPxqoCqmiN7alBti6c01gNtKys')

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class FilterState(StatesGroup):
    waiting_for_min_amount = State()
    waiting_for_logs = State()

@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def set_min_amount(msg: Message, state: FSMContext):
    try:
        min_amount = float(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введите число, например 10")
        return

    await state.update_data(min_amount=min_amount)
    await msg.answer("✅ Отлично! Теперь отправь список логов для фильтрации.")
    await state.set_state(FilterState.waiting_for_logs)

@dp.message(FilterState.waiting_for_logs)
async def filter_logs(msg: Message, state: FSMContext):
    data = await state.get_data()
    min_amount = data.get("min_amount", 0)
    logs = msg.text
    lines = logs.splitlines()

    last_records = {}

    for line in lines:
        if ("🟥wd👾" in line) and ("💸" in line) and ("🆔" in line):
            try:
                status = "success" if "success" in line else "pending" if "pending" in line else None
                if not status:
                    continue

                tx_id = line.split("🆔")[1].split("💸")[0].strip()
                amount = float(line.split("💸")[1].split("🏴")[0].strip())

                if amount >= min_amount:
                    last_records[tx_id] = {
                        "amount": amount,
                        "status": status
                    }
            except Exception:
                continue

    if not last_records:
        await msg.answer("❌ Ничего не найдено по условиям.")
        await state.clear()
        return

    result = []
    for i, (tx_id, data) in enumerate(last_records.items(), start=1):
        status_icon = "✅" if data["status"] == "success" else "⏳"
        result.append(f"{i}) {status_icon} 🆔 <code>{tx_id}</code> 💸 {data['amount']}")

    await msg.answer("\n".join(result), parse_mode=ParseMode.HTML)
    await msg.answer("💰 Отправь новое число, чтобы задать другой фильтр, или новый список логов.")
    await state.clear()

@dp.message()
async def ask_for_min(msg: Message, state: FSMContext):
    await msg.answer("💰 Введите минимальную сумму для фильтрации (например, 10):")
    await state.set_state(FilterState.waiting_for_min_amount)

@dp.message(FilterState.waiting_for_min_amount)
async def receive_min_then_logs(msg: Message, state: FSMContext):
    try:
        min_amount = float(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введите корректное число, например 10.")
        return
    await state.update_data(min_amount=min_amount)
    await msg.answer("✅ Теперь отправь список логов.")
    await state.set_state(FilterState.waiting_for_logs)

async def main():
    # Запускаем веб-сервер
    start_web_server()
    
    print("🤖 Бот запущен и готов к работе на Render...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
