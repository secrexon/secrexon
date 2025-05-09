from flask import Flask, request, jsonify
import sqlite3
import asyncio
from bot import (
    verify_init_data, process_query_with_query,
    process_query_no_report, process_fio_query, client
)
import json
import urllib.parse

app = Flask(__name__)

# Path to users.db
DB_PATH = "users.db"

# Bot token for verifying init data
SECRET_KEY = "7641976092:AAFUp_piifBNoC40LPaONmK_u8f5qOMBu3w"  # Replace with your bot token

# Ensure Telethon client is connected
async def ensure_client_connected():
    if not client.is_connected():
        await client.connect()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/search', methods=['POST'])
async def search():
    data = request.get_json()
    init_data = data.get('initData')
    query = data.get('query')
    search_type = data.get('search_type')

    # Verify init data
    if not verify_init_data(init_data, SECRET_KEY):
        return jsonify({"error": "Invalid init data"}), 403

    if not query or not search_type:
        return jsonify({"error": "Query or search type missing"}), 400

    # Ensure Telethon client is connected
    await ensure_client_connected()

    try:
        if search_type == "phone":
            result = await process_query_with_query(query)
        elif search_type == "email":
            result = await process_query_no_report(query)
        elif search_type == "fio":
            result = await process_fio_query(query)
        else:
            return jsonify({"error": "Unsupported search type"}), 400

        # Parse result into structured format
        if isinstance(result, dict) and "report" in result:
            formatted_results = [
                {"key": key, "value": value}
                for key, value in result["report"].items()
            ]
        elif isinstance(result, list):
            formatted_results = [
                {"key": f"Result {i+1}", "value": str(item)}
                for i, item in enumerate(result)
            ]
        else:
            formatted_results = [{"key": "Result", "value": str(result)}]

        return jsonify({"results": formatted_results})
    except Exception as e:
        return jsonify({"error": f"Search error: {str(e)}"}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    init_data = request.args.get('initData')
    if not verify_init_data(init_data, SECRET_KEY):
        return jsonify({"error": "Invalid init data"}), 403

    # Check if user is admin (ID 5866737498)
    user_id = extract_user_id(init_data)
    if user_id != 5866737498:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, status FROM users")
        users = [{"user_id": row["user_id"], "username": row["username"], "status": row["status"]} for row in cursor.fetchall()]
        conn.close()
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/admin/update_user', methods=['POST'])
def update_user():
    data = request.get_json()
    init_data = data.get('initData')
    user_id = data.get('user_id')
    status = data.get('status')

    if not verify_init_data(init_data, SECRET_KEY):
        return jsonify({"error": "Invalid init data"}), 403

    # Check if user is admin
    admin_id = extract_user_id(init_data)
    if admin_id != 5866737498:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

def extract_user_id(init_data):
    try:
        parsed = urllib.parse.parse_qs(init_data)
        user_data = parsed.get('user', [''])[0]
        user = json.loads(urllib.parse.unquote(user_data))
        return user.get('id')
    except:
        return None

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.start())
    app.run(host='0.0.0.0', port=port)