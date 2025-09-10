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
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
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

class Player(Model):
    user_id = IntegerField(unique=True)
    first_name = CharField()
    last_name = CharField(null=True)
    username = CharField(null=True)
    level = IntegerField(default=0)
    xp = IntegerField(default=0)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db

def init_db():
    db.connect(reuse_if_open=True)
    db.create_tables([Player], safe=True)
    db.close()

init_db()

# --- Endpoint API ---
@app.route("/api/get_single_question", methods=["GET"])
def get_single_question():
    """Menghasilkan SATU soal unik dari Gemini sesuai level."""
    level = int(request.args.get('level', 0))
    if level <= 2: difficulty = "sangat mudah"
    elif level <= 5: difficulty = "mudah"
    elif level <= 10: difficulty = "sedang"
    else: difficulty = "sulit"

    prompt_kuis = f"""
    Buatkan 1 pertanyaan kuis pilihan ganda tentang pengetahuan umum acak. 
    Level kesulitan: {difficulty}. Bahasa: Indonesia.
    Format output HARUS berupa objek JSON tunggal yang valid, tanpa teks atau penjelasan tambahan.
    Objek JSON harus memiliki kunci: "pertanyaan", "opsi" (array 4 string), dan "jawabanBenar".
    """
    try:
        if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY tidak diatur")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_kuis)
        raw_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        question = json.loads(raw_response)
        return jsonify(question)
    except Exception as e:
        logging.error(f"Error saat memanggil Gemini API: {e}")
        return jsonify({"error": "Tidak bisa menghubungi AI generator"}), 500

@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    """Menerima progres 1 jawaban, menghitung XP, dan memproses kenaikan level."""
    data = request.json
    try:
        user_data = data["user"]
        correct_answer_increment = data["score"] # Akan bernilai 1 atau 0
        
        db.connect(reuse_if_open=True)
        player, created = Player.get_or_create(
            user_id=user_data["id"],
            defaults={"first_name": user_data.get("first_name", "Unknown")}
        )
        
        player.xp += correct_answer_increment
        level_up_occurred = False
        
        xp_needed = 10 + (player.level * 5)
        if player.xp >= xp_needed:
            player.level += 1
            player.xp -= xp_needed
            level_up_occurred = True
            
        player.save()
        
        return jsonify({
            "status": "success", 
            "level": player.level, 
            "xp": player.xp, 
            "xp_needed": 10 + (player.level * 5),
            "level_up": level_up_occurred 
        })
    except Exception as e:
        logging.error(f"Database error on submit score: {e}")
        return jsonify({"error": "Could not save score"}), 500
    finally:
        if not db.is_closed(): db.close()

@app.route("/api/get_user_progress", methods=["GET"])
def get_user_progress():
    """Mengambil data level, xp, dan xp yang dibutuhkan."""
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "user_id is required"}), 400
    try:
        db.connect(reuse_if_open=True)
        player = Player.get_or_none(Player.user_id == user_id)
        if player:
            xp_needed = 10 + (player.level * 5)
            return jsonify({"level": player.level, "xp": player.xp, "xp_needed": xp_needed})
        else:
            return jsonify({"level": 0, "xp": 0, "xp_needed": 10}) 
    except Exception as e:
        logging.error(f"Database error on get user progress: {e}")
        return jsonify({"error": "Could not fetch user progress"}), 500
    finally:
        if not db.is_closed(): db.close()

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Mengambil leaderboard diurutkan berdasarkan level dan XP."""
    try:
        db.connect(reuse_if_open=True)
        top_players = Player.select().order_by(Player.level.desc(), Player.xp.desc()).limit(10)
        leaderboard_data = [{"rank": i + 1, "first_name": p.first_name, "level": p.level} for i, p in enumerate(top_players)]
        return jsonify(leaderboard_data)
    except Exception as e:
        logging.error(f"Database error on get leaderboard: {e}")
        return jsonify({"error": "Could not fetch leaderboard"}), 500
    finally:
        if not db.is_closed(): db.close()

@app.route('/api/webhook', methods=['POST'])
def webhook():
    return 'ok', 200
        
