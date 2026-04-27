import re
import asyncio
import psutil
import logging
import os
import subprocess
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import timedelta, datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import FSInputFile, BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

API_TOKEN = 'Your_API_Token'
YOUR_CHAT_ID = 000000000
CONFIG_PATH = '/your/configs/directory/'
CPU_LIMIT = 90.0

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

class VPNStates(StatesGroup):
    waiting_for_add_name = State()

cpu_history = []

def get_server_stats():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    net = psutil.net_io_counters()
    sent = round(net.bytes_sent / (1024**2), 2)
    recv = round(net.bytes_recv / (1024**2), 2)
    
    with open('/proc/uptime', 'r') as f:
        uptime = str(timedelta(seconds=int(float(f.readline().split()[0]))))

    return (f"🖥 **СТАТУС СЕРВЕРА**\n\n"
            f"⏱ Аптайм: `{uptime}`\n"
            f"💿 ЦПУ: `{cpu}%` | ОЗУ: `{ram}%` \n"
            f"💽 Диск: `{disk}%` \n"
            f"🌐 Сеть: ↑ `{sent} MB` | ↓ `{recv} MB` \n")

async def get_graph():
    plt.figure(figsize=(8, 4))
    plt.plot(cpu_history, color='orange', linewidth=2)
    plt.title('CPU Load Last Minutes')
    plt.ylabel('Usage %')
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

async def auto_monitor():
    try:
        with open('/var/log/auth.log', 'r') as f:
            f.seek(0, 2)
            last_position = f.tell()
    except:
        last_position = 0

    while True:
        cpu = psutil.cpu_percent()
        cpu_history.append(cpu)
        if len(cpu_history) > 60: cpu_history.pop(0)
        
        if cpu > CPU_LIMIT:
            await bot.send_message(YOUR_CHAT_ID, f"⚠️ **Критическая нагрузка ЦПУ:** `{cpu}%`")

        try:
            with open('/var/log/auth.log', 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
                
                for line in new_lines:
                    if "Accepted" in line and ("ssh2" in line or "password" in line):
                        match = re.search(r'for (\S+) from (\S+)', line)
                        info = f"👤 User: `{match.group(1)}` \n🌐 IP: `{match.group(2)}`" if match else f"`{line.strip()}`"
                        await bot.send_message(YOUR_CHAT_ID, f"🛡 **Новое SSH подключение!**\n{info}", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Monitor error: {e}")

        await asyncio.sleep(10)

def fetch_vpn_clients():
    try:
        res_list = subprocess.check_output(["sudo", "pivpn", "list"], stderr=subprocess.STDOUT).decode('utf-8')
        clean_list = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', res_list)
        
        res_conn = subprocess.check_output(["sudo", "pivpn", "-c"], stderr=subprocess.STDOUT).decode('utf-8')
        clean_conn = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', res_conn)

        clients = []
        for line in clean_list.splitlines():
            line = line.strip()
            if not line or any(x in line for x in [":::", "Client", "---", "Description"]):
                continue
            
            parts = line.split()
            if parts:
                name = parts[0]
                status = "⚪"
                if name in clean_conn:
                    for c_line in clean_conn.splitlines():
                        if name in c_line and any(unit in c_line for unit in ["KiB", "MiB", "GiB"]):
                            status = "🟢"
                            break
                
                clients.append(f"{status} `{name}`")
        
        return sorted(list(set(clients)))
    except Exception as e:
        logging.error(f"Error in fetch_vpn_clients: {e}")
        return []

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📊 Статус")
    kb.button(text="👥 Список")
    kb.button(text="➕ Создать")
    kb.button(text="❌ Удалить")
    kb.button(text="🧹 Очистка")
    kb.button(text="🔄 Ребут")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        await message.answer("🛠 **Панель управления VPN**", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "📊 Статус")
async def stat_msg(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        graph = await get_graph()
        await message.answer_photo(BufferedInputFile(graph.read(), filename="graph.png"), caption=get_server_stats(), parse_mode="Markdown")

@dp.message(F.text == "👥 Список")
async def list_msg(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        c = fetch_vpn_clients()
        text = "👥 **Клиенты (🟢-в сети):**\n\n" + "\n".join(c) if c else "Список пуст."
        await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "➕ Создать")
async def vpn_add_req(message: types.Message, state: FSMContext):
    if message.from_user.id == YOUR_CHAT_ID:
        await message.answer("⌨️ Введите имя клиента:", reply_markup=InlineKeyboardBuilder().button(text="Отмена", callback_data="cancel").as_markup())
        await state.set_state(VPNStates.waiting_for_add_name)

@dp.message(VPNStates.waiting_for_add_name)
async def vpn_add_exec(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not re.match(r"^[a-zA-Z0-9_-]+$", name): return await message.answer("❌ Неверное имя")
    
    await message.answer(f"⚙️ Генерирую `{name}`...")
    os.system(f"printf '\n' | sudo pivpn add -n {name}")
    await asyncio.sleep(2)
    
    file_path = f"{CONFIG_PATH}{name}.conf"
    if os.path.exists(file_path):
        qr_path = f"{file_path}.png"
        os.system(f"qrencode -t png -o {qr_path} < {file_path}")
        await bot.send_document(YOUR_CHAT_ID, FSInputFile(file_path))
        await bot.send_photo(YOUR_CHAT_ID, FSInputFile(qr_path), caption="📱 QR-код для WireGuard")
        os.remove(qr_path)
    await state.clear()

@dp.message(F.text == "❌ Удалить")
async def vpn_del_choose(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        clients = [c.split("`")[1] for c in fetch_vpn_clients()]
        if not clients: return await message.answer("Пусто")
        kb = InlineKeyboardBuilder()
        for c in clients: kb.button(text=f"🗑 {c}", callback_data=f"del_{c}")
        kb.adjust(2).row(types.InlineKeyboardButton(text="Отмена", callback_data="cancel"))
        await message.answer("Кого удаляем?", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def vpn_del_exec(callback: types.CallbackQuery):
    name = callback.data.split("_")[1]
    os.system(f"sudo pivpn -r -y {name}")
    await callback.message.edit_text(f"✅ `{name}` удален.")

@dp.message(F.text == "🧹 Очистка")
async def sys_clean(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        await message.answer("🧹 Начинаю очистку...")
        os.system("sudo apt clean && sudo apt autoremove -y")
        await message.answer("✅ Система очищена!")

@dp.callback_query(F.data == "cancel")
async def cancel(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.delete()

@dp.message(F.text == "🔄 Ребут")
async def reboot_req(message: types.Message):
    if message.from_user.id == YOUR_CHAT_ID:
        kb = InlineKeyboardBuilder().button(text="Да", callback_data="reboot").button(text="Нет", callback_data="cancel")
        await message.answer("Перезагрузить?", reply_markup=kb.adjust(2).as_markup())

@dp.callback_query(F.data == "reboot")
async def do_reboot(cb: types.CallbackQuery):
    await cb.message.edit_text("♻️ Ребут...")
    os.system("sudo reboot")

async def main():
    try:
        await bot.send_message(YOUR_CHAT_ID, "🚀 **Сервер запущен и бот активен!**", parse_mode="Markdown")
    except: pass
    asyncio.create_task(auto_monitor())
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

