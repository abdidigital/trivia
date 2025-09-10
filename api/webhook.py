import os
import logging
import json
import datetime
import google.generativeai as genai
from flask import Flask, request, jsonify
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    IntegerField,
    DateTimeField
)

# --- Konfigurasi & Inisialisasi ---
app = Flask(__name__)
BOT_TOKEN = os.environ.get("8264701988:AAH5x9q03FR9Em6RSXOPC_ZEjWiIhD9wcXo")

# Konfigurasi kunci API Gemini
GEMINI_API_KEY = os.environ.get("AIzaSyA5WC0JNFSVdtnm8Z_pyaL9vsc2nMbfQHI")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Pengaturan Database (SQLite) ---
db_path = "/tmp/leaderboard.db"
db = SqliteDatabase(db_path)

class BaseModel(Model):
    class Meta:
        database = db

class Score(BaseModel):
    user_id = IntegerField(unique=True)
    first_name = CharField()
    last_name = CharField(null=True)
    username = CharField(null=True)
    score = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Score], safe=True)
    db.close()

init_db()

# --- Endpoint API ---
@app.route("/api/questions", methods=["GET"])
def get_questions():
    """Menghasilkan 5 soal unik dari Google Gemini."""
    prompt_kuis = """
    Buatkan 5 pertanyaan kuis pilihan ganda tentang pengetahuan umum acak (sains, sejarah, geografi, teknologi). 
    Level kesulitan: sedang. Bahasa: Indonesia.
    Format output HARUS berupa array JSON yang valid, tanpa teks atau penjelasan tambahan di luar array.
    Setiap objek dalam array harus memiliki kunci: "pertanyaan" (string), "opsi" (array berisi 4 string), dan "jawabanBenar" (string).
    """
    try:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tidak diatur")
        logging.info("Meminta soal baru dari Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_kuis)
        raw_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        logging.info("Menerima jawaban dari Gemini.")
        questions = json.loads(raw_response)
        return jsonify(questions)
    except Exception as e:
        logging.error(f"Error saat memanggil Gemini API: {e}")
        return jsonify({"error": "Tidak bisa menghubungi AI generator"}), 500

@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    data = request.json
    try:
        user_data = data["user"]
        user_score = data["score"]
        db.connect(reuse_if_open=True)
        player, created = Score.get_or_create(
            user_id=user_data["id"],
            defaults={
                "first_name": user_data.get("first_name", "Unknown"),
                "last_name": user_data.get("last_name"),
                "username": user_data.get("username"),
                "score": user_score,
            },
        )
        if not created and user_score > player.score:
            player.score = user_score
            player.updated_at = datetime.datetime.now()
            player.save()
        return jsonify({"status": "success"})
    except Exception as e:
        logging.error(f"Database error on submit score: {e}")
        return jsonify({"error": "Could not save score"}), 500
    finally:
        if not db.is_closed():
            db.close()

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    try:
        db.connect(reuse_if_open=True)
        top_scores = Score.select().order_by(Score.score.desc()).limit(10)
        leaderboard_data = [
            {"rank": i + 1, "first_name": score.first_name, "score": score.score}
            for i, score in enumerate(top_scores)
        ]
        return jsonify(leaderboard_data)
    except Exception as e:
        logging.error(f"Database error on get leaderboard: {e}")
        return jsonify({"error": "Could not fetch leaderboard"}), 500
    finally:
        if not db.is_closed():
            db.close()

@app.route('/api/webhook', methods=['POST'])
def webhook():
    # Fungsi ini bisa dikembangkan lebih lanjut jika bot butuh merespon chat
    return 'ok', 200
        
