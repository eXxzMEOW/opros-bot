import sqlite3
from datetime import datetime
import json


class Database:
    def __init__(self, db_name='tests.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица результатов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                test_id TEXT,
                score INTEGER,
                total INTEGER,
                percentage REAL,
                answers TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        self.conn.commit()

    def add_user(self, user_id, username):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        ''', (user_id, username))
        self.conn.commit()

    def save_result(self, user_id, test_id, score, total, answers):
        percentage = round(score / total * 100, 2) if total > 0 else 0

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO results (user_id, test_id, score, total, percentage, answers)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, test_id, score, total, percentage, json.dumps(answers)))
        self.conn.commit()

    def get_user_results(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT test_id, score, total, percentage, date
            FROM results
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 10
        ''', (user_id,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'test_id': row[0],
                'score': row[1],
                'total': row[2],
                'percentage': row[3],
                'date': row[4]
            })

        return results