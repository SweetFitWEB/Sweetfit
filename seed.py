import mysql.connector
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

db = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='sweetfit')
c = db.cursor()

# 1. Fix column size for hashes
c.execute("ALTER TABLE empleado MODIFY CONTRASEÑA VARCHAR(255)")

# 2. Clean existing data
for t in ('detalle_compra','detalle_venta','compra','venta','producto_proveedor','producto','proveedor','cliente','empleado'):
    c.execute(f"DELETE FROM {t}")

# 3. Empleados
emps = [
    (1, 'Admin',  'Sweetfit', 'admin@sweetfit.com',  generate_password_hash('admin123'),  'Administrador'),
    (2, 'Cajero', 'Sweetfit', 'cajero@sweetfit.com', generate_password_hash('cajero123'), 'Cajero'),
]
c.executemany("INSERT INTO empleado (ID_EMPLEADO,NOMBRE,APELLIDOS,EMAIL,CONTRASEÑA,PUESTO) VALUES (%s,%s,%s,%s,%s,%s)", emps)

# 4. Proveedores
provs = [
    (1, 'contacto@greenfields.com',     '2291112233', 'Green Fields Orgánicos', generate_password_hash('12345')),
    (2, 'ventas@fitprotein.com',        '2292223344', 'Fit Protein Supply',     generate_password_hash('12345')),
    (3, 'pedidos@vitalJuice.com',       '2293334455', 'Vital Juice Co.',        generate_password_hash('12345')),
]
c.executemany("INSERT INTO proveedor (ID_PROVEEDOR,EMAIL,TELEFONO,NOMBRE,CONTRASEÑA) VALUES (%s,%s,%s,%s,%s)", provs)

# 5. Productos fit
prods = [
    (1,  'Ensalada Caesar Fit',   'Lechuga romana, pollo grillé, crutones integrales, aderezo light',     'Ensaladas',        25, 79.00, 'aderezo.jpg', 'APROBADO'),
    (2,  'Bowl Verde',            'Quinoa, espinaca, aguacate, pepino, brócoli y vinagreta de limón',      'Bowls',            20, 89.00, 'aguacate.jpg', 'APROBADO'),
    (3,  'Pechuga Empanizada',    'Pechuga de pollo empanizada con avena, horneada no frita',               'Proteína',         30, 79.00, 'pechuga.jpg', 'APROBADO'),
    (4,  'Salmón a la Plancha',   'Filete de salmón fresco con especias y vegetales salteados',             'Proteína',         15, 119.00, 'atun.jpg', 'APROBADO'),
    (5,  'Barrita Proteica',      'Barrita de proteína vegetal, sin azúcar añadida',                        'Snacks Fit',       50, 29.00, 'barritas_proteicas.jpg', 'APROBADO'),
    (6,  'Green Smoothie',        'Espinaca, piña, manzana verde y jengibre',                                'Jugos y Licuados', 30, 55.00, 'Extra_Naranja.jpg', 'APROBADO'),
    (7,  'Limonada con Chía',     'Limonada natural con semillas de chía y stevia',                         'Bebidas',          40, 35.00, 'naranja_miel.jpg', 'APROBADO'),
    (8,  'Palomitas de Aire',     'Palomitas de maíz sin aceite, con sal de mar y romero',                  'Snacks Fit',       50, 25.00, 'palomitas_aire.jpg', 'APROBADO'),
    (9,  'Protein Shake',         'Licuado de proteína vegetal, plátano y leche de almendras',              'Jugos y Licuados', 20, 65.00, 'leche_coco.jpg', 'APROBADO'),
    (10, 'Ensalada de Atún (Propuesta)', 'Ensalada de atún fresco con mezcla de verdes, pepino y jitomate cherry', 'Ensaladas', 40, 45.00, 'Deli_Tuna_CH.jpg', 'PENDIENTE'),
    (11, 'Pack Protein Bars (Propuesta)', 'Pack 12 barritas proteicas sabor chocolate y vainilla',          'Snacks Fit',       60, 25.00, 'barritas_proteicas.jpg', 'PENDIENTE'),
]
c.executemany("INSERT INTO producto (ID_PRODUCTO,NOMBRE,DESCRIPCION,CATEGORIA,CANTIDAD,PRECIO,IMAGEN,ESTADO_APROBACION) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", prods)

