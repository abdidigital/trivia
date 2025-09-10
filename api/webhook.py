import os
import logging
import json
import datetime
import random
import hashlib
import google.generativeai as genai
from flask import Flask, request, jsonify
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    IntegerField,
    DateTimeField,
    ForeignKeyField
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

class AnsweredQuestion(BaseModel):
    player = ForeignKeyField(Player, backref='questions')
    question_hash = CharField(index=True)

# ## FUNGSI BARU UNTUK INISIALISASI DATABASE SEKALI JALAN ##
def initialize_database():
    """Fungsi ini hanya akan dipanggil jika file database belum ada."""
    try:
        db.connect()
        db.create_tables([Player, AnsweredQuestion], safe=True)
        logging.info("Tabel database berhasil dibuat.")
    except Exception as e:
        logging.error(f"Gagal membuat tabel database: {e}")
    finally:
        if not db.is_closed():
            db.close()

# --- Pengelola Koneksi Database Otomatis ---
@app.before_request
def before_request():
    # ## PERUBAHAN UTAMA: Cek file sebelum connect ##
    # Jika file .db belum ada di direktori /tmp, buat dulu
    if not os.path.exists(db_path):
        initialize_database()
    db.connect(reuse_if_open=True)

@app.after_request
def after_request(response):
    if not db.is_closed():
        db.close()
    return response

# Hapus blok "with app.app_context()" yang lama

# --- Endpoint API ---
@app.route("/api/get_question_batch", methods=["GET"])
def get_question_batch():
    # ... (KODE FUNGSI INI SAMA PERSIS SEPERTI SEBELUMNYA, TIDAK ADA PERUBAHAN)
    user_id = request.args.get('user_id')
    level = int(request.args.get('level', 0))
    if not user_id: return jsonify({"error": "user_id is required"}), 400

    TOPIK_KUIS = [
        "Sains dan Alam", "Sejarah Dunia", "Geografi", "Teknologi dan Komputer",
        "Seni dan Budaya", "Film dan Sinema", "Musik Modern", "Musik Klasik", "Olahraga Dunia",
        "Mitologi Yunani", "Mitologi Romawi", "Mitologi Nordik", "Makanan dan Minuman Internasional",
        "Astronomi dan Luar Angkasa", "Biologi dan Hewan", "Kimia Dasar", "Fisika Sehari-hari",
        "Kesusastraan Dunia", "Penemuan dan Inovasi", "Anatomi Manusia", "Ibukota Negara"
    ]
    
    if level <= 5: difficulty = "mudah"
    elif level <= 15: difficulty = "sedang"
    else: difficulty = "sulit"
    topik_acak = random.choice(TOPIK_KUIS)

    prompt_kuis = f"""
    Buatkan 50 pertanyaan kuis pilihan ganda tentang topik "{topik_acak}".
    Level kesulitan: {difficulty}. Bahasa: Indonesia.
    Format output HARUS berupa array JSON yang valid, tanpa teks atau penjelasan tambahan.
    Setiap objek dalam array harus memiliki kunci: "pertanyaan", "opsi" (array 4 string), dan "jawabanBenar".
    """
    try:
        if not GEMINI_API_KEY: raise ValueError("GEMINI_API_KEY tidak diatur")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_kuis)
        raw_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        generated_questions = json.loads(raw_response)
        
        player = Player.get_or_none(Player.user_id == user_id)
        
        answered_hashes = set()
        if player:
            query = AnsweredQuestion.select(AnsweredQuestion.question_hash).where(AnsweredQuestion.player == player)
            answered_hashes = {q.question_hash for q in query}
        
        unique_questions = [q for q in generated_questions if hashlib.sha256(q.get("pertanyaan", "").encode()).hexdigest() not in answered_hashes]
        
        logging.info(f"Generated {len(generated_questions)}, returning {len(unique_questions)} unique questions for user {user_id}")
        return jsonify(unique_questions)
    except Exception as e:
        error_message = f"Error di backend: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500


@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    # ... (KODE FUNGSI INI SAMA PERSIS SEPERTI SEBELUMNYA, TIDAK ADA PERUBAHAN)
    data = request.json
    try:
        user_data = data["user"]
        correct_answer_increment = data["score"]
        question_text = data.get("question")
        
        player, created = Player.get_or_create(
            user_id=user_data["id"],
            defaults={"first_name": user_data.get("first_name", "Unknown")}
        )
        
        if question_text:
            question_hash = hashlib.sha256(question_text.encode()).hexdigest()
            AnsweredQuestion.get_or_create(player=player, question_hash=question_hash)

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

@app.route("/api/get_user_progress", methods=["GET"])
def get_user_progress():
    # ... (KODE FUNGSI INI SAMA PERSIS SEPERTI SEBELUMNYA, TIDAK ADA PERUBAHAN)
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "user_id is required"}), 400
    try:
        player = Player.get_or_none(Player.user_id == user_id)
        if player:
            xp_needed = 10 + (player.level * 5)
            return jsonify({"level": player.level, "xp": player.xp, "xp_needed": xp_needed})
        else:
            return jsonify({"level": 0, "xp": 0, "xp_needed": 10}) 
    except Exception as e:
        logging.error(f"Database error on get user progress: {e}")
        return jsonify({"error": "Could not fetch user progress"}), 500

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    # ... (KODE FUNGSI INI SAMA PERSIS SEPERTI SEBELUMNYA, TIDAK ADA PERUBAHAN)
    try:
        top_players = Player.select().order_by(Player.level.desc(), Player.xp.desc()).limit(10)
        leaderboard_data = [{"rank": i + 1, "first_name": p.first_name, "level": p.level} for i, p in enumerate(top_players)]
        return jsonify(leaderboard_data)
    except Exception as e:
        logging.error(f"Database error on get leaderboard: {e}")
        return jsonify({"error": "Could not fetch leaderboard"}), 500

@app.route('/api/webhook', methods=['POST'])
def webhook():
    return 'ok', 200
    
