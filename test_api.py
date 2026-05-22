import urllib.request, json, sys

BASE = 'http://localhost:5000'

def api(method, path, data=None, headers=None):
    body = json.dumps(data).encode() if data else None
    req_headers = {'Content-Type': 'application/json'} if data else {}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=req_headers)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {'ERROR': f'HTTP {e.code}: {e.read().decode()}'}
    except Exception as e:
        return {'ERROR': str(e)}

# 1. Login Admin
r = api('POST', '/api/login', {'email': 'admin@sweetfit.com', 'contraseña': 'admin123'})
print(f"[ADMIN LOGIN] {r.get('mensaje','ERROR')} | Puesto: {r.get('usuario',{}).get('puesto','?')}")

# 2. Login Cajero
r = api('POST', '/api/login', {'email': 'cajero@sweetfit.com', 'contraseña': 'cajero123'})
print(f"[CAJERO LOGIN] {r.get('mensaje','ERROR')} | Puesto: {r.get('usuario',{}).get('puesto','?')}")

# 3. Login fallido
r = api('POST', '/api/login', {'email': 'admin@sweetfit.com', 'contraseña': 'wrong'})
print(f"[LOGIN FALLIDO] {'OK' if 'error' in r else 'FALLA'}")

# 4. Extranet login proveedor
r = api('POST', '/api/extranet/login', {'email': 'contacto@greenfields.com', 'password': '12345'})
print(f"[EXTRANET LOGIN] {r.get('mensaje','ERROR')} | Proveedor: {r.get('proveedor',{}).get('nombre','?')}")

# 5. Dashboard
r = api('GET', '/api/dashboard')
print(f"[DASHBOARD] Ventas dia: ${r.get('ventas_dia',0)} | Clientes: {r.get('clientes_registrados',0)} | Prod: {r.get('productos_disponibles',0)}")

# 6. Productos
r = api('GET', '/api/productos')
print(f"[PRODUCTOS] {r.get('total_productos',0)} total")

# 7. Menú público
r = api('GET', '/api/menu')
cats = list(r.keys())
print(f"[MENU] Categorias: {cats}")

# 8. Ventas historial
r = api('GET', '/api/ventas')
print(f"[VENTAS] {len(r)} registradas")

# 9. Productos pendientes
r = api('GET', '/api/productos/pendientes')
print(f"[PENDIENTES] {len(r)} productos pendientes")

# 10. Reporte categorias
r = api('GET', '/api/reportes/categorias')
print(f"[REPORTE CATS] {len(r.get('categorias',[]))} categorias")

# 11. Reporte ventas
r = api('GET', '/api/reportes/ventas?tipo=diario')
print(f"[REPORTE VENTAS] {'OK' if 'ventas' in r else 'FALLA'} ({len(r.get('ventas',[]))} registros)")

# 12. Reporte productos mas vendidos
r = api('GET', '/api/reportes/productos-mas-vendidos')
print(f"[PROD MAS VENDIDOS] {'OK' if isinstance(r,list) else 'FALLA'} ({len(r) if isinstance(r,list) else 0} registros)")

# 13. Pedido online
r = api('POST', '/api/pedidos', {
    'nombre': 'Test', 'telefono': '2299999999', 'tipo_pedido': 'Local',
    'items': [{'id_producto': 2, 'cantidad': 1, 'precio': 79.00}]
})
print(f"[PEDIDO ONLINE] ID: {r.get('id_pedido','ERROR')}")

# 14. Registrar venta POS (admin auth)
r = api('POST', '/api/ventas', {
    'cliente': {'nombre':'Test','apellido_paterno':'POS','apellido_materno':'','direccion':'','telefono':'2298888888'},
    'carrito': [{'id': 2, 'cantidad': 1, 'subtotal': 79.00}, {'id': 3, 'cantidad': 1, 'subtotal': 49.00}],
    'empleado': 'Admin Sweetfit',
    'tipo_venta': 'Local',
    'estado': 'FINALIZADA'
}, headers={'X-User-Role': 'Administrador', 'X-User-Id': '1'})
print(f"[VENTA POS] ID: {r.get('id_venta','ERROR')}")

# 15. Detalle venta
if 'id_venta' in r:
    r2 = api('GET', f'/api/ventas/{r["id_venta"]}')
    print(f"[DETALLE VENTA] Orden: {r2.get('orden','?')} | Cliente: {r2.get('cliente','?')}")

# 16. Compras historial
r = api('GET', '/api/compras')
print(f"[COMPRAS] {len(r)} registradas")

print("\n=== TODOS LOS TEST COMPLETADOS ===")
