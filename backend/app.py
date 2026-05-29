from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
from mysql.connector import pooling
from flask_cors import CORS
import os
from datetime import datetime, date, timedelta 
import re
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import time

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Carpeta absoluta para guardar imágenes subidas
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

BASE_DIR = os.path.dirname(app.root_path)


db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'sweetfit'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'pool_name': 'sweetfit_pool',
    'pool_size': 5,
    'pool_reset_session': True
}

def get_db():
    try:
        return mysql.connector.connect(**db_config)
    except pooling.PoolError:
        return mysql.connector.connect(**db_config)

# ESTOS ENDPOINTS PERTENECEN A PANEL.HTML___________________________________________________

@app.route('/api/dashboard')
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    hoy = date.today()

    cursor.execute("SELECT IFNULL(SUM(TOTAL_VENTA), 0) AS ventas_dia FROM venta WHERE DATE(FECHA_VENTA) = %s", (hoy,))
    ventas_dia = cursor.fetchone()['ventas_dia']

    cursor.execute("SELECT COUNT(*) AS clientes_registrados FROM cliente")
    clientes_registrados = cursor.fetchone()['clientes_registrados']

    cursor.execute("SELECT COUNT(*) AS productos_disponibles FROM producto")
    productos_disponibles = cursor.fetchone()['productos_disponibles']

    cursor.execute("SELECT MAX(FECHA_COMPRA) AS ultima_compra FROM compra")
    ultima_compra = cursor.fetchone()['ultima_compra']
    ultima_compra = ultima_compra.strftime('%d/%m/%Y') if ultima_compra else 'Sin registro'

    conn.close()

    return jsonify({
        'ventas_dia': float(ventas_dia),
        'clientes_registrados': clientes_registrados,
        'productos_disponibles': productos_disponibles,
        'ultima_compra': ultima_compra
    })

# ESTOS ENDPOINTS PERTENECEN AL MENÚ DIGITAL PÚBLICO___________________________________________________

@app.route('/api/menu', methods=['GET'])
def obtener_menu_publico():
    """Devuelve productos aprobados con stock para el menú digital público."""
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ID_PRODUCTO, NOMBRE, DESCRIPCION, PRECIO, CATEGORIA, IMAGEN, CANTIDAD
            FROM producto
            WHERE ESTADO_APROBACION = 'APROBADO' AND CANTIDAD > 0
            ORDER BY CATEGORIA, NOMBRE
        """)
        productos = cursor.fetchall()
        cursor.close()
        conn.close()
        # Agrupar por categoría
        menu = {}
        for p in productos:
            cat = p['CATEGORIA'] or 'General'
            if cat not in menu:
                menu[cat] = []
            p['PRECIO'] = float(p['PRECIO']) if p['PRECIO'] else 0
            menu[cat].append(p)
        return jsonify(menu)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pedidos', methods=['POST', 'OPTIONS'])
def crear_pedido_online():
    """Registra un pedido online como venta EN ESPERA."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.json
        nombre_cliente = data.get('nombre', 'Cliente Web')
        telefono = data.get('telefono', '')
        tipo = data.get('tipo_pedido', 'Local')
        direccion = data.get('direccion', '')
        notas = data.get('notas', '')
        items = data.get('items', [])

        if not items:
            return jsonify({'error': 'El carrito está vacío'}), 400

        total = sum(float(i['precio']) * int(i['cantidad']) for i in items)

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Validar stock disponible para todos los productos
        for item in items:
            id_producto = item.get('id_producto')
            cantidad_pedido = int(item.get('cantidad', 0))

            cursor.execute("SELECT NOMBRE, CANTIDAD FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
            prod = cursor.fetchone()
            if not prod:
                cursor.close()
                conn.close()
                return jsonify({'error': f'Producto con ID {id_producto} no encontrado'}), 404
            
            stock_actual = prod['CANTIDAD']
            if cantidad_pedido > stock_actual:
                cursor.close()
                conn.close()
                return jsonify({'error': f"Stock insuficiente para el producto '{prod['NOMBRE']}' (Disponible: {stock_actual}, Pedido: {cantidad_pedido})"}), 400

        # Insertar venta con datos del cliente web
        cursor.execute("""
            INSERT INTO venta (TIPO_VENTA, TOTAL_VENTA, ESTADO, ID_CLIENTE, ID_EMPLEADO,
                               NOMBRE_CLIENTE_WEB, TELEFONO_CLIENTE_WEB, DIRECCION_CLIENTE_WEB, NOTAS_PEDIDO)
            VALUES (%s, %s, 'EN ESPERA', NULL, NULL, %s, %s, %s, %s)
        """, (tipo, total, nombre_cliente, telefono, direccion, notas))
        id_venta = cursor.lastrowid

        # Insertar detalle_venta y descontar stock
        for item in items:
            cursor.execute("""
                INSERT INTO detalle_venta (ID_VENTA, ID_PRODUCTO, CANTIDAD_VENTA, SUBTOTAL_VENTA)
                VALUES (%s, %s, %s, %s)
            """, (
                id_venta,
                item['id_producto'],
                item['cantidad'],
                float(item['precio']) * int(item['cantidad'])
            ))
            cursor.execute("""
                UPDATE producto 
                SET CANTIDAD = CANTIDAD - %s 
                WHERE ID_PRODUCTO = %s
            """, (int(item['cantidad']), item['id_producto']))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'mensaje': 'Pedido registrado exitosamente',
            'id_pedido': id_venta,
            'total': total,
            'nombre_cliente': nombre_cliente,
            'telefono': telefono,
            'notas': notas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ESTOS ENDPOINTS PERTENECEN A PRODUCTOS.HTML Y VENTAS.HTML___________________________________________________

# Ruta para obtener todos los productos
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    try:
        page = request.args.get('page', type=int)
        limit = request.args.get('limit', type=int)
        categoria = request.args.get('categoria', '')
        nombre = request.args.get('nombre', '').strip().lower()

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        filtros = ["ESTADO_APROBACION = 'APROBADO'"]
        valores = []

        if categoria:
            filtros.append("categoria = %s")
            valores.append(categoria)

        if nombre:
            filtros.append("LOWER(nombre) LIKE %s")
            valores.append(f"%{nombre}%")

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

        if nombre:
            query = f"SELECT * FROM producto {where_clause}"
            cursor.execute(query, tuple(valores))
            productos_crudos = cursor.fetchall()
            total_productos = len(productos_crudos)
            total_paginas = 1
            pagina_actual = 1
        else:
            page = page or 1
            limit = limit or 6
            offset = (page - 1) * limit

            count_query = f"SELECT COUNT(*) FROM producto {where_clause}"
            cursor.execute(count_query, tuple(valores))
            total_productos = cursor.fetchone()['COUNT(*)']

            query = f"SELECT * FROM producto {where_clause} LIMIT %s OFFSET %s"
            cursor.execute(query, (*valores, limit, offset))
            productos_crudos = cursor.fetchall()

            total_paginas = (total_productos // limit) + (1 if total_productos % limit != 0 else 0)
            pagina_actual = page

        cursor.close()
        conn.close()

        productos = [ {
            'id': p['ID_PRODUCTO'],
            'nombre': p['NOMBRE'],
            'descripcion': p['DESCRIPCION'],
            'categoria': p['CATEGORIA'],
            'cantidad': p['CANTIDAD'],
            'precio': float(p['PRECIO']),
            'imagen': p['IMAGEN']
        } for p in productos_crudos ]

        return jsonify({
            'productos': productos,
            'total_productos': total_productos,
            'total_paginas': total_paginas,
            'pagina_actual': pagina_actual
        })

    except mysql.connector.Error as err:
        print("ERROR MYSQL:", err)
        return jsonify({'error': str(err)}), 500

@app.route('/')
def root():
    return send_from_directory(BASE_DIR, 'login.html')

@app.route('/login.html')
def login_page():
    return send_from_directory(BASE_DIR, 'login.html')

@app.route('/menu.html')
def menu_page():
    return send_from_directory(BASE_DIR, 'menu.html')

@app.route('/extranet.html')
def extranet_page():
    return send_from_directory(BASE_DIR, 'extranet.html')

@app.route('/extranet_login.html')
def extranet_login_page():
    return send_from_directory(BASE_DIR, 'extranet_login.html')

@app.route('/pedido_confirmado.html')
def pedido_confirmado_page():
    return send_from_directory(BASE_DIR, 'pedido_confirmado.html')

@app.route('/index.html')
def index_page():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)

@app.route('/img/<path:filename>')
def serve_img(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'img'), filename)

# Ruta para servir archivos HTML del directorio views
@app.route('/views/<path:filename>')
def serve_views(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'views'), filename)

#Ruta del login
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return '', 200
    data = request.json  
    print(f"DEBUG: Request data received = {data}")
    email = data.get('email')
    contraseña = data.get('contraseña') or data.get('password')
    print(f"DEBUG: Extracted - Email: {email}, Contraseña: {contraseña}")

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM empleado WHERE EMAIL = %s", (email,))
        user = cursor.fetchone()

        if user:
            stored = user["CONTRASEÑA"]
            if stored.startswith("pbkdf2:") or stored.startswith("scrypt:") or stored.startswith("$2"):
                valida = check_password_hash(stored, contraseña)
            else:
                valida = (stored == contraseña)
                if valida:
                    cursor.execute(
                        "UPDATE empleado SET CONTRASEÑA = %s WHERE ID_EMPLEADO = %s",
                        (generate_password_hash(contraseña), user["ID_EMPLEADO"])
                    )
                    conn.commit()
        else:
            valida = False

        cursor.close()
        conn.close()

        if user and valida:
            return jsonify({
        "mensaje": "Login exitoso",
        "usuario": {
        "id": user["ID_EMPLEADO"],
        "nombre": user["NOMBRE"],
        "apellidos": user["APELLIDOS"],
        "email": user["EMAIL"],
        "puesto": user["PUESTO"]
    }
})
        else:
            return jsonify({"error": "Credenciales incorrectas"}), 401

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


# Ruta para obtener las categorías
@app.route('/api/categorias', methods=['GET'])
def obtener_categorias():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT categoria FROM producto")
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(categorias)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


