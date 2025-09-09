import os
import logging
import json
import random
from flask import Flask, request, jsonify
from telegram import Update, Bot
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    IntegerField,
    DateTimeField,
    fn,
)
import datetime

# --- Konfigurasi & Inisialisasi ---
app = Flask(__name__)
BOT_TOKEN = os.environ.get("8264701988:AAH5x9q03FR9Em6RSXOPC_ZEjWiIhD9wcXo")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Pengaturan Database (SQLite) ---
# Vercel hanya punya direktori /tmp yang bisa ditulis
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

# Buat tabel jika belum ada
db.connect()
db.create_tables([Score], safe=True)
db.close()

# --- Endpoint API ---

@app.route("/api/questions", methods=["GET"])
def get_questions():
    """Mengacak soal, mengambil 5, dan mengirimkannya."""
    try:
        with open("api/soal.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
        
        # Acak urutan soal
        random.shuffle(questions)
        
        # Ambil hanya 5 soal pertama
        limited_questions = questions[:5]
        
        return jsonify(limited_questions)
    except Exception as e:
        logging.error(f"Error reading/processing questions file: {e}")
        return jsonify({"error": "Could not load questions"}), 500

@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    """Menerima dan menyimpan skor dari user."""
    data = request.json
    if not all(k in data for k in ["user", "score"]):
        return jsonify({"error": "Missing user data or score"}), 400

    user_data = data["user"]
    user_score = data["score"]

    try:
        db.connect(reuse_if_open=True)
        # Cari user, jika tidak ada, buat baru. Jika ada, update.
        player, created = Score.get_or_create(
            user_id=user_data["id"],
            defaults={
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name"),
                "username": user_data.get("username"),
                "score": user_score,
            },
        )

        # Jika user sudah ada dan skor baru lebih tinggi, update
        if not created and user_score > player.score:
            player.score = user_score
            player.updated_at = datetime.datetime.now()
            player.save()
        
        return jsonify({"status": "success", "message": "Score updated!"})
    except Exception as e:
        logging.error(f"Database error on submit score: {e}")
        return jsonify({"error": "Could not save score"}), 500
    finally:
        if not db.is_closed():
            db.close()


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Mengambil 10 skor tertinggi dari database."""
    try:
        db.connect(reuse_if_open=True)
        top_scores = (
            Score.select()
            .order_by(Score.score.desc(), Score.updated_at.asc())
            .limit(10)
        )
        
        leaderboard_data = [
            {
                "rank": i + 1,
                "first_name": score.first_name,
                "score": score.score,
            }
            for i, score in enumerate(top_scores)
        ]
        return jsonify(leaderboard_data)
    except Exception as e:
        logging.error(f"Database error on get leaderboard: {e}")
        return jsonify({"error": "Could not fetch leaderboard"}), 500
    finally:
        if not db.is_closed():
            db.close()

# Endpoint webhook tidak perlu diubah, biarkan seperti sebelumnya
@app.route('/api/webhook', methods=['POST'])
def webhook():
    return 'ok', 200

