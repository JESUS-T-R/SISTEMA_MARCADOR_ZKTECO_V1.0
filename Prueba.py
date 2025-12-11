import threading
import time
from zk import ZK, const

def descargar_registros(marcador):
    ip = marcador["ip"]
    puerto = marcador["puerto"]
    nombre = marcador["nombre"]

    print(f"\n🔌 Conectando a {nombre} ({ip}:{puerto})...")
    inicio = time.time()  # Tiempo de inicio individual

    try:
        zk = ZK(ip, port=puerto, timeout=180)
        conn = zk.connect()
        conn.disable_device()

        registros = conn.get_attendance()
        total = len(registros)

        fin = time.time()  # Tiempo de fin individual
        duracion = fin - inicio

        print(f"✅ {nombre}: {total} registros obtenidos en {duracion:.2f} segundos")

        conn.enable_device()
        conn.disconnect()

    except Exception as e:
        fin = time.time()
        duracion = fin - inicio
        print(f"❌ Error con {nombre}: {e} (Duración: {duracion:.2f} s)")

# Lista de marcadores
marcadores = [
    {"ip": "172.16.11.30", "puerto": 4370, "nombre": "Marcador A"},
    {"ip": "172.16.11.23", "puerto": 4370, "nombre": "Marcador B"},
    {"ip": "172.16.11.20", "puerto": 4370, "nombre": "Marcador C"},
]

# Tiempo total de ejecución
inicio_total = time.time()

# Crear e iniciar hilos
hilos = []
for m in marcadores:
    hilo = threading.Thread(target=descargar_registros, args=(m,))
    hilo.start()
    hilos.append(hilo)

# Esperar a que todos terminen
for hilo in hilos:
    hilo.join()

fin_total = time.time()
duracion_total = fin_total - inicio_total

print(f"\n🏁 Descarga completada desde todos los marcadores en {duracion_total:.2f} segundos totales.")