# Ruta para agregar producto con imagen
@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        categoria = request.form.get('categoria')
        cantidad = request.form.get('cantidad')
        precio = request.form.get('precio')
        imagen_file = request.files.get('imagen')

        if not imagen_file:
            return jsonify({'error': 'Imagen requerida'}), 400

        filename = f"{int(time.time())}_{secure_filename(imagen_file.filename)}"
        ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen_file.save(ruta_imagen)

        conn = get_db()
        cursor = conn.cursor()
        query = """INSERT INTO producto 
                   (nombre, descripcion, categoria, cantidad, precio, imagen)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (nombre, descripcion, categoria, cantidad, precio, filename))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'mensaje': 'Producto agregado exitosamente'})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# Ruta para servir las imágenes
@app.route('/uploads/<filename>')
def servir_imagen(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Eliminar producto
@app.route('/api/eliminar_producto/<int:id_producto>', methods=['DELETE'])
def eliminar_producto(id_producto):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT IMAGEN FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
        prod = cursor.fetchone()
        if not prod:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
        
        cursor.execute("DELETE FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
        conn.commit()

        # Eliminar archivo de imagen del disco
        if prod['IMAGEN']:
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], prod['IMAGEN'])
            if os.path.exists(ruta):
                os.remove(ruta)

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'mensaje': 'Producto eliminado correctamente'})
    except mysql.connector.Error as err:
        if err.errno == 1451:
            return jsonify({'success': False, 'error': 'No se puede eliminar porque tiene ventas, compras o relaciones asociadas'}), 409
        return jsonify({'success': False, 'error': str(err)}), 500

# Editar producto (actualizar imagen)
@app.route('/api/editar_producto/<int:id_producto>', methods=['GET', 'POST'])
def editar_producto(id_producto):
    if request.method == 'POST' and request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    if request.method == 'GET':
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            query = """
                    SELECT ID_PRODUCTO, NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN
                    FROM producto 
                    WHERE ID_PRODUCTO = %s
                """
            cursor.execute(query, (id_producto,))
            producto = cursor.fetchone()
            cursor.close()
            conn.close()
            if not producto:
                return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
            
            producto_data = {
                'ID_PRODUCTO': producto['ID_PRODUCTO'],
                'nombre': producto['NOMBRE'],
                'descripcion': producto['DESCRIPCION'],
                'categoria': producto['CATEGORIA'],
                'cantidad': producto['CANTIDAD'],
                'precio': float(producto['PRECIO']),
                'imagen': producto['IMAGEN']
            }
            return jsonify(producto_data), 200
        except mysql.connector.Error as err:
            return jsonify({'success': False, 'error': str(err)}), 500

    if request.method == 'POST' and request.form.get('_method') == 'PUT':
        try:
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            categoria = request.form.get('categoria')
            precio = request.form.get('precio')

            imagen = None
            if 'imagen' in request.files:
                imagen_file = request.files['imagen']
                if imagen_file and imagen_file.filename != '':
                    filename = f"{int(time.time())}_{secure_filename(imagen_file.filename)}"
                    ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    imagen_file.save(ruta_imagen)
                    imagen = filename

            conn = get_db()
            cursor = conn.cursor()

            if imagen:
                query = """UPDATE producto 
                           SET NOMBRE = %s, DESCRIPCION = %s, CATEGORIA = %s, 
                               PRECIO = %s, IMAGEN = %s, ESTADO_APROBACION = 'APROBADO' 
                           WHERE ID_PRODUCTO = %s"""
                cursor.execute(query, (nombre, descripcion, categoria, precio, imagen, id_producto))
            else:
                query = """UPDATE producto 
                           SET NOMBRE = %s, DESCRIPCION = %s, CATEGORIA = %s, 
                               PRECIO = %s, ESTADO_APROBACION = 'APROBADO' 
                           WHERE ID_PRODUCTO = %s"""
                cursor.execute(query, (nombre, descripcion, categoria, precio, id_producto))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({
                'success': True,
                'mensaje': 'Producto actualizado exitosamente',
                'imagen': imagen
            }), 200

        except mysql.connector.Error as err:
            return jsonify({'success': False, 'error': str(err)}), 500
        except Exception as e:
            return jsonify({'success': False, 'error': f"Error inesperado: {str(e)}"}), 500

    return jsonify({'success': False, 'error': 'Método no permitido'}), 405

# Obtener producto por ID
@app.route('/api/producto/<int:id_producto>', methods=['GET'])
def obtener_producto_por_id(id_producto):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
        p = cursor.fetchone()
        cursor.close()
        conn.close()

        if p:
            producto = {
                'id_producto': p['ID_PRODUCTO'],
                'nombre': p['NOMBRE'],
                'descripcion': p['DESCRIPCION'],
                'categoria': p['CATEGORIA'],
                'cantidad': p['CANTIDAD'],
                'precio': float(p['PRECIO']),
                'imagen': p['IMAGEN']
            }
            return jsonify(producto)
        else:
            return jsonify({'error': 'Producto no encontrado'}), 404
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    
# ESTOS ENDPOINTS PERTENECEN A VENTAS.HTML___________________________________________________
@app.route('/api/ventas', methods=['GET'])
def obtener_ventas():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                v.ID_VENTA,
                v.FECHA_VENTA,
                v.TIPO_VENTA,
                v.TOTAL_VENTA,
                v.ESTADO,
                CONCAT(e.NOMBRE, ' ', e.APELLIDOS) AS empleado,
                CONCAT(c.NOMBRE, ' ', c.APELLIDO_PATERNO) AS CLIENTE
            FROM venta v
            LEFT JOIN empleado e ON v.ID_EMPLEADO = e.ID_EMPLEADO
            LEFT JOIN cliente c ON v.ID_CLIENTE = c.ID_CLIENTE
            ORDER BY v.FECHA_VENTA DESC
        """
        cursor.execute(query)
        ventas = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(ventas)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    

