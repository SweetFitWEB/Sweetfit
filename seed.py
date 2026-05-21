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

# 4. Proveedores — orden real: ID_PROVEEDOR, EMAIL, TELEFONO, NOMBRE, CONTRASEÑA
provs = [
    (1, 'info@panaderialasbrisas.com', '2291112233', 'Panadería Las Brisas',  generate_password_hash('12345')),
    (2, 'ventas@carnesselectas.com',   '2292223344', 'Carnes Selectas S.A.',  generate_password_hash('12345')),
    (3, 'pedidos@lacteos.com',        '2293334455', 'Distribuidora Lácteos', generate_password_hash('12345')),
]
c.executemany("INSERT INTO proveedor (ID_PROVEEDOR,EMAIL,TELEFONO,NOMBRE,CONTRASEÑA) VALUES (%s,%s,%s,%s,%s)", provs)

# 5. Productos — orden real: ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION
prods = [
    (1,  'Sweet Burger',    'Hamburguesa artesanal con pan brioche, carne angus, lechuga, tomate y cebolla caramelizada', 'Hamburguesas', 20, 89.00, 'sweetfit.png', 'APROBADO'),
    (2,  'Chicken Fit',     'Pechuga de pollo empanizada con queso suizo y pepinillos',                                  'Hamburguesas', 15, 79.00, 'sweetfit.png', 'APROBADO'),
    (3,  'Hot Dog Clásico', 'Salchicha de pavo con pan artesanal, cebolla crujiente y salsas',                           'Hot Dogs',     25, 49.00, 'sweetfit.png', 'APROBADO'),
    (4,  'Dog Especial',    'Hot Dog con queso cheddar, tiras de bacon y jalapeño',                                      'Hot Dogs',     20, 59.00, 'sweetfit.png', 'APROBADO'),
    (5,  'Brownie Fit',     'Brownie de chocolate amargo sin azúcar, con nueces',                                        'Postres',      10, 39.00, 'sweetfit.png', 'APROBADO'),
    (6,  'Smoothie Verde',  'Espinaca, piña, manzana y jengibre',                                                        'Bebidas',      30, 45.00, 'sweetfit.png', 'APROBADO'),
    (7,  'Limonada Natural', 'Limonada fresca con hierbabuena',                                                          'Bebidas',      40, 29.00, 'sweetfit.png', 'APROBADO'),
    (8,  'Papas rústicas',  'Papas horneadas con romero y sal de mar',                                                   'Papas',        50, 35.00, 'sweetfit.png', 'APROBADO'),
    (9,  'Sweet Shake',     'Malteada de vainilla con proteína vegetal',                                                  'Bebidas',      12, 55.00, 'sweetfit.png', 'APROBADO'),
    (10, 'Pan Hamburguesa Artesanal (Propuesta)', 'Pan brioche artesanal horneado por Panadería Las Brisas', 'Hamburguesas', 100, 15.00, 'deleite.png', 'PENDIENTE'),
    (11, 'Carne Angus Premium (Propuesta)',        'Corte angus importado para hamburguesas gourmet',       'Hamburguesas', 50,  45.00, 'pinchesHamburguesas.png', 'PENDIENTE'),
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

# 9. Detalle ventas — orden real: ID_DETVENTA, SUBTOTAL_VENTA, CANTIDAD_VENTA, ID_VENTA, ID_PRODUCTO
dvs = [
    (1, 89.00, 1, 1, 1),
    (2, 89.00, 1, 1, 2),
    (3, 89.00, 1, 2, 1),
    (4, 89.00, 1, 3, 1),
    (5, 39.00, 1, 3, 5),
    (6, 49.00, 1, 4, 3),
    (7, 89.00, 1, 5, 1),
    (8, 35.00, 1, 5, 8),
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
    (1, 150.00, 10, 1, 1),
    (2, 165.00, 10, 3, 1),
    (3, 200.00, 10, 5, 1),
    (4, 450.00, 10, 2, 2),
]
c.executemany("INSERT INTO detalle_compra (ID_DETCOMPRA,SUBTOTAL_COMPRA,CANTIDAD_COMPRA,ID_PRODUCTO,ID_COMPRA) VALUES (%s,%s,%s,%s,%s)", dcs)

# 12. Ajustar stock por ventas y compras
c.execute("UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO IN (1,2,3,5,8)")
c.execute("UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO IN (1,3,5,2)")

db.commit()
c.close()
db.close()
print("Seed completado.")
print()
print("Credenciales:")
print("  Admin:   admin@sweetfit.com / admin123")
print("  Cajero:  cajero@sweetfit.com / cajero123")
print("  Proveedor: info@panaderialasbrisas.com / 12345")
