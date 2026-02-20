from flask import Flask, request, jsonify, render_template_string
import mysql.connector
import os
import time

app = Flask(__name__)

# DB設定
db_config = {
    'host': os.environ.get('DB_HOST', 'db'),
    'user': os.environ.get('DB_USER', 'tracker_user'),
    'password': os.environ.get('DB_PASSWORD', 'tracker_pass'),
    'database': os.environ.get('DB_NAME', 'tracker_logs')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            site_id VARCHAR(50),
            user_id VARCHAR(50),
            element_id VARCHAR(100),
            ip_address VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# 初回起動時にテーブル作成を試みる（簡易的実装）
time.sleep(5) # DB起動待ち
try:
    init_db()
    print("Database initialized.")
except Exception as e:
    print(f"DB Init Error: {e}")

# --- API ---
@app.route('/api/track', methods=['POST'])
def track():
    data = request.json
    # Nginx経由の場合、X-Forwarded-ForにIPが入る
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO logs (site_id, user_id, element_id, ip_address) VALUES (%s, %s, %s, %s)',
        (data.get('site_id'), data.get('user_id'), data.get('element_id'), ip)
    )
    conn.commit()
    cursor.close()
    conn.close()
    
    # CORS対応: プリフライトはNginxで処理するが、ここでもヘッダを返すと安全
    response = jsonify({'status': 'success'})
    return response

# --- 管理画面 (簡易HTML) ---
@app.route('/admin')
def admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 最新50件を取得
    cursor.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT 50')
    logs = cursor.fetchall()
    
    # サイトごとの集計
    cursor.execute('SELECT site_id, COUNT(*) as count FROM logs GROUP BY site_id')
    stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head><title>Simple Tracker Admin</title>
    <style>body{font-family:sans-serif; padding:20px;} table{border-collapse:collapse; width:100%;} th,td{border:1px solid #ddd; padding:8px;} th{background-color:#f2f2f2;}</style>
    </head>
    <body>
        <h1>📊 ユーザー行動ログ管理画面</h1>
        
        <h2>サイト別集計</h2>
        <ul>
        {% for s in stats %}
            <li><b>{{ s.site_id }}</b>: {{ s.count }} clicks</li>
        {% endfor %}
        </ul>

        <h2>最新ログ (Top 50)</h2>
        <table>
            <tr><th>ID</th><th>Time</th><th>Site ID</th><th>User ID</th><th>Element ID</th><th>IP</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.id }}</td>
                <td>{{ log.created_at }}</td>
                <td>{{ log.site_id }}</td>
                <td>{{ log.user_id }}</td>
                <td>{{ log.element_id }}</td>
                <td>{{ log.ip_address }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, logs=logs, stats=stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