@app.route('/api/ventas', methods=['POST'])
def registrar_venta():
    if request.headers.get('X-User-Role') not in ('Administrador', 'Cajero'):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.get_json()

        cliente = data.get("cliente")
        carrito = data.get("carrito")
        empleado = data.get("empleado")
        TIPOS_VENTA_VALIDOS = {"Local", "Domicilio", "App"}

        tipo_venta_raw = data.get("tipo_venta", "")
        tipo_venta = tipo_venta_raw.strip().capitalize()

        if tipo_venta not in TIPOS_VENTA_VALIDOS:
            return jsonify({"error": f"Tipo de venta inválido. Valores permitidos: {', '.join(TIPOS_VENTA_VALIDOS)}"}), 400


        estado = data.get("estado", "FINALIZADA").upper()

        ESTADOS_VALIDOS = {"FINALIZADA", "EN ESPERA", "CANCELADA"}
        if estado not in ESTADOS_VALIDOS:
            return jsonify({"error": f"Estado inválido. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}"}), 400

        if not carrito or not cliente or not empleado or not tipo_venta:
            return jsonify({"error": "Datos incompletos"}), 400

        conn = get_db()
        cursor = conn.cursor()

        # 1. Buscar si el cliente ya existe
        query_buscar_cliente = """
            SELECT ID_CLIENTE FROM cliente
            WHERE NOMBRE = %s AND APELLIDO_PATERNO = %s AND APELLIDO_MATERNO = %s AND TELEFONO = %s
        """
        cursor.execute(query_buscar_cliente, (
            cliente["nombre"],
            cliente["apellido_paterno"],
            cliente["apellido_materno"],
            cliente["telefono"]
        ))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            id_cliente = cliente_existente[0]
        else:
            # Si no existe, insertarlo
            query_cliente = """
                INSERT INTO cliente (NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, DIRECCION, TELEFONO)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query_cliente, (
                cliente["nombre"],
                cliente["apellido_paterno"],
                cliente["apellido_materno"],
                cliente["direccion"],
                cliente["telefono"]
            ))
            id_cliente = cursor.lastrowid


        # 2. Obtener ID del empleado (supongo que llega como nombre completo)
        query_empleado = "SELECT ID_EMPLEADO FROM empleado WHERE CONCAT(NOMBRE, ' ', APELLIDOS) = %s"
        cursor.execute(query_empleado, (empleado,))
        empleado_result = cursor.fetchone()
        if not empleado_result:
            conn.rollback()
            return jsonify({"error": "empleado no encontrado"}), 400
        id_empleado = empleado_result[0]

        # 3. Calcular total
        total = sum(p['subtotal'] for p in carrito)

        # 4. Insertar venta
        query_venta = """
            INSERT INTO venta (ID_CLIENTE, TIPO_VENTA, TOTAL_VENTA, FECHA_VENTA, ID_EMPLEADO, ESTADO)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        fecha_venta = datetime.now()
        cursor.execute(query_venta, (
            id_cliente,
            tipo_venta,
            total,
            fecha_venta,
            id_empleado,
            estado
        ))
        id_venta = cursor.lastrowid

        # 5. Insertar productos en detalle_venta y descontar stock
        for producto in carrito:
            query_detalle = """
                INSERT INTO detalle_venta (SUBTOTAL_VENTA, CANTIDAD_VENTA, ID_VENTA, ID_PRODUCTO)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query_detalle, (
                producto["subtotal"],
                producto["cantidad"],
                id_venta,
                producto["id"]
            ))

            cursor.execute(
                "UPDATE producto SET CANTIDAD = CANTIDAD - %s WHERE ID_PRODUCTO = %s",
                (producto["cantidad"], producto["id"])
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"mensaje": "Venta registrada correctamente", "id_venta": id_venta})

    except mysql.connector.Error as err:
        print("Error al registrar venta:", err)
        return jsonify({"error": str(err)}), 500
    

@app.route('/api/ventas/<int:id_venta>', methods=['PUT'])
def actualizar_venta_completa(id_venta):
    if request.headers.get('X-User-Role') not in ('Administrador', 'Cajero'):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.get_json()

        nuevo_estado = data.get("estado", "").upper()
        tipo_venta_raw = data.get("tipo_venta") or data.get("tipoVenta") or ""
        cliente_data = data.get("cliente")
        carrito_data = data.get("carrito")

        ESTADOS_VALIDOS = {"FINALIZADA", "EN ESPERA", "CANCELADA"}
        TIPOS_VENTA_VALIDOS = {"Local", "Domicilio", "App"}

        tipo_venta = None
        if tipo_venta_raw:
            tipo_venta_formateado = tipo_venta_raw.strip().capitalize()
            if tipo_venta_formateado not in TIPOS_VENTA_VALIDOS:
                return jsonify({"error": f"Tipo de venta inválido. Debe ser uno de: {', '.join(TIPOS_VENTA_VALIDOS)}"}), 400
            tipo_venta = tipo_venta_formateado

        if nuevo_estado and nuevo_estado not in ESTADOS_VALIDOS:
            return jsonify({"error": f"Estado inválido. Debe ser uno de: {', '.join(ESTADOS_VALIDOS)}"}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Obtener cliente asociado
        cursor.execute("SELECT ID_CLIENTE FROM venta WHERE ID_VENTA = %s", (id_venta,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "Venta no encontrada"}), 404
        id_cliente = result["ID_CLIENTE"]

        # Si no se proporciona carrito, decidimos según el nuevo estado
        if carrito_data is None:
            if nuevo_estado == "CANCELADA":
                # Comportamiento original para cancelación: devolver stock y borrar detalles
                cursor.execute("SELECT ID_PRODUCTO, CANTIDAD_VENTA FROM detalle_venta WHERE ID_VENTA = %s", (id_venta,))
                detalles_antiguos = cursor.fetchall()
                for detalle in detalles_antiguos:
                    cursor.execute(
                        "UPDATE producto SET CANTIDAD = CANTIDAD + %s WHERE ID_PRODUCTO = %s",
                        (detalle["CANTIDAD_VENTA"], detalle["ID_PRODUCTO"])
                    )
                cursor.execute("UPDATE venta SET ESTADO = %s WHERE ID_VENTA = %s", (nuevo_estado, id_venta))
                cursor.execute("DELETE FROM detalle_venta WHERE ID_VENTA = %s", (id_venta,))
            else:
                # Solo actualizar el estado de la venta sin tocar stock ni detalles
                if nuevo_estado:
                    cursor.execute("UPDATE venta SET ESTADO = %s WHERE ID_VENTA = %s", (nuevo_estado, id_venta))
                if tipo_venta:
                    cursor.execute("UPDATE venta SET TIPO_VENTA = %s WHERE ID_VENTA = %s", (tipo_venta, id_venta))
        else:
            # Comportamiento completo original
            # Obtener detalles antiguos (productos y cantidades)
            cursor.execute("SELECT ID_PRODUCTO, CANTIDAD_VENTA FROM detalle_venta WHERE ID_VENTA = %s", (id_venta,))
            detalles_antiguos = cursor.fetchall()

            # *** DEVOLVER STOCK ANTIGUO PRIMERO ***
            for detalle in detalles_antiguos:
                cursor.execute(
                    "UPDATE producto SET CANTIDAD = CANTIDAD + %s WHERE ID_PRODUCTO = %s",
                    (detalle["CANTIDAD_VENTA"], detalle["ID_PRODUCTO"])
                )

            # VALIDAR STOCK NUEVO
            for item in carrito_data:
                id_producto = item.get("ID_PRODUCTO") or item.get("id") or item.get("id_producto")
                cantidad_nueva = item.get("cantidad")

                if id_producto is None or cantidad_nueva is None:
                    return jsonify({"error": f"Producto con datos faltantes: {item}"}), 400

                cursor.execute("SELECT CANTIDAD FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
                producto = cursor.fetchone()
                if not producto:
                    return jsonify({"error": f"Producto con ID {id_producto} no encontrado"}), 404

                stock_actual = producto["CANTIDAD"]

                if cantidad_nueva > stock_actual:
                    return jsonify({"error": f"Stock insuficiente para el producto {id_producto} (Disponible: {stock_actual}, Pedido: {cantidad_nueva})"}), 400

            # ACTUALIZAR CLIENTE
            if cliente_data:
                cursor.execute("""
                    UPDATE cliente SET NOMBRE = %s, APELLIDO_PATERNO = %s, APELLIDO_MATERNO = %s,
                    DIRECCION = %s, TELEFONO = %s WHERE ID_CLIENTE = %s
                """, (
                    cliente_data.get("nombre"),
                    cliente_data.get("apellido_paterno"),
                    cliente_data.get("apellido_materno"),
                    cliente_data.get("direccion"),
                    cliente_data.get("telefono"),
                    id_cliente
                ))

            # ACTUALIZAR ESTADO Y TIPO VENTA
            if nuevo_estado:
                cursor.execute("UPDATE venta SET ESTADO = %s WHERE ID_VENTA = %s", (nuevo_estado, id_venta))
            if tipo_venta:
                cursor.execute("UPDATE venta SET TIPO_VENTA = %s WHERE ID_VENTA = %s", (tipo_venta, id_venta))

            # ELIMINAR DETALLES ANTIGUOS (ya devolvimos stock antes)
            cursor.execute("DELETE FROM detalle_venta WHERE ID_VENTA = %s", (id_venta,))

            # INSERTAR NUEVOS DETALLES Y DESCONTAR STOCK
            insert_detalle_query = """
                INSERT INTO detalle_venta (ID_VENTA, ID_PRODUCTO, CANTIDAD_VENTA, SUBTOTAL_VENTA)
                VALUES (%s, %s, %s, %s)
            """
            for item in carrito_data:
                id_producto = item.get("ID_PRODUCTO") or item.get("id") or item.get("id_producto")
                cantidad = item.get("cantidad")
                subtotal = item.get("subtotal")

                cursor.execute(insert_detalle_query, (id_venta, id_producto, cantidad, subtotal))
                cursor.execute("""
                    UPDATE producto 
                    SET CANTIDAD = CANTIDAD - %s 
                    WHERE ID_PRODUCTO = %s
                """, (cantidad, id_producto))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"mensaje": f"Venta {id_venta} actualizada correctamente"})

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


@app.route('/api/ventas/<int:id_venta>', methods=['GET'])
def obtener_detalles_venta(id_venta):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Obtener info cliente, venta y empleado
        query_venta = """
            SELECT v.ID_VENTA, v.FECHA_VENTA, v.TIPO_VENTA, v.TOTAL_VENTA, v.ESTADO,
                   v.NOMBRE_CLIENTE_WEB, v.TELEFONO_CLIENTE_WEB, v.DIRECCION_CLIENTE_WEB, v.NOTAS_PEDIDO,
                   c.ID_CLIENTE, c.NOMBRE AS cliente_nombre, c.APELLIDO_PATERNO AS cliente_apellido_paterno,
                   c.APELLIDO_MATERNO AS cliente_apellido_materno, c.DIRECCION AS cliente_direccion,
                   c.TELEFONO AS cliente_telefono,
                   e.NOMBRE AS empleado_nombre, e.APELLIDOS AS empleado_apellidos
            FROM venta v
            LEFT JOIN cliente c ON v.ID_CLIENTE = c.ID_CLIENTE
            LEFT JOIN empleado e ON v.ID_EMPLEADO = e.ID_EMPLEADO
            WHERE v.ID_VENTA = %s
        """
        cursor.execute(query_venta, (id_venta,))
        venta = cursor.fetchone()
        if not venta:
            return jsonify({"error": "Venta no encontrada"}), 404

        # Obtener detalles del carrito (productos)
        query_detalle = """
            SELECT dv.ID_PRODUCTO, p.NOMBRE, dv.CANTIDAD_VENTA AS cantidad, 
                   p.PRECIO, dv.SUBTOTAL_VENTA AS subtotal
            FROM detalle_venta dv
            JOIN producto p ON dv.ID_PRODUCTO = p.ID_PRODUCTO
            WHERE dv.ID_VENTA = %s
        """
        cursor.execute(query_detalle, (id_venta,))
        carrito = cursor.fetchall()

        cursor.close()
        conn.close()

        # Si es pedido web, usar datos guardados en la venta
        es_pedido_web = venta.get("NOMBRE_CLIENTE_WEB") is not None
        if es_pedido_web:
            cliente_nombre_completo = venta["NOMBRE_CLIENTE_WEB"]
        else:
            cliente_nombre_completo = " ".join(filter(None, [
                venta.get("cliente_nombre"),
                venta.get("cliente_apellido_paterno"),
                venta.get("cliente_apellido_materno")
            ])).strip() or "Cliente desconocido"

        # Construir empleado como nombre completo
        empleado_nombre_completo = " ".join(filter(None, [
            venta.get("empleado_nombre"),
            venta.get("empleado_apellidos")
        ])).strip() or "Empleado desconocido"

        # Fecha en formato ISO para JS
        fecha_iso = venta["FECHA_VENTA"].isoformat() if venta.get("FECHA_VENTA") else ""

        # Estructura de respuesta
        response = {
            "orden": venta["ID_VENTA"],
            "id_cliente": venta.get("ID_CLIENTE"),
            "cliente": cliente_nombre_completo,
            "empleado": empleado_nombre_completo,
            "fecha": fecha_iso,
            "direccion": venta.get("cliente_direccion", ""),
            "telefono": venta.get("cliente_telefono", ""),
            "tipo_venta": venta.get("TIPO_VENTA", ""),
            "es_pedido_web": es_pedido_web,
            "telefono_web": venta.get("TELEFONO_CLIENTE_WEB", ""),
            "direccion_web": venta.get("DIRECCION_CLIENTE_WEB", ""),
            "notas_web": venta.get("NOTAS_PEDIDO", ""),
            "detallesV": [
                {
                    "ID_PRODUCTO": item["ID_PRODUCTO"],              # ¡Aquí está el ID correcto!
                    "PRODUCTO": item["NOMBRE"],
                    "CANTIDAD_VENTA": item["cantidad"],
                    "PRECIO_UNITARIO": float(item["PRECIO"]),
                    "SUBTOTAL_VENTA": float(item["subtotal"])
                } for item in carrito
            ]
        }

        return jsonify(response)

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    
    
# Obtener historial de ventas con filtros
@app.route('/api/ventas/historial', methods=['GET'])
def historial_ventas():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado: solo administradores'}), 403
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_venta = request.args.get('tipo_venta')
        id_empleado = request.args.get('empleado')

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT v.ID_VENTA, v.FECHA_VENTA, v.TOTAL_VENTA, v.TIPO_VENTA, v.ESTADO,
                   c.NOMBRE AS nombre_cliente,
                   e.NOMBRE AS nombre_empleado
            FROM venta v
            LEFT JOIN cliente c ON v.ID_CLIENTE = c.ID_CLIENTE
            LEFT JOIN empleado e ON v.ID_EMPLEADO = e.ID_EMPLEADO
            WHERE 1=1
        """
        params = []

        if fecha_inicio and fecha_fin:
            query += " AND v.FECHA_VENTA BETWEEN %s AND %s"
            params.extend([fecha_inicio, fecha_fin])

        if tipo_venta:
            query += " AND v.TIPO_VENTA = %s"
            params.append(tipo_venta)

        if id_empleado:
            query += " AND v.ID_EMPLEADO = %s"
            params.append(id_empleado)

        query += " ORDER BY v.FECHA_VENTA DESC"

        cursor.execute(query, tuple(params))
        ventas = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(ventas)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


