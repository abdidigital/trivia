import os
import logging
import json
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Inisialisasi Flask app
app = Flask(__name__)

# Ambil Token Bot dari Environment Variable Vercel
BOT_TOKEN = os.environ.get('8264701988:AAH5x9q03FR9Em6RSXOPC_ZEjWiIhD9wcXo')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Endpoint API BARU untuk mengambil soal ---
@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Membaca file soal.json dan mengirimkannya sebagai respons."""
    try:
        # Path relatif dari root folder proyek
        with open('api/soal.json', 'r', encoding='utf-8') as f:
            questions = json.load(f)
        return jsonify(questions)
    except Exception as e:
        logging.error(f"Error reading questions file: {e}")
        return jsonify({"error": "Could not load questions"}), 500

# --- Endpoint Webhook yang sudah ada ---
@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Menerima update dari Telegram dan memprosesnya."""
    # Inisialisasi bot di dalam fungsi agar aman
    bot = Bot(token=BOT_TOKEN)
    
    # Dapatkan data JSON yang dikirim oleh Telegram
    update_data = request.get_json()
    
    # Buat objek Update dari data
    update = Update.de_json(update_data, bot)
    
    # Buat aplikasi dan daftarkan handler (bisa dioptimalkan nanti)
    application = Application.builder().bot(bot).build()

    # Contoh handler jika diperlukan (misal: /start)
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Buka Mini App untuk memulai kuis!")
    
    application.add_handler(CommandHandler("start", start))
    
    # Proses update-nya
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.process_update(update))
    
    return 'ok', 200
    
