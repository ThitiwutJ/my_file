from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # Allow CORS for frontend

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    # This line ensures the URL starts with 'postgresql://' instead of 'postgres://'
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url)

# Initialize database
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            nickname VARCHAR(50) UNIQUE NOT NULL,
            streak INTEGER DEFAULT 0,
            last_active DATE
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/streak', methods=['GET'])
def get_streak():
    nickname = request.args.get('nickname')
    if not nickname:
        return jsonify({'error': 'nickname required'}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT streak FROM users WHERE nickname = %s", (nickname,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user:
        return jsonify({'streak': user['streak']})
    else:
        return jsonify({'streak': 0})

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    data = request.get_json()
    nickname = data.get('nickname')
    if not nickname:
        return jsonify({'error': 'nickname required'}), 400

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get current user data
    cur.execute("SELECT streak, last_active FROM users WHERE nickname = %s", (nickname,))
    user = cur.fetchone()

    if user:
        last_active = user['last_active']
        current_streak = user['streak']

        if last_active == yesterday:
            # Consecutive day, increment streak
            new_streak = current_streak + 1
        elif last_active == today:
            # Already started today, no change
            new_streak = current_streak
        else:
            # Break in streak, reset to 1
            new_streak = 1

        cur.execute("UPDATE users SET streak = %s, last_active = %s WHERE nickname = %s",
                    (new_streak, today, nickname))
    else:
        # New user, start with 1
        new_streak = 1
        cur.execute("INSERT INTO users (nickname, streak, last_active) VALUES (%s, %s, %s)",
                    (nickname, new_streak, today))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'streak': new_streak})

if __name__ == '__main__':
    # Grab Render's assigned port, or use 5000 if running on your laptop
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
