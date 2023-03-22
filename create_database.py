import sqlite3

conn = sqlite3.connect('estoque.db')

db = conn.cursor()
db.execute("""CREATE TABLE user(
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT)
        """)
conn.close()