@app.route('/api/cliente', methods=['GET'])
def buscar_cliente():
    nombre_query = request.args.get('nombre', '').strip()
    if not nombre_query:
        return jsonify([])  # Sin nombre no buscamos nada

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Buscar clientes cuyo nombre empiece con lo escrito
    query = """
        SELECT NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, DIRECCION, TELEFONO
        FROM cliente
        WHERE NOMBRE LIKE %s
        LIMIT 5
    """
    cursor.execute(query, (nombre_query + '%',))
    resultados = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(resultados)

# ESTOS ENDPOINTS PERTENECEN A CLIENTE.HTML __________________________________________________________________________________________
# Ruta para obtener todos los clientes
@app.route('/api/clientes', methods=['GET'])
def obtener_clientes():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cliente")
        clientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(clientes)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    
# ruta para agregar clientes
@app.route('/api/clientes', methods=['POST'])
def agregar_cliente():
    try:
        data = request.json
        nombre = data.get('nombre')
        apellido_paterno = data.get('apellido_paterno')
        apellido_materno = data.get('apellido_materno')
        direccion = data.get('direccion')
        telefono = data.get('telefono')

        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO cliente (nombre, apellido_paterno, apellido_materno, direccion, telefono) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (nombre, apellido_paterno, apellido_materno, direccion, telefono))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'error': str(err)}), 500
    
# Ruta para eliminar clientes
@app.route('/api/clientes/<int:id_cliente>', methods=['DELETE'])
def eliminar_cliente(id_cliente):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cliente WHERE id_cliente = %s", (id_cliente,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'error': str(err)}), 500
    
# Ruta para actualizar cliente
@app.route('/api/clientes/<int:id_cliente>', methods=['PUT'])
def actualizar_cliente(id_cliente):
    try:
        data = request.json
        conn = get_db()
        cursor = conn.cursor()
        query = """
            UPDATE cliente 
            SET NOMBRE = %s, APELLIDO_PATERNO = %s, APELLIDO_MATERNO = %s, 
                DIRECCION = %s, TELEFONO = %s 
            WHERE ID_CLIENTE = %s
        """
        cursor.execute(query, (
            data.get('nombre'), data.get('apellido_paterno'), data.get('apellido_materno'),
            data.get('direccion'), data.get('telefono'), id_cliente
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'error': str(err)}), 500

# Ruta para obtener el historial de venntas por cada cliente
@app.route('/api/clientes/<int:id_cliente>/historial', methods=['GET'])
def obtener_historial_compras(id_cliente):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT V.ID_VENTA, V.TIPO_VENTA, V.TOTAL_VENTA, V.FECHA_VENTA
        FROM venta V
        WHERE V.ID_CLIENTE = %s
        """
        cursor.execute(query, (id_cliente,))
        historial = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(historial if historial else [])
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
# __________________________________________________________________________________________________________________________________

# ESTOS ENDPOINTS PERTENECEN A PROVEEDORES.HTML __________________________________________________________________________________________
# Obtener proveedores
@app.route('/api/proveedores', methods=['GET'])
def obtener_proveedores():
    try:
        nombre = request.args.get('nombre','').strip().lower()

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        if nombre:
            query = "SELECT ID_PROVEEDOR, NOMBRE, EMAIL, TELEFONO FROM proveedor WHERE LOWER(NOMBRE) LIKE %s"
            cursor.execute(query, (f"%{nombre}%",))
        else:
            cursor.execute("SELECT ID_PROVEEDOR, NOMBRE, EMAIL, TELEFONO FROM proveedor")

        proveedores = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(proveedores)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    
#Obtener productos por proveedor
@app.route('/api/productoproveedor/<int:id_proveedor>', methods=['GET'])
@app.route('/api/proveedores/<int:id_proveedor>/productos', methods=['GET'])
def obtener_productoproveedor(id_proveedor):
    try: 
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT p.*, pr.NOMBRE as nombre_proveedor, pr.ID_PROVEEDOR as id_proveedor
        FROM producto p
        JOIN producto_proveedor pp ON p.ID_PRODUCTO = pp.ID_PRODUCTO
        JOIN proveedor pr ON pp.ID_PROVEEDOR = pr.ID_PROVEEDOR
        WHERE pr.ID_PROVEEDOR = %s
        """
        cursor.execute(query, (id_proveedor,))
        productos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(productos)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# Agregar proveedor
@app.route('/api/proveedores', methods=['POST'])
def agregar_proveedor():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.json
        nombre = data.get('nombre')
        email = data.get('email')
        telefono = data.get('telefono')
        contrasena = data.get('contrasena')

        conn = get_db()
        cursor = conn.cursor()
        query = "INSERT INTO proveedor (NOMBRE, EMAIL, TELEFONO, CONTRASEÑA) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (nombre, email, telefono, generate_password_hash(contrasena) if contrasena else None))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    
#EliminarProveedor
@app.route('/api/proveedores/<int:id_proveedor>', methods=['DELETE'])
def eliminar_proveedor(id_proveedor):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM proveedor WHERE ID_PROVEEDOR = %s", (id_proveedor,))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    
#Editar Proveedor
@app.route('/api/proveedores/<int:id_proveedor>', methods=['PUT'])
def actualizar_proveedor(id_proveedor):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.json
        nombre = data.get('nombre')
        email = data.get('email')
        telefono = data.get('telefono')
        contrasena = data.get('contrasena')

        conn = get_db()
        cursor = conn.cursor()

        if contrasena:
            query = """
                    UPDATE PROVEEDOR
                    SET NOMBRE = %s, EMAIL = %s, TELEFONO = %s, CONTRASEÑA = %s
                    WHERE ID_PROVEEDOR = %s
            """
            cursor.execute(query, (nombre, email, telefono, generate_password_hash(contrasena), id_proveedor))
        else:
            query = """
                    UPDATE PROVEEDOR
                    SET NOMBRE = %s, EMAIL = %s, TELEFONO = %s
                    WHERE ID_PROVEEDOR = %s
            """
            cursor.execute(query, (nombre, email, telefono, id_proveedor))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}, 500)

