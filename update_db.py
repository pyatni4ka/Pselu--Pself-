import sqlite3

def update_database():
    try:
        conn = sqlite3.connect('mgtu_app.db')
        cursor = conn.cursor()
        
        # Добавляем новую колонку
        cursor.execute('ALTER TABLE questions ADD COLUMN question_number TEXT')
        
        # Заполняем значения по умолчанию
        cursor.execute('UPDATE questions SET question_number = "1"')
        
        conn.commit()
        print("База данных успешно обновлена!")
        
    except sqlite3.Error as e:
        print(f"Ошибка при обновлении базы данных: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_database()
