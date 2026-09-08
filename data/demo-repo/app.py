import logging
import os
import sqlite3
import threading
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"), maxBytes=5_000_000, backupCount=3
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s [%(name)s] %(message)s"
))
logging.basicConfig(level=logging.INFO, handlers=[handler])

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "demo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def seed_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, item TEXT, qty INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")
    if conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO orders (item, qty) VALUES (?, ?)",
            [("widget", 3), ("gadget", 1), ("gizmo", 7)],
        )
    if conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO items (name) VALUES (?)",
            [(f"item-{i}",) for i in range(25)],
        )
    conn.commit()
    conn.close()


seed_db()


# --- Orders ---
log_orders = logging.getLogger("orders")


@app.get("/orders/<order_id>")
def get_order(order_id):
    conn = get_db()
    query = f"SELECT * FROM orders WHERE id = {order_id}"
    try:
        row = conn.execute(query).fetchone()
    except sqlite3.OperationalError:
        log_orders.error("Failed to fetch order %s", order_id, exc_info=True)
        return jsonify({"error": "invalid order id"}), 400
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


# --- Users ---
log_users = logging.getLogger("users")
_users = []


@app.post("/users")
def create_user():
    body = request.get_json(force=True, silent=True) or {}
    try:
        email = body["email"]
    except KeyError:
        log_users.error("Missing required field while creating user: %s", body, exc_info=True)
        return jsonify({"error": "email is required"}), 400
    _users.append({"email": email})
    return jsonify({"email": email}), 201


# --- Items (paginated) ---
log_items = logging.getLogger("items")
PAGE_SIZE = 10


@app.get("/items/page/<int:page>")
def get_items_page(page):
    conn = get_db()
    rows = conn.execute("SELECT * FROM items ORDER BY id").fetchall()
    conn.close()
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    try:
        chunk = [dict(rows[i]) for i in range(start, end + 1)]
    except IndexError:
        log_items.error("Pagination out of range for page %s (have %d items)", page, len(rows), exc_info=True)
        return jsonify({"error": "page out of range"}), 400
    return jsonify(chunk)


# --- Counter ---
log_counter = logging.getLogger("counter")
_counter = {"value": 0}
_counter_lock = threading.Lock()


@app.post("/counter/increment")
def increment_counter():
    with _counter_lock:
        _counter["value"] += 1
        value = _counter["value"]
    return jsonify({"value": value})


@app.get("/counter/check")
def check_counter():
    expected = request.args.get("expected", type=int)
    actual = _counter["value"]
    if expected is not None and actual != expected:
        log_counter.error(
            "Counter mismatch: expected %d, got %d",
            expected, actual,
        )
        return jsonify({"expected": expected, "actual": actual, "mismatch": True}), 200
    return jsonify({"actual": actual, "mismatch": False})


# --- Reports ---
log_reports = logging.getLogger("reports")


@app.get("/reports/summary")
def reports_summary():
    conn = get_db()
    rows = conn.execute(
        "SELECT orders.id AS order_id, items.id AS item_id, items.name AS item_name "
        "FROM orders LEFT JOIN items ON items.id = orders.id"
    ).fetchall()
    conn.close()
    summary = [
        {
            "order_id": row["order_id"],
            "item": {"id": row["item_id"], "name": row["item_name"]} if row["item_id"] is not None else None,
        }
        for row in rows
    ]
    return jsonify(summary)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5001, threaded=True)
