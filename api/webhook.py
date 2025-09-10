import os
import logging
import json
import random
import google.generativeai as genai
from flask import Flask, request, jsonify

# --- Konfigurasi & Inisialisasi ---
app = Flask(__name__)
print("Flask App Initialized")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API Key Configured")
    except Exception as e:
        print(f"ERROR configuring Gemini: {e}")
else:
    print("ERROR: GEMINI_API_KEY environment variable not found!")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Endpoint API ---
@app.route("/api/get_question_batch", methods=["GET"])
def get_question_batch():
    print("\n--- Request received for /api/get_question_batch ---")
    try:
        level = int(request.args.get('level', 0))
        print(f"Level received: {level}")

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tidak ditemukan di environment.")

        TOPIK_KUIS = ["Sains dan Alam", "Sejarah Dunia", "Geografi", "Teknologi"]
        topik_acak = random.choice(TOPIK_KUIS)
        print(f"Random topic selected: {topik_acak}")

        prompt_kuis = f"""
        Buatkan 5 pertanyaan kuis pilihan ganda tentang topik "{topik_acak}".
        Level kesulitan: mudah. Bahasa: Indonesia.
        Format output HARUS berupa array JSON yang valid, tanpa teks atau penjelasan tambahan.
        """

        print("Generating content from Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_kuis)
        print("Response received from Gemini.")
        
        raw_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        print("Parsing JSON response...")
        questions = json.loads(raw_response)
        print("JSON parsed successfully. Sending response to frontend.")
        
        return jsonify(questions)
        
    except Exception as e:
        error_message = f"!!! CRITICAL ERROR in get_question_batch: {str(e)}"
        print(error_message)
        logging.error(error_message)
        return jsonify({"error": error_message}), 500

# Endpoint lain dibuat non-aktif sementara untuk debugging
@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    return jsonify({"status": "ok_debug"})

@app.route("/api/get_user_progress", methods=["GET"])
def get_user_progress():
    return jsonify({"level": 0, "xp": 0, "xp_needed": 10})

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    return jsonify([])

@app.route('/api/webhook', methods=['POST'])
def webhook():
    return 'ok', 200

