import mysql.connector
from werkzeug.security import generate_password_hash

db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'sweetfit'
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)

for table, id_col in [('empleado', 'ID_EMPLEADO'), ('proveedor', 'ID_PROVEEDOR')]:
    cursor.execute(f"SELECT {id_col}, CONTRASEÑA FROM {table}")
    rows = cursor.fetchall()
    for row in rows:
        pwd = row['CONTRASEÑA']
        if pwd and not (pwd.startswith('pbkdf2:') or pwd.startswith('scrypt:') or pwd.startswith('$2')):
            hashed = generate_password_hash(pwd)
            cursor.execute(f"UPDATE {table} SET CONTRASEÑA = %s WHERE {id_col} = %s", (hashed, row[id_col]))
            print(f"  {table} {id_col}={row[id_col]}: hasheada")

conn.commit()
cursor.close()
conn.close()
print("Migracion completada.")
