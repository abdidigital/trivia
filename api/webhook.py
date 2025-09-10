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

app = Flask(__name__)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

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
    lives = IntegerField(default=3) # Kolom baru untuk nyawa
    updated_at = DateTimeField(default=datetime.datetime.now)
    class Meta:
        database = db

class AnsweredQuestion(BaseModel):
    player = ForeignKeyField(Player, backref='questions')
    question_hash = CharField(index=True)

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

@app.route("/api/get_question_batch", methods=["GET"])
def get_question_batch():
    # ... (Fungsi ini tidak berubah dari versi soal.json terakhir)
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "user_id is required"}), 400
    try:
        with open("api/soal.json", "r", encoding="utf-8") as f:
            all_questions = json.load(f)
        random.shuffle(all_questions)
        player = Player.get_or_none(Player.user_id == user_id)
        answered_hashes = set()
        if player:
            query = AnsweredQuestion.select(AnsweredQuestion.question_hash).where(AnsweredQuestion.player == player)
            answered_hashes = {q.question_hash for q in query}
        unique_questions = [q for q in all_questions if hashlib.sha256(q.get("pertanyaan", "").encode()).hexdigest() not in answered_hashes]
        return jsonify(unique_questions[:10])
    except Exception as e:
        return jsonify({"error": f"Error di backend: {str(e)}"}), 500

@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    data = request.json
    try:
        user_data = data["user"]
        correct_answer_increment = data["score"]
        question_text = data.get("question")
        
        player, created = Player.get_or_create(user_id=user_data["id"], defaults={"first_name": user_data.get("first_name", "Unknown")})
        
        if question_text:
            question_hash = hashlib.sha256(question_text.encode()).hexdigest()
            AnsweredQuestion.get_or_create(player=player, question_hash=question_hash)

        # Kurangi nyawa jika jawaban salah
        if correct_answer_increment == 0 and player.lives > 0:
            player.lives -= 1

        player.xp += correct_answer_increment
        level_up_occurred = False
        xp_needed = 10 + (player.level * 5)
        if player.xp >= xp_needed:
            player.level += 1
            player.xp -= xp_needed
            level_up_occurred = True
        player.save()
        
        return jsonify({"status": "success", "level": player.level, "xp": player.xp, "xp_needed": 10 + (player.level * 5), "level_up": level_up_occurred, "lives": player.lives})
    except Exception as e:
        return jsonify({"error": "Could not save score"}), 500

@app.route("/api/get_user_progress", methods=["GET"])
def get_user_progress():
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({"error": "user_id is required"}), 400
    try:
        player, created = Player.get_or_create(user_id=user_id, defaults={"first_name": "Player"})
        xp_needed = 10 + (player.level * 5)
        return jsonify({"level": player.level, "xp": player.xp, "xp_needed": xp_needed, "lives": player.lives})
    except Exception as e:
        return jsonify({"error": "Could not fetch user progress"}), 500

@app.route("/api/add_life", methods=["POST"])
def add_life():
    """Endpoint untuk menambah 1 nyawa setelah menonton iklan."""
    data = request.json
    user_id = data.get("user", {}).get("id")
    if not user_id: return jsonify({"error": "user_id is required"}), 400
    try:
        player = Player.get_or_none(Player.user_id == user_id)
        if player:
            player.lives += 1
            player.save()
            return jsonify({"status": "success", "lives": player.lives})
        else:
            return jsonify({"error": "Player not found"}), 404
    except Exception as e:
        return jsonify({"error": "Could not add life"}), 500
        
@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    # ... (Fungsi ini tidak berubah)
    try:
        top_players = Player.select().order_by(Player.level.desc(), Player.xp.desc()).limit(10)
        leaderboard_data = [{"rank": i + 1, "first_name": p.first_name, "level": p.level} for i, p in enumerate(top_players)]
        return jsonify(leaderboard_data)
    except Exception as e:
        return jsonify({"error": "Could not fetch leaderboard"}), 500

@app.route('/api/webhook', methods=['POST'])
def webhook():
    return 'ok', 200
        
