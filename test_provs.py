import urllib.request
import json

try:
    with urllib.request.urlopen('http://localhost:5000/api/proveedores') as response:
        data = response.read()
        provs = json.loads(data)
        print("Proveedores:", len(provs))
        if provs:
            print(provs[0])
except Exception as e:
    print("Error:", e)