# 6. Vincular productos pendientes con proveedores
c.executemany("INSERT INTO producto_proveedor (ID_PRODUCTO,ID_PROVEEDOR) VALUES (%s,%s)", [(10,1), (11,2)])

# 7. Clientes — orden real: ID_CLIENTE, NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, DIRECCION, TELEFONO
clientes = [
    (1, 'Juan',   'Pérez',   'García',   'Calle 1 #123, Centro',        '2291000100'),
    (2, 'María',  'López',   'Martínez', 'Av. 2 #456, Reforma',         '2291000200'),
    (3, 'Carlos', 'Ramírez', None,       'Blvd. 3 #789, Costa de Oro',  '2291000300'),
]
c.executemany("INSERT INTO cliente (ID_CLIENTE,NOMBRE,APELLIDO_PATERNO,APELLIDO_MATERNO,DIRECCION,TELEFONO) VALUES (%s,%s,%s,%s,%s,%s)", clientes)

# 8. Ventas — orden real: ID_VENTA, ID_CLIENTE, TIPO_VENTA, TOTAL_VENTA, FECHA_VENTA, ID_EMPLEADO, ESTADO
hoy = datetime.now()
ventas = [
    (1, 1, 'Local',     178.00, hoy - timedelta(days=1), 2, 'FINALIZADA'),
    (2, 2, 'Domicilio',  89.00, hoy,                     2, 'FINALIZADA'),
    (3, 3, 'Local',     128.00, hoy - timedelta(days=2), 2, 'EN ESPERA'),
    (4, 1, 'App',        49.00, hoy - timedelta(days=3), 1, 'CANCELADA'),
    (5, 2, 'Local',     124.00, hoy,                     1, 'FINALIZADA'),
]
c.executemany("INSERT INTO venta (ID_VENTA,ID_CLIENTE,TIPO_VENTA,TOTAL_VENTA,FECHA_VENTA,ID_EMPLEADO,ESTADO) VALUES (%s,%s,%s,%s,%s,%s,%s)", ventas)

# 9. Detalle ventas
dvs = [
    (1, 79.00, 1, 1, 1),
    (2, 89.00, 1, 1, 2),
    (3, 79.00, 1, 2, 3),
    (4, 89.00, 1, 3, 2),
    (5, 29.00, 1, 3, 5),
    (6, 55.00, 1, 4, 6),
    (7, 79.00, 1, 5, 1),
    (8, 25.00, 1, 5, 8),
]
c.executemany("INSERT INTO detalle_venta (ID_DETVENTA,SUBTOTAL_VENTA,CANTIDAD_VENTA,ID_VENTA,ID_PRODUCTO) VALUES (%s,%s,%s,%s,%s)", dvs)

# 10. Compras — orden real: ID_COMPRA, FECHA_COMPRA, TOTAL_COMPRA, ID_EMPLEADO, ID_PROVEEDOR
compras = [
    (1, hoy - timedelta(days=5), 315.00, 1, 1),
    (2, hoy - timedelta(days=2), 450.00, 1, 2),
]
c.executemany("INSERT INTO compra (ID_COMPRA,FECHA_COMPRA,TOTAL_COMPRA,ID_EMPLEADO,ID_PROVEEDOR) VALUES (%s,%s,%s,%s,%s)", compras)

# 11. Detalle compras — orden real: ID_DETCOMPRA, SUBTOTAL_COMPRA, CANTIDAD_COMPRA, ID_PRODUCTO, ID_COMPRA
dcs = [
    (1, 450.00, 10, 1, 1),
    (2, 350.00, 10, 6, 1),
    (3, 250.00, 10, 5, 1),
    (4, 790.00, 10, 3, 2),
]
c.executemany("INSERT INTO detalle_compra (ID_DETCOMPRA,SUBTOTAL_COMPRA,CANTIDAD_COMPRA,ID_PRODUCTO,ID_COMPRA) VALUES (%s,%s,%s,%s,%s)", dcs)

# 12. Ajustar stock por ventas y compras
c.execute("UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO IN (1,2,3,5,6,8)")
c.execute("UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO IN (1,3,5,6)")

db.commit()
c.close()
db.close()
print("Seed completado.")
print()
print("Credenciales:")
print("  Admin:   admin@sweetfit.com / admin123")
print("  Cajero:  cajero@sweetfit.com / cajero123")
print("  Proveedor: contacto@greenfields.com / 12345")
