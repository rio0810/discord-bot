import mysql.connector
import os

class EconomyBase:
    def __init__(self):
        # 環境変数から読み込む（設定がない場合はデフォルト値）
        self.db_config = {
            'host': os.getenv('DB_HOST', 'db'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'user'),
            'password': os.getenv('DB_PASS', 'password'),
            'database': os.getenv('DB_NAME', 'economy_db'),
            # Aivenなどの外部接続用（SSLを要求される場合）
            'ssl_disabled': False 
        }

    def get_db(self):
        # 外部DB（Aiven）接続時はタイムアウトを防ぐためコネクションをその都度作成
        return mysql.connector.connect(**self.db_config)

    def update_balance_logic(self, user_id, amount):
        conn = self.get_db()
        cur = conn.cursor()
        sql = """
        INSERT INTO users (user_id, balance) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE balance = balance + %s
        """
        cur.execute(sql, (user_id, amount, amount))
        conn.commit()
        cur.close()
        conn.close()

    def get_balance_logic(self, user_id):
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else 0
