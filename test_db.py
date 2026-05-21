import mysql.connector

db_config = {'host':'localhost','port':3306,'user':'root','password':'','database':'sweetfit'}
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
tablas = [r[0] for r in cursor.fetchall()]

for tabla in tablas:
    print(f"\n{'='*40}")
    print(f"TABLA: {tabla}")
    print('='*40)
    cursor.execute(f"DESCRIBE {tabla}")
    for col in cursor.fetchall():
        print(f"  {col[0]:30} {col[1]:25} NULL:{col[2]:3}  KEY:{col[3]:4}  DEFAULT:{col[4]}")

cursor.close()
conn.close()
