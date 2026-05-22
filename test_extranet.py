import urllib.request
import json

# Probar login y luego obtener productos
login_data = json.dumps({"email": "contacto@greenfields.com", "password": "12345"}).encode('utf-8')
req = urllib.request.Request(
    'http://localhost:5000/api/extranet/login',
    data=login_data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        print("Login:", data)
        id_prov = data['proveedor']['id']
        
    # Obtener productos de ese proveedor
    with urllib.request.urlopen(f'http://localhost:5000/api/extranet/productos/{id_prov}') as resp:
        prods = json.loads(resp.read())
        print(f"Productos para proveedor {id_prov}: {len(prods)}")
        if prods:
            print("Ejemplo:", prods[0])
except Exception as e:
    print("Error:", e)