# Registrar una compra
@app.route('/api/compras', methods=['POST'])
def registrar_compra():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.json
        proveedor_id = data.get('proveedor')
        empleado_id = data.get('empleado')
        productos = data.get('productos')

        if not proveedor_id or not productos or not empleado_id:
            return jsonify({'error': 'Faltan datos de proveedor, empleado o productos'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO compra (ID_PROVEEDOR, ID_EMPLEADO, TOTAL_COMPRA) VALUES (%s, %s, %s)",
            (proveedor_id, empleado_id, 0)  # Total temporal
        )
        id_compra = cursor.lastrowid

        total = 0
        for prod in productos:
            id_producto = prod['id']
            cantidad = prod['cantidad']

            cursor.execute("SELECT PRECIO FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
            precio = cursor.fetchone()[0]
            subtotal = float(precio) * cantidad
            total += subtotal

            cursor.execute("""
                INSERT INTO detalle_compra (ID_COMPRA, ID_PRODUCTO, CANTIDAD_COMPRA, SUBTOTAL_COMPRA)
                VALUES (%s, %s, %s, %s)
            """, (id_compra, id_producto, cantidad, subtotal))

            # Actualizar inventario

            cursor.execute("""
                UPDATE producto SET CANTIDAD = CANTIDAD + %s WHERE ID_PRODUCTO = %s
           """, (cantidad, id_producto))

        # Actualizar total final
        cursor.execute("UPDATE compra SET TOTAL_COMPRA = %s WHERE ID_COMPRA = %s", (total, id_compra))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# Obtener historial de compras
@app.route('/api/compras', methods=['GET'])
def historial_compras_proveedores():
    try:
        fecha = request.args.get('fecha')

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT C.ID_COMPRA, C.FECHA_COMPRA, C.TOTAL_COMPRA, P.NOMBRE AS NOMBRE_PROVEEDOR
        FROM compra C
        JOIN proveedor P ON C.ID_PROVEEDOR = P.ID_PROVEEDOR
        """
        if fecha:
            query += " WHERE DATE(C.FECHA_COMPRA) = %s ORDER BY C.FECHA_COMPRA DESC"
            cursor.execute(query, (fecha,))
        else:
            query += " ORDER BY C.FECHA_COMPRA DESC"
            cursor.execute(query)

        compras = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([
            {
                'id_compra': c['ID_COMPRA'],
                'fecha': c['FECHA_COMPRA'].strftime("%d-%m-%Y %H:%M"),
                'total': float(c['TOTAL_COMPRA']),
                'nombre_proveedor': c['NOMBRE_PROVEEDOR']
            } for c in compras
        ])
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# RUTA PARA LOS TICKETS DE COMPRA
@app.route('/api/compras/<int:id_compra>', methods=['GET'])
def detalle_compra(id_compra):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query_compra = """
        SELECT C.FECHA_COMPRA, P.NOMBRE AS PROVEEDOR_NOMBRE, C.ID_COMPRA AS ORDEN_COMPRA, E.NOMBRE AS NOMBRE_EMPLEADO
        FROM compra C
        JOIN proveedor P ON C.ID_PROVEEDOR = P.ID_PROVEEDOR
        JOIN empleado E ON C.ID_EMPLEADO = E.ID_EMPLEADO
        WHERE C.ID_COMPRA = %s;
        """
        cursor.execute(query_compra, (id_compra,))
        compra = cursor.fetchone()

        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404

        fecha_compra = compra['FECHA_COMPRA'].strftime("%Y-%m-%dT%H:%M:%S")
        nombre_proveedor = compra['PROVEEDOR_NOMBRE']
        orden_compra = compra['ORDEN_COMPRA']
        nombre_empleado = compra['NOMBRE_EMPLEADO']


        query_detalles = """
        SELECT DP.CANTIDAD_COMPRA, PR.NOMBRE, PR.PRECIO AS 'PRECIO UNITARIO', DP.SUBTOTAL_COMPRA
        FROM detalle_compra DP
        JOIN producto PR ON DP.ID_PRODUCTO = PR.ID_PRODUCTO
        WHERE DP.ID_COMPRA = %s;
        """
        cursor.execute(query_detalles, (id_compra,))
        detalles = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'fecha': fecha_compra,
            'proveedor': nombre_proveedor,
            'orden': orden_compra,
            'empleado': nombre_empleado,
            'detalles': detalles
        })

    except mysql.connector.Error as err:
        print("Error al consultar detalles de la compra:", err)
        return jsonify({'error': str(err)}), 500

# __________________________________________________________________________________________________________________________________

# ESTOS ENDPOINTS PERTENECEN A REPORTES.HTML______________________________________________________________________________________________________________________

def parse_fecha_semana(fecha):
    match = re.match(r"(\d{4})-W(\d{1,2})", fecha)
    if match:
        anio = int(match.group(1))
        semana = int(match.group(2))
        return anio, semana
    return None, None

def validar_fecha_diario(fecha):
    try:
        dt = datetime.strptime(fecha, '%Y-%m-%d')
        return dt.date()
    except ValueError:
        return None

def validar_fecha_mensual(fecha):
    try:
        dt = datetime.strptime(fecha, '%Y-%m')
        return dt.year, dt.month
    except ValueError:
        return None, None

@app.route('/api/reportes/ventas', methods=['GET'])
def obtener_ventas_reporte():
    tipo = request.args.get('tipo', 'diario').lower()
    fecha = request.args.get('fecha', None)

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if tipo == 'diario':
            if fecha:
                fecha_valida = validar_fecha_diario(fecha)
                if not fecha_valida:
                    return jsonify({'error': 'Formato de fecha inválido para tipo diario. Use YYYY-MM-DD'}), 400

                query = """
                    SELECT 
                        DATE_FORMAT(FECHA_VENTA, '%Y-%m-%d %H:00:00') AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE DATE(FECHA_VENTA) = %s AND ESTADO = 'FINALIZADA'
                    GROUP BY DATE_FORMAT(FECHA_VENTA, '%Y-%m-%d %H:00:00')
                    ORDER BY fecha
                """
                cursor.execute(query, (fecha_valida,))
                ventas = cursor.fetchall()
            else:
                query = """
                    SELECT 
                        DATE(FECHA_VENTA) AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE FECHA_VENTA >= CURDATE() - INTERVAL 30 DAY AND ESTADO = 'FINALIZADA'
                    GROUP BY DATE(FECHA_VENTA)
                    ORDER BY fecha
                """
                cursor.execute(query)
                ventas = cursor.fetchall()

        elif tipo == 'semanal':
            if fecha:
                anio, semana = parse_fecha_semana(fecha)
                if anio is None or semana is None:
                    return jsonify({'error': 'Formato de fecha inválido para tipo semanal. Use YYYY-Www'}), 400

                query = """
                    SELECT 
                        DATE(FECHA_VENTA) AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE YEAR(FECHA_VENTA) = %s 
                    AND WEEK(FECHA_VENTA, 1) = %s
                    AND ESTADO = 'FINALIZADA'
                    GROUP BY DATE(FECHA_VENTA)
                    ORDER BY fecha
                """
                cursor.execute(query, (anio, semana))
                ventas = cursor.fetchall()
            else:
                query = """
                    SELECT 
                        DATE(FECHA_VENTA) AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE FECHA_VENTA >= CURDATE() - INTERVAL 12 WEEK
                    AND ESTADO = 'FINALIZADA'
                    GROUP BY DATE(FECHA_VENTA)
                    ORDER BY fecha
                """
                cursor.execute(query)
                ventas = cursor.fetchall()

        elif tipo == 'mensual':
            if fecha:
                anio, mes = validar_fecha_mensual(fecha)
                if anio is None or mes is None:
                    return jsonify({'error': 'Formato de fecha inválido para tipo mensual. Use YYYY-MM'}), 400

                query = """
                    SELECT 
                        YEAR(FECHA_VENTA) AS anio,
                        MONTH(FECHA_VENTA) AS mes,
                        DATE_FORMAT(FECHA_VENTA, '%Y-%m-01') AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE YEAR(FECHA_VENTA) = %s AND MONTH(FECHA_VENTA) = %s AND ESTADO = 'FINALIZADA'
                    GROUP BY anio, mes, fecha
                    ORDER BY anio, mes
                """
                cursor.execute(query, (anio, mes))
                ventas = cursor.fetchall()
            else:
                query = """
                    SELECT 
                        YEAR(FECHA_VENTA) AS anio,
                        MONTH(FECHA_VENTA) AS mes,
                        DATE_FORMAT(FECHA_VENTA, '%Y-%m-01') AS fecha,
                        SUM(TOTAL_VENTA) AS total_ventas
                    FROM venta
                    WHERE FECHA_VENTA >= CURDATE() - INTERVAL 12 MONTH AND ESTADO = 'FINALIZADA'
                    GROUP BY anio, mes, fecha
                    ORDER BY anio, mes
                """
                cursor.execute(query)
                ventas = cursor.fetchall()

        else:
            return jsonify({'error': 'Tipo de reporte inválido. Use diario, semanal o mensual.'}), 400

        cursor.close()
        conn.close()

        return jsonify({'ventas': ventas})

    except mysql.connector.Error as err:
        print("ERROR MYSQL:", err)
        return jsonify({'error': str(err)}), 500

    
@app.route('/api/reportes/categorias', methods=['GET'])
def obtener_categorias_mas_vendidas():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT p.CATEGORIA, SUM(dv.CANTIDAD_VENTA) as total_cantidad_vendida, SUM(dv.SUBTOTAL_VENTA) as total_ventas
            FROM detalle_venta dv
            JOIN producto p ON dv.ID_PRODUCTO = p.ID_PRODUCTO
            JOIN venta v ON dv.ID_VENTA = v.ID_VENTA
            WHERE v.FECHA_VENTA >= CURDATE() - INTERVAL 30 DAY
            GROUP BY p.CATEGORIA
            ORDER BY total_cantidad_vendida DESC
            LIMIT 10
        """
        cursor.execute(query)
        categorias = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({'categorias': categorias})

    except mysql.connector.Error as err:
        print("ERROR MYSQL:", err)
        return jsonify({'error': str(err)}), 500
    

@app.route('/api/reportes/productos-mas-vendidos', methods=['GET'])
def productos_mas_vendidos():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT p.NOMBRE AS nombre,
                   SUM(dv.CANTIDAD_VENTA) AS total_vendido,
                   SUM(dv.SUBTOTAL_VENTA) AS total_ingresos
            FROM detalle_venta dv
            JOIN producto p ON dv.ID_PRODUCTO = p.ID_PRODUCTO
            JOIN venta v ON dv.ID_VENTA = v.ID_VENTA
            WHERE v.ESTADO = 'FINALIZADA'
            GROUP BY p.ID_PRODUCTO
            ORDER BY total_vendido DESC
            LIMIT 10
        """
        cursor.execute(query)
        productos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(productos)
    except mysql.connector.Error as err:
        print("ERROR MYSQL:", err)
        return jsonify({'error': str(err)}), 500


@app.route('/api/reportes/detalles', methods=['GET'])
def obtener_reporte_completo():
    tipo = request.args.get('tipo')
    fecha = request.args.get('fecha')

    if not tipo or not fecha:
        return jsonify({'error': 'Parámetros requeridos: tipo y fecha'}), 400

    # Validar fechas según tipo
    if tipo == 'diario':
        fecha_valida = validar_fecha_diario(fecha)
        if not fecha_valida:
            return jsonify({'error': 'Fecha inválida (YYYY-MM-DD requerida)'}), 400
        filtro_fecha = "DATE(v.FECHA_VENTA) = %s"
        filtro_fecha_compra = "DATE(c.FECHA_COMPRA) = %s"
        params = (fecha_valida,)
    
    elif tipo == 'semanal':
        anio, semana = parse_fecha_semana(fecha)
        if not anio or not semana:
            return jsonify({'error': 'Fecha inválida para semanal (YYYY-Www)'}), 400
        filtro_fecha = "YEAR(v.FECHA_VENTA) = %s AND WEEK(v.FECHA_VENTA, 1) = %s"
        filtro_fecha_compra = "YEAR(c.FECHA_COMPRA) = %s AND WEEK(c.FECHA_COMPRA, 1) = %s"
        params = (anio, semana)
    
    elif tipo == 'mensual':
        anio, mes = validar_fecha_mensual(fecha)
        if not anio or not mes:
            return jsonify({'error': 'Fecha inválida para mensual (YYYY-MM)'}), 400
        filtro_fecha = "YEAR(v.FECHA_VENTA) = %s AND MONTH(v.FECHA_VENTA) = %s"
        filtro_fecha_compra = "YEAR(c.FECHA_COMPRA) = %s AND MONTH(c.FECHA_COMPRA) = %s"
        params = (anio, mes)
    
    else:
        return jsonify({'error': 'Tipo inválido. Use diario, semanal o mensual'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Detalle de ventas
        query_ventas = f"""
            SELECT 
                v.FECHA_VENTA,
                p.NOMBRE AS producto,
                p.CATEGORIA,
                dv.CANTIDAD_VENTA,
                ROUND(dv.SUBTOTAL_VENTA / NULLIF(dv.CANTIDAD_VENTA, 0), 2) AS PRECIO,
                dv.SUBTOTAL_VENTA
            FROM venta v
            JOIN detalle_venta dv ON v.ID_VENTA = dv.ID_VENTA
            JOIN producto p ON dv.ID_PRODUCTO = p.ID_PRODUCTO
            WHERE {filtro_fecha} AND v.ESTADO = 'FINALIZADA'
        """
        cursor.execute(query_ventas, params)
        ventas = cursor.fetchall()
        total_ventas = sum(v['SUBTOTAL_VENTA'] for v in ventas)

        # Detalle de compras
        query_compras = f"""
            SELECT 
                c.FECHA_COMPRA,
                pr.NOMBRE AS proveedor,
                p.NOMBRE AS producto,
                dc.CANTIDAD_COMPRA,
                dc.SUBTOTAL_COMPRA
            FROM compra c
            JOIN detalle_compra dc ON c.ID_COMPRA = dc.ID_COMPRA
            JOIN producto p ON dc.ID_PRODUCTO = p.ID_PRODUCTO
            JOIN proveedor pr ON c.ID_PROVEEDOR = pr.ID_PROVEEDOR
            WHERE {filtro_fecha_compra}
        """
        cursor.execute(query_compras, params)
        compras = cursor.fetchall()
        total_compras = sum(c['SUBTOTAL_COMPRA'] for c in compras)

        cursor.close()
        conn.close()

        return jsonify({
            'ventas': ventas,
            'totalVentas': total_ventas,
            'compras': compras,
            'totalCompras': total_compras
        })

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


# CIERRE DE CAJA __________________________________________________________________________________________________________________________
@app.route('/api/cierre-caja', methods=['GET'])
def cierre_caja():
    if request.headers.get('X-User-Role') not in ('Administrador', 'Cajero'):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        hoy = date.today()

        cursor.execute("""
            SELECT COUNT(*) AS total_ventas, IFNULL(SUM(TOTAL_VENTA), 0) AS total_ingresos
            FROM venta WHERE DATE(FECHA_VENTA) = %s AND ESTADO = 'FINALIZADA'
        """, (hoy,))
        resumen = cursor.fetchone()

        cursor.execute("""
            SELECT TIPO_VENTA, COUNT(*) AS cantidad, SUM(TOTAL_VENTA) AS total
            FROM venta WHERE DATE(FECHA_VENTA) = %s AND ESTADO = 'FINALIZADA'
            GROUP BY TIPO_VENTA
        """, (hoy,))
        desglose = cursor.fetchall()

        cursor.execute("""
            SELECT p.NOMBRE, SUM(dv.CANTIDAD_VENTA) AS vendido
            FROM detalle_venta dv
            JOIN producto p ON dv.ID_PRODUCTO = p.ID_PRODUCTO
            JOIN venta v ON dv.ID_VENTA = v.ID_VENTA
            WHERE DATE(v.FECHA_VENTA) = %s AND v.ESTADO = 'FINALIZADA'
            GROUP BY p.ID_PRODUCTO
            ORDER BY vendido DESC LIMIT 5
        """, (hoy,))
        mas_vendidos = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS pendientes FROM venta
            WHERE DATE(FECHA_VENTA) = %s AND ESTADO = 'EN ESPERA'
        """, (hoy,))
        pendientes = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            'fecha': hoy.isoformat(),
            'total_ventas': resumen['total_ventas'],
            'total_ingresos': float(resumen['total_ingresos']),
            'desglose_por_tipo': desglose,
            'productos_mas_vendidos': mas_vendidos,
            'pedidos_pendientes': pendientes['pendientes']
        })
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500


