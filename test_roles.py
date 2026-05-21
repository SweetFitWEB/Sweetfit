import urllib.request, json

BASE = 'http://localhost:5000'

def api(method, path, data=None, headers=None):
    body = json.dumps(data).encode() if data else None
    hdrs = {'Content-Type': 'application/json'} if data else {}
    if headers: hdrs.update(headers)
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=hdrs)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'ERROR': f'HTTP {e.code}: {e.read().decode()}'}
    except Exception as e:
        return {'ERROR': str(e)}

# 1. Cierre de caja (sin auth - deberia fallar)
print("1. CIERRE CAJA sin auth:", json.dumps(api('GET', '/api/cierre-caja')))

# 2. Cierre de caja (como admin)
print("2. CIERRE CAJA admin:", json.dumps(api('GET', '/api/cierre-caja', headers={'X-User-Role': 'Administrador'})))

# 3. Cierre de caja (como cajero)
print("3. CIERRE CAJA cajero:", json.dumps(api('GET', '/api/cierre-caja', headers={'X-User-Role': 'Cajero'})))

# 4. Historial ventas (como cajero - deberia fallar 403)
print("4. HISTORIAL cajero:", api('GET', '/api/ventas/historial', headers={'X-User-Role': 'Cajero'}))

# 5. Historial ventas (como admin)
print("5. HISTORIAL admin:", api('GET', '/api/ventas/historial', headers={'X-User-Role': 'Administrador'}))

# 6. Eliminar producto (como cajero - deberia fallar)
print("6. ELIMINAR PROD cajero:", api('DELETE', '/api/eliminar_producto/1', headers={'X-User-Role': 'Cajero'}))

# 7. Eliminar producto (como admin)
print("7. ELIMINAR PROD admin:", api('DELETE', '/api/eliminar_producto/1', headers={'X-User-Role': 'Administrador'}))
