-- =========================================================
-- SWEETFIT - DATOS DE PRUEBA
-- =========================================================

-- 1. Ajustar columna CONTRASEÑA para soportar hashes bcrypt
ALTER TABLE empleado MODIFY CONTRASEÑA VARCHAR(255);

-- 2. Limpiar datos existentes (en orden por FK)
DELETE FROM detalle_compra;
DELETE FROM detalle_venta;
DELETE FROM compra;
DELETE FROM venta;
DELETE FROM producto_proveedor;
DELETE FROM producto;
DELETE FROM proveedor;
DELETE FROM cliente;
DELETE FROM empleado;

-- 3. EMPLEADOS (pass: admin123 / cajero123)
INSERT INTO empleado (ID_EMPLEADO, NOMBRE, APELLIDOS, EMAIL, CONTRASEÑA, PUESTO) VALUES
(1, 'Admin', 'Sweetfit', 'admin@sweetfit.com', 'pbkdf2:sha256:600000$salt_admin$hash_admin_placeholder', 'Administrador'),
(2, 'Cajero', 'Sweetfit', 'cajero@sweetfit.com', 'pbkdf2:sha256:600000$salt_cajero$hash_cajero_placeholder', 'Cajero');

-- 4. PROVEEDORES (pass: 12345)
INSERT INTO proveedor (ID_PROVEEDOR, NOMBRE, EMAIL, TELEFONO, CONTRASEÑA) VALUES
(1, 'Panadería Las Brisas',   'info@panaderialasbrisas.com', '2291112233', 'pbkdf2:sha256:600000$prov1$hash_prov1'),
(2, 'Carnes Selectas S.A.',   'ventas@carnesselectas.com',   '2292223344', 'pbkdf2:sha256:600000$prov2$hash_prov2'),
(3, 'Distribuidora Lácteos',  'pedidos@lacteos.com',        '2293334455', 'pbkdf2:sha256:600000$prov3$hash_prov3');

-- 5. PRODUCTOS (aprobados)
INSERT INTO producto (ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION) VALUES
(1, 'Sweet Burger',      'Hamburguesa artesanal con pan brioche, carne angus, lechuga, tomate y cebolla caramelizada', 'Hamburguesas', 20, 89.00, 'sweetfit.png', 'APROBADO'),
(2, 'Chicken Fit',       'Pechuga de pollo empanizada con queso suizo y pepinillos',                              'Hamburguesas', 15, 79.00, 'sweetfit.png', 'APROBADO'),
(3, 'Hot Dog Clásico',   'Salchicha de pavo con pan artesanal, cebolla crujiente y salsas',                        'Hot Dogs',     25, 49.00, 'sweetfit.png', 'APROBADO'),
(4, 'Dog Especial',      'Hot Dog con queso cheddar, tiras de bacon y jalapeño',                                   'Hot Dogs',     20, 59.00, 'sweetfit.png', 'APROBADO'),
(5, 'Brownie Fit',       'Brownie de chocolate amargo sin azúcar, con nueces',                                     'Postres',      10, 39.00, 'sweetfit.png', 'APROBADO'),
(6, 'Smoothie Verde',    'Espinaca, piña, manzana y jengibre',                                                      'Bebidas',      30, 45.00, 'sweetfit.png', 'APROBADO'),
(7, 'Limonada Natural',  'Limonada fresca con hierbabuena',                                                         'Bebidas',      40, 29.00, 'sweetfit.png', 'APROBADO'),
(8, 'Papas rústicas',    'Papas horneadas con romero y sal de mar',                                                 'Papas',        50, 35.00, 'sweetfit.png', 'APROBADO'),
(9, 'Sweet Shake',       'Malteada de vainilla con proteína vegetal',                                               'Bebidas',      12, 55.00, 'sweetfit.png', 'APROBADO');

-- 6. PRODUCTOS PENDIENTES (ofertas de proveedores)
INSERT INTO producto (ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION) VALUES
(10, 'Pan de Hamburguesa Artesanal (Propuesta)', 'Pan brioche artesanal horneado por Panadería Las Brisas', 'Hamburguesas', 100, 15.00, 'deleite.png', 'PENDIENTE'),
(11, 'Carne Angus Premium (Propuesta)', 'Corte angus importado para hamburguesas gourmet', 'Hamburguesas', 50, 45.00, 'pinchesHamburguesas.png', 'PENDIENTE');

-- 7. VINCULAR PRODUCTOS CON PROVEEDORES
INSERT INTO producto_proveedor (ID_PRODUCTO, ID_PROVEEDOR) VALUES
(10, 1),
(11, 2);

-- 8. CLIENTES
INSERT INTO cliente (ID_CLIENTE, NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, DIRECCION, TELEFONO) VALUES
(1, 'Juan',    'Pérez',   'García', 'Calle 1 #123, Centro',          '2291000100'),
(2, 'María',   'López',   'Martínez', 'Av. 2 #456, Reforma',         '2291000200'),
(3, 'Carlos',  'Ramírez', NULL, 'Blvd. 3 #789, Costa de Oro',       '2291000300');

-- 9. VENTAS
INSERT INTO venta (ID_VENTA, ID_CLIENTE, TIPO_VENTA, TOTAL_VENTA, FECHA_VENTA, ID_EMPLEADO, ESTADO) VALUES
(1, 1, 'Local',    178.00, DATE_SUB(NOW(), INTERVAL 1 DAY),  2, 'FINALIZADA'),
(2, 2, 'Domicilio', 89.00, NOW(),                            2, 'FINALIZADA'),
(3, 3, 'Local',    128.00, DATE_SUB(NOW(), INTERVAL 2 DAY),  2, 'EN ESPERA'),
(4, 1, 'App',       49.00, DATE_SUB(NOW(), INTERVAL 3 DAY),  1, 'CANCELADA'),
(5, 2, 'Local',    124.00, NOW(),                            1, 'FINALIZADA');

INSERT INTO detalle_venta (ID_DETVENTA, SUBTOTAL_VENTA, CANTIDAD_VENTA, ID_VENTA, ID_PRODUCTO) VALUES
(1, 89.00, 1, 1, 1),
(2, 89.00, 1, 1, 2),
(3, 89.00, 1, 2, 1),
(4, 89.00, 1, 3, 1),
(5, 39.00, 1, 3, 5),
(6, 49.00, 1, 4, 3),
(7, 89.00, 1, 5, 1),
(8, 35.00, 1, 5, 8);

-- 10. COMPRAS A PROVEEDORES
INSERT INTO compra (ID_COMPRA, FECHA_COMPRA, TOTAL_COMPRA, ID_EMPLEADO, ID_PROVEEDOR) VALUES
(1, DATE_SUB(NOW(), INTERVAL 5 DAY),  315.00, 1, 1),
(2, DATE_SUB(NOW(), INTERVAL 2 DAY),  450.00, 1, 2);

INSERT INTO detalle_compra (ID_DETCOMPRA, SUBTOTAL_COMPRA, CANTIDAD_COMPRA, ID_PRODUCTO, ID_COMPRA) VALUES
(1, 150.00, 10, 1, 1),
(2, 165.00, 10, 3, 1),
(3, 200.00, 10, 5, 1),
(4, 450.00, 10, 2, 2);

-- 11. Ajustar stock por compras y ventas iniciales
UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO = 1;
UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO = 2;
UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO = 3;
UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO = 5;
UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO = 8;
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO = 1;
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO = 10;
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO = 3;
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO = 5;
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO = 2;

SELECT '✅ Datos insertados correctamente' AS resultado;
