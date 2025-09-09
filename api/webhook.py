import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Inisialisasi Flask app
app = Flask(__name__)

# Ambil Token Bot dari Environment Variable Vercel
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8264701988:AAH5x9q03FR9Em6RSXOPC_ZEjWiIhD9wcXo')

# Inisialisasi bot
bot = Bot(token=BOT_TOKEN)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bank Soal (sama seperti sebelumnya)
BANK_SOAL = [
    {
        "pertanyaan": "Apa ibukota Indonesia?",
        "opsi": ["Bandung", "Surabaya", "Jakarta", "Medan"],
        "jawaban_benar": 2
    },
    {
        "pertanyaan": "Siapakah presiden pertama Indonesia?",
        "opsi": ["Soeharto", "Soekarno", "B.J. Habibie", "Joko Widodo"],
        "jawaban_benar": 1
    }
]

# --- Fungsi-fungsi Handler (sama seperti sebelumnya) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"Hai {user.mention_html()}! Ketik /kuis untuk memulai."
    )

async def kuis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    soal = BANK_SOAL[1] # Ambil soal
    await context.bot.send_quiz(
        chat_id=update.effective_chat.id,
        question=soal["pertanyaan"],
        options=soal["opsi"],
        correct_option_id=soal["jawaban_benar"],
        type='quiz'
    )

# --- Endpoint utama untuk Webhook ---
# Vercel akan mengarahkan semua request ke file ini.
# Flask akan menangani routing ke path '/'.
@app.route('/', methods=['POST'])
def webhook():
    # Dapatkan data JSON yang dikirim oleh Telegram
    update_data = request.get_json()

    # Buat objek Update dari data
    update = Update.de_json(update_data, bot)

    # Proses update (ini akan memanggil command handler yang sesuai)
    # Kita perlu membuat Application & Dispatcher di sini
    application = Application.builder().bot(bot).build()

    # Daftarkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("kuis", kuis))

    # Proses update-nya
    # Menggunakan asyncio untuk menjalankan fungsi async di dalam fungsi sync
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))

    # Beri respon OK 200 ke Telegram agar tidak mengirim update yang sama berulang kali
    return 'ok'

# Endpoint untuk development lokal (opsional)
if __name__ == "__main__":
    app.run(debug=True)
  