# ESTO ENDPOINT  PERTENECE A LA CARGA DE empleadoS DE VENTAS__________________________________________________________________________________________
@app.route('/api/empleados', methods=['GET'])
def obtener_empleados():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ID_EMPLEADO, NOMBRE, APELLIDOS FROM empleado")
        empleados = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(empleados)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

# ESTOS ENPOINTS PERTENECEN A LA VENTANA DE CONFIGURACION.HTML _____________________________________
# Endpoint para mostrar todos los empleados
@app.route('/empleados', methods=['GET'])
def mostrar_empleados():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ID_EMPLEADO, NOMBRE, APELLIDOS, EMAIL, PUESTO FROM empleado")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(empleados)

# Endpoint para agregar un nuevo empleado
@app.route('/empleados', methods=['POST'])
def agregar_empleado():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    data = request.json
    nombre = data.get('nombre')
    apellidos = data.get('apellidos')
    email = data.get('email')
    contraseña = data.get('password')
    puesto = data.get('puesto')

    if not (nombre and apellidos and email and contraseña and puesto):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Insertar nuevo empleado
    sql = "INSERT INTO empleado (NOMBRE, APELLIDOS, EMAIL, CONTRASEÑA, PUESTO) VALUES (%s, %s, %s, %s, %s)"
    try:
        cursor.execute(sql, (nombre, apellidos, email, generate_password_hash(contraseña), puesto))
        conn.commit()
    except mysql.connector.Error as err:
        cursor.close()
        conn.close()
        return jsonify({'error': str(err)}), 500

    cursor.close()
    conn.close()

    return jsonify({'message': 'empleado agregado exitosamente'}), 201

