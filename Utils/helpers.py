# Utils/helpers.py  (versión corregida)
from datetime import datetime
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw
import pystray


LOCK_FILE = 'app.lock'
ventana_tk = None
icono_bandeja = None

def redondear_timestamp(ts): return ts.replace(microsecond=0)

def fecha_valida(fecha_str): return datetime.fromisoformat(fecha_str) if fecha_str else None

def obtener_ultimo_registro(cur, marcador_id):
    cur.execute("SELECT MAX(timestamp) FROM asistencias WHERE marcador_id = ?;", (marcador_id,))
    (max_ts,) = cur.fetchone()
    return fecha_valida(max_ts)

# ---------------- resource_path ----------------
def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta al recurso:
    - Si se está corriendo desde un EXE creado con PyInstaller, usa sys._MEIPASS.
    - Si se está corriendo desde .py, resuelve relativo al directorio del script (cwd).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------- mostrar_splash ----------------
def mostrar_splash(imagen_path: str, duracion_ms: int) -> None:
    """
    Muestra un splash usando tk.PhotoImage. imagen_path puede ser:
      - "logo.png"
      - "assets/logo.png"
    La función buscará el recurso usando resource_path() y verificará existencia.
    Nota: tk.PhotoImage acepta .png o .gif (no .jpg).
    """
    ruta = resource_path(imagen_path)

    if not os.path.exists(ruta):
        # imprimir ruta para debugging y evitar crash
        print(f"❌ mostrar_splash: no existe el archivo de imagen: {ruta}")
        return

    splash = tk.Tk()
    splash.overrideredirect(True)

    try:
        imagen = tk.PhotoImage(file=ruta)  # .png o .gif
    except Exception as e:
        print(f"❌ Error al cargar imagen en mostrar_splash({ruta}): {e}")
        splash.destroy()
        return

    label = ttk.Label(splash, image=imagen)
    label.image = imagen
    label.pack()

    splash.update_idletasks()
    w, h = splash.winfo_width(), splash.winfo_height()
    x = (splash.winfo_screenwidth() - w) // 2
    y = (splash.winfo_screenheight() - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    splash.after(duracion_ms, splash.destroy)
    splash.mainloop()

def dentro_del_rango_permitido(ts: datetime) -> bool:
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    inicio = datetime(2025, 7, 21)
    fin = datetime.now()
    return inicio <= ts <= fin

# ---------------- extracción de recursos (opcional) ----------------
def extraer():
    """Copia assets/logo.png a cwd/logo.png si aún no existe (útil para desarrollo)."""
    origen = Path(resource_path("assets/logo.png"))
    destino = Path.cwd() / "logo.png"
    try:
        if destino.exists():
            return
        shutil.copy(origen, destino)
    except Exception as e:
        print(f"❌  No se pudo copiar logo.png: {e}")

def extraer_icono():
    """Copia assets/icono.ico a cwd/icono.ico si aún no existe."""
    origen = Path(resource_path("assets/icono.ico"))
    destino = Path.cwd() / "icono.ico"
    try:
        if destino.exists():
            return
        shutil.copy(origen, destino)
    except Exception as e:
        print(f"❌  No se pudo copiar icono.ico: {e}")

# ---------------- ping host ----------------
def ping_host(ip, timeout=1):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        # En windows -w espera ms, en linux -W espera segundos (aquí forzamos ms only para windows)
        if platform.system().lower() == "windows":
            result = subprocess.run(["ping", param, "1", "-w", str(timeout * 1000), ip],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            result = subprocess.run(["ping", param, "1", ip],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout+1)
        return result.returncode == 0
    except Exception:
        return False
