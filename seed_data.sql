-- SWEETFIT FIT - DATOS DE PRUEBA
ALTER TABLE empleado MODIFY CONTRASEÑA VARCHAR(255);
ALTER TABLE producto MODIFY CATEGORIA ENUM('Ensaladas','Jugos y Licuados','Proteína','Snacks Fit','Bowls','Bebidas') DEFAULT NULL;

DELETE FROM detalle_compra;
DELETE FROM detalle_venta;
DELETE FROM compra;
DELETE FROM venta;
DELETE FROM producto_proveedor;
DELETE FROM producto;
DELETE FROM proveedor;
DELETE FROM cliente;
DELETE FROM empleado;

INSERT INTO empleado (ID_EMPLEADO, NOMBRE, APELLIDOS, EMAIL, CONTRASEÑA, PUESTO) VALUES
(1, 'Admin', 'Sweetfit', 'admin@sweetfit.com', 'pbkdf2:sha256:600000$salt_admin$hash_admin_placeholder', 'Administrador'),
(2, 'Cajero', 'Sweetfit', 'cajero@sweetfit.com', 'pbkdf2:sha256:600000$salt_cajero$hash_cajero_placeholder', 'Cajero');

INSERT INTO proveedor (ID_PROVEEDOR, NOMBRE, EMAIL, TELEFONO, CONTRASEÑA) VALUES
(1, 'Green Fields Orgánicos', 'contacto@greenfields.com', '2291112233', 'pbkdf2:sha256:600000$prov1$hash_prov1'),
(2, 'Fit Protein Supply',     'ventas@fitprotein.com',    '2292223344', 'pbkdf2:sha256:600000$prov2$hash_prov2'),
(3, 'Vital Juice Co.',        'pedidos@vitalJuice.com',  '2293334455', 'pbkdf2:sha256:600000$prov3$hash_prov3');

INSERT INTO producto (ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION) VALUES
(1, 'Ensalada Caesar Fit',  'Lechuga romana, pollo grillé, crutones integrales, aderezo light',  'Ensaladas', 25, 79.00, 'aderezo.jpg', 'APROBADO'),
(2, 'Bowl Verde',           'Quinoa, espinaca, aguacate, pepino, brócoli y vinagreta de limón',   'Bowls', 20, 89.00, 'aguacate.jpg', 'APROBADO'),
(3, 'Pechuga Empanizada',   'Pechuga de pollo empanizada con avena, horneada no frita',            'Proteína', 30, 79.00, 'pechuga.jpg', 'APROBADO'),
(4, 'Salmón a la Plancha',  'Filete de salmón fresco con especias y vegetales salteados',          'Proteína', 15, 119.00, 'atun.jpg', 'APROBADO'),
(5, 'Barrita Proteica',     'Barrita de proteína vegetal, sin azúcar añadida',                     'Snacks Fit', 50, 29.00, 'barritas_proteicas.jpg', 'APROBADO'),
(6, 'Green Smoothie',       'Espinaca, piña, manzana verde y jengibre',                             'Jugos y Licuados', 30, 55.00, 'Extra_Naranja.jpg', 'APROBADO'),
(7, 'Limonada con Chía',    'Limonada natural con semillas de chía y stevia',                      'Bebidas', 40, 35.00, 'naranja_miel.jpg', 'APROBADO'),
(8, 'Palomitas de Aire',    'Palomitas de maíz sin aceite, con sal de mar y romero',               'Snacks Fit', 50, 25.00, 'palomitas_aire.jpg', 'APROBADO'),
(9, 'Protein Shake',        'Licuado de proteína vegetal, plátano y leche de almendras',           'Jugos y Licuados', 20, 65.00, 'leche_coco.jpg', 'APROBADO');

INSERT INTO producto (ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION) VALUES
(10, 'Ensalada de Atún (Propuesta)', 'Ensalada de atún fresco con mezcla de verdes', 'Ensaladas', 40, 45.00, 'Deli_Tuna_CH.jpg', 'PENDIENTE'),
(11, 'Pack Protein Bars (Propuesta)', 'Pack 12 barritas sabor chocolate y vainilla', 'Snacks Fit', 60, 25.00, 'barritas_proteicas.jpg', 'PENDIENTE');

INSERT INTO producto_proveedor (ID_PRODUCTO, ID_PROVEEDOR) VALUES (10, 1), (11, 2);

INSERT INTO cliente (ID_CLIENTE, NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, DIRECCION, TELEFONO) VALUES
(1, 'Juan', 'Pérez', 'García', 'Calle 1 #123, Centro', '2291000100'),
(2, 'María', 'López', 'Martínez', 'Av. 2 #456, Reforma', '2291000200'),
(3, 'Carlos', 'Ramírez', NULL, 'Blvd. 3 #789, Costa de Oro', '2291000300');

INSERT INTO venta (ID_VENTA, ID_CLIENTE, TIPO_VENTA, TOTAL_VENTA, FECHA_VENTA, ID_EMPLEADO, ESTADO) VALUES
(1, 1, 'Local', 168.00, DATE_SUB(NOW(), INTERVAL 1 DAY), 2, 'FINALIZADA'),
(2, 2, 'Domicilio', 79.00, NOW(), 2, 'FINALIZADA'),
(3, 3, 'Local', 118.00, DATE_SUB(NOW(), INTERVAL 2 DAY), 2, 'EN ESPERA'),
(4, 1, 'App', 55.00, DATE_SUB(NOW(), INTERVAL 3 DAY), 1, 'CANCELADA'),
(5, 2, 'Local', 104.00, NOW(), 1, 'FINALIZADA');

INSERT INTO detalle_venta (ID_DETVENTA, SUBTOTAL_VENTA, CANTIDAD_VENTA, ID_VENTA, ID_PRODUCTO) VALUES
(1, 79.00, 1, 1, 1),
(2, 89.00, 1, 1, 2),
(3, 79.00, 1, 2, 3),
(4, 89.00, 1, 3, 2),
(5, 29.00, 1, 3, 5),
(6, 55.00, 1, 4, 6),
(7, 79.00, 1, 5, 1),
(8, 25.00, 1, 5, 8);

INSERT INTO compra (ID_COMPRA, FECHA_COMPRA, TOTAL_COMPRA, ID_EMPLEADO, ID_PROVEEDOR) VALUES
(1, DATE_SUB(NOW(), INTERVAL 5 DAY), 1050.00, 1, 1),
(2, DATE_SUB(NOW(), INTERVAL 2 DAY), 790.00, 1, 2);

INSERT INTO detalle_compra (ID_DETCOMPRA, SUBTOTAL_COMPRA, CANTIDAD_COMPRA, ID_PRODUCTO, ID_COMPRA) VALUES
(1, 450.00, 10, 1, 1),
(2, 350.00, 10, 6, 1),
(3, 250.00, 10, 5, 1),
(4, 790.00, 10, 3, 2);

UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO IN (1,2,3,5,6,8);
UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO IN (1,3,5,6);

SELECT ' Datos fit insertados' AS resultado;
