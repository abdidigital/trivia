import os
import logging
import json
import datetime
import random
import hashlib
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

# --- Pengelola Koneksi Database Otomatis ---
@app.before_request
def before_request():
    if not os.path.exists(db_path):
        db.connect()
        db.create_tables([Player, AnsweredQuestion], safe=True)
    else:
        db.connect(reuse_if_open=True)

@app.after_request
def after_request(response):
    if not db.is_closed():
        db.close()
    return response

# --- Endpoint API ---
@app.route("/api/get_question_batch", methods=["GET"])
def get_question_batch():
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "user_id is required"}), 400

    try:
        # Membaca soal dari file JSON lokal
        with open("api/soal.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)
        
        random.shuffle(all_questions) # Acak soal dari file
        
        player = Player.get_or_none(Player.user_id == user_id)
        
        answered_hashes = set()
        if player:
            query = AnsweredQuestion.select(AnsweredQuestion.question_hash).where(AnsweredQuestion.player == player)
            answered_hashes = {q.question_hash for q in query}
        
        unique_questions = []
        for q in all_questions:
            q_hash = hashlib.sha256(q.get("pertanyaan", "").encode()).hexdigest()
            if q_hash not in answered_hashes:
                unique_questions.append(q)
        
        # Kirim maksimal 10 soal unik per sesi
        return jsonify(unique_questions[:10])
        
    except Exception as e:
        error_message = f"Error di backend: {str(e)}"
        logging.error(error_message)
        return jsonify({"error": error_message}), 500

# Endpoint lainnya (submit_score, get_user_progress, leaderboard, webhook)
# Kode di bawah ini tidak perlu diubah sama sekali, sudah kompatibel.
@app.route("/api/submit_score", methods=["POST"])
def submit_score():
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
                  
