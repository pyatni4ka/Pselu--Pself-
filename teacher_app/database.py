import sqlite3
import os
from sqlite3 import Error

# Get the absolute path to the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_DIR, "database")
DB_FILE = os.path.join(DB_FOLDER, "mgtu_app.db")

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn

def initialize_db():
    # Ensure the database folder exists
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
        print(f"Folder '{DB_FOLDER}' created.")

    conn = create_connection(DB_FILE)
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS lab_works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                time INTEGER NOT NULL,
                question_count INTEGER NOT NULL
            );""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lab_id INTEGER,
                category TEXT CHECK(category IN ('теория', 'практика', 'графики')),
                question_text TEXT,
                answer1 TEXT,
                answer2 TEXT,
                answer3 TEXT,
                answer4 TEXT,
                correct_index INTEGER,
                FOREIGN KEY (lab_id) REFERENCES lab_works (id)
            );""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                middle_name TEXT,
                group_name TEXT NOT NULL,
                year INTEGER
            );""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                lab_id INTEGER,
                score INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (lab_id) REFERENCES lab_works (id)
            );""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                student_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students (id)
            );""")
        conn.commit()
        conn.close()
        print(f"Database initialized at '{DB_FILE}'.")
    else:
        print("Ошибка! Не удалось создать соединение с базой данных.")

if __name__ == "__main__":
    initialize_db()
