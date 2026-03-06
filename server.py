from flask import Flask, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)
DB = "messages.db"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        webhook_id TEXT UNIQUE,
        phone TEXT,
        message TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
    """)
    c.commit()
    c.close()

@app.route("/")
def home():
    return "WhatsApp server running"

@app.route("/messages")
def get_messages():
    status = request.args.get("status","pending")
    c = db()
    rows = c.execute(
        "SELECT webhook_id, phone, message, created_at FROM messages WHERE status=? LIMIT 20",
        (status,)
    ).fetchall()
    c.close()
    return jsonify({messages": [dict(r) for r in rows]})

@app.route("/messages/<webhook_id>/done", methods=["POST"])
def mark_done(webhook_id):
    c = db()
    c.execute("UPDATE messages SET status='done' WHERE webhook_id=?", (webhook_id,))
    c.commit()
    c.close()
    return jsonify({"ok": True})

VERIFY_TOKEN = "hal_token_123"

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return "verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return "ok"

        msg = value["messages"][0]

        webhook_id = msg["id"]
        phone = msg["from"]
        text = msg["text"]["body"]

        c = db()
        c.execute(
            "INSERT OR IGNORE INTO messages(webhook_id,phone,message,created_at) VALUES(?,?,?,?)",
            (
                webhook_id,
                phone,
                text,
                datetime.datetime.utcnow().isoformat()
            )
        )
        c.commit()
        c.close()

    except Exception as e:
        print("webhook error:", e)

    return "ok"

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