@app.route('/empleados/<int:id>', methods=['PUT'])
def actualizar_empleado(id):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        if data.get('password'):
            sql = """UPDATE empleado SET NOMBRE=%s, APELLIDOS=%s, EMAIL=%s, CONTRASEÑA=%s, PUESTO=%s WHERE ID_EMPLEADO=%s"""
            cursor.execute(sql, (data['nombre'], data['apellidos'], data['email'], generate_password_hash(data['password']), data['puesto'], id))
        else:
            sql = """UPDATE empleado SET NOMBRE=%s, APELLIDOS=%s, EMAIL=%s, PUESTO=%s WHERE ID_EMPLEADO=%s"""
            cursor.execute(sql, (data['nombre'], data['apellidos'], data['email'], data['puesto'], id))
        conn.commit()
        return jsonify({"message": "empleado actualizado exitosamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/empleados/<int:id>', methods=['DELETE'])
def eliminar_empleado(id):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM empleado WHERE ID_EMPLEADO = %s", (id,))
        conn.commit()
        return jsonify({"message": "empleado eliminado exitosamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Ruta de prueba
@app.route('/api/test')
def test_conexion():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        if conn.is_connected():
            return jsonify({"mensaje": "Conexión exitosa a MySQL en puerto 3306"})
        else:
            return jsonify({"error": "No se pudo conectar"})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)})

# ==============================================================================
# EXTRANET ENDPOINTS (PROVEEDORES)
# ==============================================================================

@app.route('/api/extranet/login', methods=['POST', 'OPTIONS'])
def extranet_login():
    if request.method == 'OPTIONS':
        return '', 200
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM proveedor WHERE EMAIL = %s", (email,))
        prov = cursor.fetchone()

        if prov:
            stored = prov["CONTRASEÑA"]
            if stored.startswith("pbkdf2:") or stored.startswith("scrypt:") or stored.startswith("$2"):
                valida = check_password_hash(stored, password)
            else:
                valida = (stored == password)
                if valida:
                    cursor.execute(
                        "UPDATE proveedor SET CONTRASEÑA = %s WHERE ID_PROVEEDOR = %s",
                        (generate_password_hash(password), prov["ID_PROVEEDOR"])
                    )
                    conn.commit()
        else:
            valida = False

        cursor.close()
        conn.close()

        if prov and valida:
            return jsonify({
                "mensaje": "Login exitoso",
                "proveedor": {
                    "id": prov["ID_PROVEEDOR"],
                    "nombre": prov["NOMBRE"],
                    "email": prov["EMAIL"]
                }
            })
        else:
            return jsonify({"error": "Credenciales inválidas"}), 401
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

def verificar_proveedor(request, id_proveedor):
    prov_id = request.headers.get('X-Proveedor-Id')
    return prov_id is not None and str(prov_id) == str(id_proveedor)

@app.route('/api/extranet/productos/<int:id_proveedor>', methods=['GET'])
def extranet_obtener_productos(id_proveedor):
    if not verificar_proveedor(request, id_proveedor):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * FROM producto
        WHERE ID_PROVEEDOR = %s
        """
        cursor.execute(query, (id_proveedor,))
        productos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/extranet/productos/<int:id_proveedor>', methods=['POST'])
def extranet_agregar_producto(id_proveedor):
    if not verificar_proveedor(request, id_proveedor):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion', '')
            categoria = request.form.get('categoria', 'Ensaladas')
            precio = request.form.get('precio', 0)
            imagen_file = request.files.get('imagen')
            if imagen_file and imagen_file.filename:
                filename = f"{int(time.time())}_{secure_filename(imagen_file.filename)}"
                ruta_imagen = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen_file.save(ruta_imagen)
            else:
                filename = ''
        else:
            data = request.json
            nombre = data.get('nombre')
            descripcion = data.get('descripcion', '')
            categoria = data.get('categoria', 'Ensaladas')
            precio = data.get('precio', 0)
            filename = data.get('imagen', '')

        conn = get_db()
        cursor = conn.cursor()
        
        # Insertar producto PENDIENTE (sin vincular aún a producto_proveedor)
        query_prod = """
        INSERT INTO producto (NOMBRE, DESCRIPCION, CATEGORIA, CANTIDAD, PRECIO, IMAGEN, ESTADO_APROBACION, ID_PROVEEDOR)
        VALUES (%s, %s, %s, %s, %s, %s, 'PENDIENTE', %s)
        """
<<<<<<< HEAD
        cursor.execute(query_prod, (nombre, descripcion, categoria, cantidad, precio, imagen, id_proveedor))
=======
        cursor.execute(query_prod, (nombre, descripcion, categoria, 0, precio, filename))
>>>>>>> bb77722d4179b47229964e1c0b5133bf97e29a88
        id_producto = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'id_producto': id_producto})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/extranet/productos/<int:id_producto>', methods=['PUT'])
def extranet_editar_producto(id_producto):
    prov_id = request.headers.get('X-Proveedor-Id')
    if not prov_id:
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM producto_proveedor WHERE ID_PRODUCTO = %s AND ID_PROVEEDOR = %s", (id_producto, prov_id))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Acceso denegado'}), 403
        
        data = request.json
        nombre = data.get('nombre')
        precio = data.get('precio')
        cursor.execute("UPDATE producto SET NOMBRE = %s, PRECIO = %s WHERE ID_PRODUCTO = %s", (nombre, precio, id_producto))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/extranet/productos/<int:id_producto>/<int:id_proveedor>', methods=['DELETE'])
def extranet_eliminar_producto(id_producto, id_proveedor):
    if not verificar_proveedor(request, id_proveedor):
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor()
<<<<<<< HEAD
        cursor.execute("DELETE FROM producto WHERE ID_PRODUCTO = %s AND ID_PROVEEDOR = %s", (id_producto, id_proveedor))
        # (producto_proveedor se borra por CASCADE)
=======
        query_unlink = "DELETE FROM producto_proveedor WHERE ID_PRODUCTO = %s AND ID_PROVEEDOR = %s"
        cursor.execute(query_unlink, (id_producto, id_proveedor))
>>>>>>> bb77722d4179b47229964e1c0b5133bf97e29a88
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================================================================
# APROBACIONES ADMIN
# ==============================================================================

@app.route('/api/productos/pendientes', methods=['GET'])
def obtener_productos_pendientes():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT p.*, pr.NOMBRE as proveedor_nombre 
        FROM producto p
        LEFT JOIN proveedor pr ON p.ID_PROVEEDOR = pr.ID_PROVEEDOR
        WHERE p.ESTADO_APROBACION = 'PENDIENTE'
        """
        cursor.execute(query)
        pendientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(pendientes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/productos/<int:id_producto>/aprobar', methods=['PUT'])
def aprobar_producto(id_producto):
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = request.json
        estado = data.get('estado', 'APROBADO')
        conn = get_db()
        cursor = conn.cursor()

        if estado == 'RECHAZADO':
            cursor.execute("DELETE FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
        else:
            cursor.execute("SELECT ID_PROVEEDOR FROM producto WHERE ID_PRODUCTO = %s", (id_producto,))
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute("INSERT IGNORE INTO producto_proveedor (ID_PRODUCTO, ID_PROVEEDOR) VALUES (%s, %s)", (id_producto, row[0]))
            cursor.execute("UPDATE producto SET ESTADO_APROBACION = %s WHERE ID_PRODUCTO = %s", (estado, id_producto))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/db/config')
def db_config_view():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    return f'''<h1>Config BD</h1>
<pre>
Host: {os.environ.get('DB_HOST', 'localhost')}
Port: {os.environ.get('DB_PORT', 3306)}
User: {os.environ.get('DB_USER', 'root')}
Password: {os.environ.get('DB_PASSWORD', '(vacia)')}
Database: {os.environ.get('DB_NAME', 'sweetfit')}
</pre>
<p>Usa estos datos en DBeaver > New Connection > MySQL</p>'''

@app.route('/db/migrate')
def db_migrate():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    """Agrega columnas para pedidos web a la tabla venta si no existen."""
    resultados = []
    try:
        conn = get_db()
        c = conn.cursor()
        migraciones = [
            "ALTER TABLE venta ADD COLUMN NOMBRE_CLIENTE_WEB VARCHAR(255)",
            "ALTER TABLE venta ADD COLUMN TELEFONO_CLIENTE_WEB VARCHAR(20)",
            "ALTER TABLE venta ADD COLUMN NOTAS_PEDIDO TEXT",
            "ALTER TABLE venta ADD COLUMN DIRECCION_CLIENTE_WEB TEXT",
            "ALTER TABLE producto ADD COLUMN ID_PROVEEDOR INT"
        ]
        for sql in migraciones:
            try:
                c.execute(sql)
                col = sql.split("ADD COLUMN ")[1].split(" ")[0]
                resultados.append(f"Columna {col} agregada")
            except Exception as e:
                if "Duplicate column" in str(e):
                    resultados.append(f"Columna ya existe")
                else:
                    resultados.append(f"Error: {e}")
        conn.commit()
        c.close()
        conn.close()
        return jsonify({"mensaje": "Migración completada", "detalles": resultados})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/db/seed')
def db_seed():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta
    import random
    seed = []
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute("SET FOREIGN_KEY_CHECKS = 0")
        for t in ['detalle_compra','detalle_venta','compra','venta','producto_proveedor','producto','proveedor','cliente','empleado']:
            c.execute(f"DELETE FROM {t}")
        c.execute("SET FOREIGN_KEY_CHECKS = 1")

        c.execute("ALTER TABLE empleado MODIFY CONTRASEÑA VARCHAR(255)")

        # Agregar columnas para datos de pedidos web si no existen
        try:
            c.execute("ALTER TABLE venta ADD COLUMN NOMBRE_CLIENTE_WEB VARCHAR(255)")
        except:
            pass
        try:
            c.execute("ALTER TABLE venta ADD COLUMN TELEFONO_CLIENTE_WEB VARCHAR(20)")
        except:
            pass
        try:
            c.execute("ALTER TABLE venta ADD COLUMN NOTAS_PEDIDO TEXT")
        except:
            pass
        try:
            c.execute("ALTER TABLE venta ADD COLUMN DIRECCION_CLIENTE_WEB TEXT")
        except:
            pass
        c.executemany("INSERT INTO empleado (ID_EMPLEADO,NOMBRE,APELLIDOS,EMAIL,CONTRASEÑA,PUESTO) VALUES (%s,%s,%s,%s,%s,%s)", [
            (1,'Admin','Sweetfit','admin@sweetfit.com',generate_password_hash('admin123'),'Administrador'),
            (2,'Cajero','Sweetfit','cajero@sweetfit.com',generate_password_hash('cajero123'),'Cajero'),
            (3,'María','López García','maria@sweetfit.com',generate_password_hash('maria123'),'Cajero'),
            (4,'Carlos','Martínez Ruiz','carlos@sweetfit.com',generate_password_hash('carlos123'),'Cajero'),
            (5,'Ana','Hernández Cruz','ana@sweetfit.com',generate_password_hash('ana123'),'Administrador'),
        ])
        seed.append('5 empleados')

        c.executemany("INSERT INTO proveedor (ID_PROVEEDOR,EMAIL,TELEFONO,NOMBRE,CONTRASEÑA) VALUES (%s,%s,%s,%s,%s)", [
            (1,'contacto@greenfields.com','2291112233','Green Fields Orgánicos',generate_password_hash('12345')),
            (2,'ventas@fitprotein.com','2292223344','Fit Protein Supply',generate_password_hash('12345')),
            (3,'pedidos@vitalJuice.com','2293334455','Vital Juice Co.',generate_password_hash('12345')),
            (4,'distribucion@naturalsnack.com','2294445566','Natural Snack Distribución',generate_password_hash('12345')),
            (5,'ventas@superfoods.mx','2295556677','Superfoods México',generate_password_hash('12345')),
            (6,'contacto@dairyfit.com','2296667788','DairyFit Lácteos',generate_password_hash('12345')),
        ])
        seed.append('6 proveedores')

        c.executemany("INSERT INTO cliente (ID_CLIENTE,NOMBRE,APELLIDO_PATERNO,APELLIDO_MATERNO,DIRECCION,TELEFONO) VALUES (%s,%s,%s,%s,%s,%s)", [
            (1,'Juan','Pérez','García','Calle 1 #123, Centro','2291000100'),
            (2,'María','López','Martínez','Av. 2 #456, Reforma','2291000200'),
            (3,'Carlos','Ramírez',None,'Blvd. 3 #789, Costa de Oro','2291000300'),
            (4,'Ana','Torres','Mendoza','Calle 5 #234, Las Ánimas','2291000400'),
            (5,'Luis','Fernández','Herrera','Av. 6 #567, Faros','2291000500'),
            (6,'Sofía','García','Ríos','Calle 7 #890, Reforma','2291000600'),
            (7,'Miguel','Álvarez','Nieto','Blvd. 8 #123, Costa Verde','2291000700'),
            (8,'Diana','Morales','Castillo','Calle 9 #456, Centro','2291000800'),
            (9,'Roberto','Cruz','Vega','Av. 10 #789, Las Brisas','2291000900'),
            (10,'Laura','Jiménez','Ortega','Calle 11 #321, Reforma','2291001000'),
        ])
        seed.append('10 clientes')

        c.executemany("INSERT INTO producto (ID_PRODUCTO,NOMBRE,DESCRIPCION,CATEGORIA,CANTIDAD,PRECIO,IMAGEN,ESTADO_APROBACION,ID_PROVEEDOR) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", [
            (1,'Ensalada Caesar Fit','Lechuga romana, pollo grillé, crutones integrales, aderezo light','Ensaladas',25,79.00,'aderezo.jpg','APROBADO',1),
            (2,'Bowl Verde','Quinoa, espinaca, aguacate, pepino, brócoli y vinagreta de limón','Bowls',20,89.00,'aguacate.jpg','APROBADO',1),
            (3,'Pechuga Empanizada','Pechuga de pollo empanizada con avena, horneada no frita','Proteína',30,79.00,'pechuga.jpg','APROBADO',2),
            (4,'Salmón a la Plancha','Filete de salmón fresco con especias y vegetales salteados','Proteína',15,119.00,'atun.jpg','APROBADO',2),
            (5,'Barrita Proteica','Barrita de proteína vegetal, sin azúcar añadida','Snacks Fit',50,29.00,'barritas_proteicas.jpg','APROBADO',1),
            (6,'Green Smoothie','Espinaca, piña, manzana verde y jengibre','Jugos y Licuados',30,55.00,'Extra_Naranja.jpg','APROBADO',3),
            (7,'Limonada con Chía','Limonada natural con semillas de chía y stevia','Bebidas',40,35.00,'naranja_miel.jpg','APROBADO',3),
            (8,'Palomitas de Aire','Palomitas de maíz sin aceite, con sal de mar y romero','Snacks Fit',50,25.00,'palomitas_aire.jpg','APROBADO',1),
            (9,'Protein Shake','Licuado de proteína vegetal, plátano y leche de almendras','Jugos y Licuados',20,65.00,'leche_coco.jpg','APROBADO',3),
            (10,'Ensalada de Atún (Propuesta)','Ensalada de atún fresco con mezcla de verdes, pepino y jitomate cherry','Ensaladas',40,45.00,'Deli_Tuna_CH.jpg','PENDIENTE',1),
            (11,'Pack Protein Bars (Propuesta)','Pack 12 barritas proteicas sabor chocolate y vainilla','Snacks Fit',60,25.00,'Tentacion_CH.jpg','PENDIENTE',2),
            (12,'Bowl de Frutos Rojos','Açaí, frutos rojos, granola, plátano y miel de agave','Bowls',18,95.00,'De_la_Casa_CH.jpg','APROBADO',5),
            (13,'Wrap de Pollo Fit','Tortilla integral, pollo, espinaca, jitomate y aderezo yogurt','Ensaladas',22,69.00,'Wraps_Pollo.jpg','APROBADO',1),
            (14,'Huevos Revueltos Fit','Huevos revueltos con espinaca, champiñones y pan integral','Proteína',20,59.00,'huevo_revueltos.jpg','APROBADO',6),
            (15,'Batido de Mango','Mango, leche de coco y proteína vegetal','Jugos y Licuados',25,58.00,'Agua_especial.jpg','APROBADO',3),
            (16,'Té Helado Natural','Té verde, limón y stevia, sin azúcar añadida','Bebidas',45,28.00,'Agua_del_Dia.jpg','APROBADO',6),
            (17,'Almendras Especiadas','Almendras tostadas con romero y sal de mar','Snacks Fit',35,38.00,'Gelatina_light.jpg','APROBADO',4),
            (18,'Bowl Energético','Quinoa, pollo, aguacate, mango y vinagreta cítrica','Bowls',15,99.00,'Gourmet_GDE.jpg','APROBADO',5),
            (19,'Tostadas de Aguacate','Pan integral, aguacate, huevo poché y microverdes','Ensaladas',20,65.00,'avocado_toast.jpg','APROBADO',1),
            (20,'Pechuga BBQ Light','Pechuga bañada en salsa BBQ sin azúcar, horneada','Proteína',18,85.00,'pechuga_asada.jpg','APROBADO',2),
            (21,'Smoothie de Fresa','Fresa, plátano, leche de almendras y proteína','Jugos y Licuados',22,60.00,'Gourmet_CH.jpg','APROBADO',3),
            (22,'Agua de Jamaica','Agua fresca de jamaica endulzada con stevia','Bebidas',50,20.00,'Agua_embotellada.jpg','APROBADO',6),
            (23,'Mix Frutos Secos','Nuez, almendra, cacahuate y arándano deshidratado','Snacks Fit',40,35.00,'malangas_horneadas.jpg','APROBADO',4),
            (24,'Chía Pudding','Pudín de chía con leche de coco y frutos rojos','Bowls',25,55.00,'De_la_Casa_GDE.jpg','APROBADO',5),
            (25,'Wrap Vegetariano','Tortilla integral, hummus, verduras asadas y rúcula','Ensaladas',20,62.00,'toast_tres_quesos.jpg','APROBADO',6),
        ])
        seed.append('25 productos')

        # Solo vincular en producto_proveedor los productos APROBADOS (los PENDIENTE se vinculan al aprobarse)
        prov_prods = [
            (1,1),(1,2),(1,5),(1,8),(1,13),(1,19),
            (2,3),(2,4),(2,20),
            (3,6),(3,7),(3,9),(3,15),(3,21),
            (4,17),(4,23),
            (5,12),(5,18),(5,24),
            (6,14),(6,16),(6,22),(6,25),
        ]
        c.executemany("INSERT INTO producto_proveedor (ID_PRODUCTO,ID_PROVEEDOR) VALUES (%s,%s)", prov_prods)
        seed.append(f'{len(prov_prods)} relaciones producto-proveedor')

        hoy = datetime.now()
        ventas_datos = [
            (1,1,'Local',178.00,hoy-timedelta(days=1),2,'FINALIZADA'),
            (2,2,'Domicilio',89.00,hoy,2,'FINALIZADA'),
            (3,3,'Local',128.00,hoy-timedelta(days=2),2,'EN ESPERA'),
            (4,1,'App',49.00,hoy-timedelta(days=3),1,'CANCELADA'),
            (5,2,'Local',124.00,hoy,1,'FINALIZADA'),
            (6,4,'Local',158.00,hoy-timedelta(days=4),3,'FINALIZADA'),
            (7,5,'Domicilio',212.00,hoy-timedelta(days=5),3,'FINALIZADA'),
            (8,6,'Local',95.00,hoy-timedelta(days=6),2,'EN ESPERA'),
            (9,7,'App',145.00,hoy-timedelta(days=7),1,'FINALIZADA'),
            (10,8,'Local',67.00,hoy-timedelta(days=8),4,'FINALIZADA'),
            (11,9,'Domicilio',234.00,hoy-timedelta(days=10),5,'FINALIZADA'),
            (12,10,'Local',88.00,hoy-timedelta(days=12),2,'FINALIZADA'),
            (13,3,'App',176.00,hoy-timedelta(days=14),3,'FINALIZADA'),
            (14,5,'Local',310.00,hoy-timedelta(days=18),1,'FINALIZADA'),
            (15,7,'Domicilio',129.00,hoy-timedelta(days=21),4,'CANCELADA'),
        ]
        c.executemany("INSERT INTO venta (ID_VENTA,ID_CLIENTE,TIPO_VENTA,TOTAL_VENTA,FECHA_VENTA,ID_EMPLEADO,ESTADO) VALUES (%s,%s,%s,%s,%s,%s,%s)", ventas_datos)
        seed.append(f'{len(ventas_datos)} ventas')

        dventas = [
            (1,79.00,1,1,1),(2,89.00,1,1,2),(3,79.00,1,2,3),(4,89.00,1,3,2),
            (5,29.00,1,3,5),(6,55.00,1,4,6),(7,79.00,1,5,1),(8,25.00,1,5,8),
            (9,79.00,1,6,3),(10,79.00,1,6,1),(11,89.00,2,7,2),(12,35.00,2,7,7),
            (13,28.00,1,7,16),(14,55.00,1,8,6),(15,29.00,1,8,5),(16,35.00,1,8,7),
            (17,65.00,1,9,9),(18,79.00,1,9,1),(19,69.00,1,10,13),(20,65.00,1,11,9),
            (21,79.00,1,11,4),(22,89.00,1,11,2),(23,55.00,1,12,24),(24,28.00,1,12,16),
            (25,35.00,1,12,7),(26,89.00,1,13,2),(27,79.00,1,13,3),(28,119.00,1,14,4),
            (29,79.00,1,14,20),(30,55.00,1,14,24),(31,55.00,1,14,6),(32,79.00,1,15,3),
            (33,38.00,1,15,17),(34,28.00,1,15,22),
        ]
        c.executemany("INSERT INTO detalle_venta (ID_DETVENTA,SUBTOTAL_VENTA,CANTIDAD_VENTA,ID_VENTA,ID_PRODUCTO) VALUES (%s,%s,%s,%s,%s)", dventas)
        seed.append(f'{len(dventas)} detalles de venta')

        compras_datos = [
            (1,hoy-timedelta(days=5),315.00,1,1),
            (2,hoy-timedelta(days=2),450.00,1,2),
            (3,hoy-timedelta(days=8),520.00,4,1),
            (4,hoy-timedelta(days=10),380.00,4,3),
            (5,hoy-timedelta(days=12),600.00,1,4),
            (6,hoy-timedelta(days=15),275.00,2,5),
            (7,hoy-timedelta(days=20),340.00,2,6),
            (8,hoy-timedelta(days=25),490.00,4,2),
            (9,hoy-timedelta(days=30),250.00,1,3),
            (10,hoy-timedelta(days=35),180.00,2,4),
        ]
        c.executemany("INSERT INTO compra (ID_COMPRA,FECHA_COMPRA,TOTAL_COMPRA,ID_EMPLEADO,ID_PROVEEDOR) VALUES (%s,%s,%s,%s,%s)", compras_datos)
        seed.append(f'{len(compras_datos)} compras')

        dcompras = [
            (1,450.00,10,1,1),(2,350.00,10,6,1),(3,250.00,10,5,1),(4,790.00,10,3,2),
            (5,520.00,8,2,3),(6,380.00,5,4,3),(7,600.00,12,1,4),(8,275.00,5,9,5),
            (9,340.00,10,16,6),(10,490.00,7,3,7),(11,250.00,5,8,8),(12,180.00,6,7,9),
            (13,300.00,6,20,1),(14,450.00,6,12,5),
        ]
        c.executemany("INSERT INTO detalle_compra (ID_DETCOMPRA,SUBTOTAL_COMPRA,CANTIDAD_COMPRA,ID_PRODUCTO,ID_COMPRA) VALUES (%s,%s,%s,%s,%s)", dcompras)
        seed.append(f'{len(dcompras)} detalles de compra')

        c.execute("UPDATE producto SET CANTIDAD = CANTIDAD - 1 WHERE ID_PRODUCTO IN (1,2,3,5,6,8)")
        c.execute("UPDATE producto SET CANTIDAD = CANTIDAD + 10 WHERE ID_PRODUCTO IN (1,3,5,6)")

        conn.commit()
        c.close()
        conn.close()

        html = '<h1>Seed completado</h1><ul>'
        for s in seed:
            html += f'<li>{s}</li>'
        html += '</ul><p><b>Admin:</b> admin@sweetfit.com / admin123</p><p><b>Cajero:</b> cajero@sweetfit.com / cajero123</p><p><a href=/db>Ver BD</a></p>'
        return html
    except Exception as e:
        return f'<h1>Error</h1><pre>{e}</pre>'

@app.route('/db')
def db_explorer():
    if request.headers.get('X-User-Role') != 'Administrador':
        return jsonify({'error': 'Acceso denegado'}), 403
    tables = ['empleado','cliente','proveedor','producto','venta','detalle_venta','compra','detalle_compra']
    html = '<h1>Sweetfit - BD Explorer</h1>'
    try:
        conn = get_db()
        c = conn.cursor(dictionary=True)
        for t in tables:
            c.execute(f'SELECT * FROM {t} ORDER BY 1 DESC LIMIT 50')
            rows = c.fetchall()
            html += f'<h2 style="margin-top:30px">{t.upper()}</h2><table border="1" cellpadding="6" style="border-collapse:collapse;width:100%"><tr>'
            if rows:
                for k in rows[0]:
                    html += f'<th style="background:#eee">{k}</th>'
                html += '</tr>'
                for r in rows:
                    html += '<tr>'
                    for v in r.values():
                        html += f'<td>{str(v)[:60] if v else "-"}</td>'
                    html += '</tr>'
            html += '</table>'
        c.close()
        conn.close()
    except Exception as e:
        html += f'<p style="color:red">Error: {e}</p>'
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sweetfit DB</title></head><body style="font-family:sans-serif;padding:20px">{html}</body></html>'

# Ejecutar servidor
if __name__ == '__main__':
    app.run(debug=True)