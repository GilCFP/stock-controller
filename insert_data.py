import sqlite3
conn = sqlite3.connect('estoque.db')
db = conn.cursor()

for i in range (0,5):
    db.execute("INSERT INTO tec(name,  value, damage) VALUES ('teste',10.50,'Não')")
conn.commit()
conn.close()