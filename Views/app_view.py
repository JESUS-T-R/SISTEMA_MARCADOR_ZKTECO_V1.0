from datetime import date, datetime
import os
import threading
import tkinter as tk
from tkinter import Image, ttk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageDraw
from tkinter import scrolledtext
import psutil
import pystray
from tkcalendar import DateEntry
from zk import ZK
from Utils.helpers import resource_path


ventana_tk = None
icono_bandeja = None

LOCK_FILE = 'app.lock'
class MarcadorView:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.thread = None
        self.controller = None
        self.root.geometry("780x600") 
        self.root.iconbitmap(resource_path("icono.ico"))
                # Crear pestañas
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                # Crear pestaña Terminal
        self.terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.terminal_frame, text="🖥 Terminal")


        # Textbox para la Terminal
        self.textbox = scrolledtext.ScrolledText(self.terminal_frame, height=30, width=100, font=("Consolas", 10))
        self.textbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.textbox.configure(state='disabled') 
        # ⬇️ Botones dentro de la pestaña Terminal
        button_frame = ttk.Frame(self.terminal_frame)
        button_frame.pack(pady=5)

        self.btn_start = tk.Button(button_frame, text="▶ Iniciar sincronización")
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(button_frame, text="⛔ Detener")
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.root.protocol("WM_DELETE_WINDOW", lambda: ocultar_a_bandeja(self.root))



        # ─── Pestaña Marcador ───
        self.marcador_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.marcador_frame, text="📌 Gestionar Dispositivos")
        # Formulario para nuevo marcador
        form_frame = ttk.Frame(self.marcador_frame)
        form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        self.marcador_frame.grid_columnconfigure(0, weight=0)

        # Campo IP
        ttk.Label(form_frame, text="IP:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.txt_ip = ttk.Entry(form_frame, width=30)
        self.txt_ip.grid(row=0, column=1, columnspan=2, pady=5, sticky="w")

        # Campo Nombre
        ttk.Label(form_frame, text="Nombre:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.txt_name = ttk.Entry(form_frame, width=30)
        self.txt_name.grid(row=1, column=1, columnspan=2, pady=5, sticky="w")

        # Campo Estado
        ttk.Label(form_frame, text="Estado:").grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self.combo_estado = ttk.Combobox(form_frame, values=["ACTIVO", "INACTIVO"], width=27)
        self.combo_estado.grid(row=2, column=1, pady=5, sticky="w")
        self.combo_estado.set("ACTIVO")
        # Campo Puerto (nuevo campo)
        ttk.Label(form_frame, text="Puerto:").grid(row=3, column=0, padx=(0, 5), pady=5, sticky="w")
        self.txt_puerto = ttk.Entry(form_frame, width=30)
        self.txt_puerto.grid(row=3, column=1, columnspan=2, pady=5, sticky="w")

        ttk.Label(form_frame, text="Fecha inicio de sincronización:").grid(row=4, column=0, padx=(0, 5), pady=5, sticky="w")

        self.txt_fecha_inicio = DateEntry(form_frame, width=28, date_pattern='dd-mm-yyyy',state="readonly")
        self.txt_fecha_inicio.grid(row=4, column=1, columnspan=2, pady=5, sticky="w")

        # Campo token (TextArea)
        ttk.Label(form_frame, text="Token:").grid(row=5, column=0, padx=(0, 5), pady=5, sticky="nw")

        self.txt_token = tk.Text(form_frame, width=23, height=8)
        self.txt_token.grid(row=5, column=1, columnspan=2, pady=5, sticky="w")

        ttk.Label(form_frame, text="Registros Asistencias:").grid(row=6, column=0, padx=(0, 5), pady=5, sticky="nw")
        self.var_mostrar_conteo = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            form_frame,
            text="Mostrar conteo de registros",
            variable=self.var_mostrar_conteo
        ).grid(row=6, column=1, columnspan=3, pady=5, sticky="w")

        # Frame para botones (alineación horizontal)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky="e")  # ← cambiamos "w" por "e" (east/derecha)

        self.btn_eliminar = ttk.Button(btn_frame, text="🗑 Eliminar")
        self.btn_eliminar.pack(side=tk.RIGHT, padx=(5, 0))  # ← Eliminar va primero para que quede más a la derecha

        self.btn_guardar = ttk.Button(btn_frame, text="💾 Guardar")
        self.btn_guardar.pack(side=tk.RIGHT, padx=(5, 0))

        self.btn_nuevo = ttk.Button(btn_frame, text="🆕 Nuevo", command=self.nuevo)
        self.btn_nuevo.pack(side=tk.RIGHT, padx=(5, 0))


        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        table_frame = ttk.Frame(self.marcador_frame)
        table_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        # Scrollbars
        scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=("id","ip","name","f_reg","f_act","estado","puerto","token","fecha_inicio","mostrar_conteo"),
            show="headings",
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Configurar scrollbars
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        # Encabezados
        for col, text in zip(
            ("id", "ip", "name", "f_reg", "f_act", "estado","puerto","token","fecha_inicio","mostrar_conteo"),
            ("ID","IP","Nombre","Fecha Registro","Última Sincronización","Estado","Puerto","Token","Fecha_Inicio","Mostrar Conteo")
        ):
            self.tree.heading(col, text=text)
            if col == "f_reg":  
                self.tree.column(col, width=0, stretch=False)   # ✅ Oculta la columna
            else:
                self.tree.column(col, width=120)

        # Permitir expansión del frame
        self.marcador_frame.grid_rowconfigure(4, weight=1)
        self.marcador_frame.grid_columnconfigure(0, weight=1)



    # Obtener datos del formulario
    def obtener_datos(self):
        ipx = self.txt_ip.get().strip()
        namex = self.txt_name.get().strip()
        estadox = self.combo_estado.get()
        puertox = self.txt_puerto.get().strip()
        tokenx = self.txt_token.get("1.0", tk.END).strip()
        fecha_iniciox = self.txt_fecha_inicio.get().strip()
        fecha_inicios = datetime.strptime(fecha_iniciox, "%d-%m-%Y")
        # Convertir a formato ISO compatible (ejemplo: "2025-11-03T00:00:00")
        fecha_convertida = fecha_inicios.isoformat()
        mostrar_conteo = 1 if self.var_mostrar_conteo.get() else 0
        return {
            "ip": ipx,
            "name": namex,
            "estado": 1 if estadox == "ACTIVO" else 0,
            "puerto": puertox,
            "token": tokenx,
            "fecha_inicio": fecha_convertida,
            "mostrar_conteo": mostrar_conteo
        }


    def llenar_form(self):
        selected = self.tree.focus()
        if not selected:
            return

        values = self.tree.item(selected, "values")
        if not values:
            return
        self.nuevo()
        self.btn_nuevo.pack(side=tk.LEFT, before=self.btn_guardar, padx=(0, 5))
        self.selected_id = values[0]

        self.txt_ip.delete(0, tk.END)
        self.txt_ip.insert(0, values[1])

        self.txt_name.delete(0, tk.END)
        self.txt_name.insert(0, values[2])

        self.combo_estado.set(values[5])

        self.txt_puerto.delete(0, tk.END)
        self.txt_puerto.insert(0, values[6])

        self.txt_token.delete("1.0", tk.END)
        self.txt_token.insert("1.0", values[7])

        self.txt_fecha_inicio.delete(0, tk.END)
        self.txt_fecha_inicio.insert(0, values[8])

        self.var_mostrar_conteo.set(True if values[9] == "SI" else False)

        # ✅ Sincronizar ID con el controlador
        if hasattr(self.controller, "marcador_seleccionado"):
            self.controller.marcador_seleccionado = self.selected_id


    # Limpiar formulario
    def limpiar_campos(self):
        self.txt_ip.delete(0, tk.END)
        self.txt_name.delete(0, tk.END)
        self.txt_puerto.delete(0, tk.END)
        self.combo_estado.set("ACTIVO")
        self.txt_token.delete("1.0", tk.END)
        self.txt_fecha_inicio.set_date(datetime.now().date())


    def nuevo(self):
        self.limpiar_campos()
        self.txt_ip.config(state="normal")
        self.txt_name.config(state="normal")
        self.combo_estado.config(state="normal")
        self.txt_puerto.config(state="normal")
        self.txt_token.config(state="normal")
        self.txt_fecha_inicio.config(state="normal")

        # 🔥 Resetear ID seleccionado para modo "insertar"
        self.selected_id = None

        # 🔥 Notificar al controlador que se deseleccione también
        if hasattr(self.controller, "marcador_seleccionado"):
            self.controller.marcador_seleccionado = None

        # 🔥 Desactivar botón eliminar (ya que no hay nada seleccionado)
        self.btn_eliminar.config(state=tk.DISABLED)

    def on_tab_changed(self, event):
        tab = event.widget.tab(event.widget.select(), "text")
        self.limpiar_campos()
        if tab == "🖥 Terminal":
            # Deshabilitar los campos cuando se está en la pestaña Terminal
            self.txt_ip.config(state="disabled")
            self.txt_name.config(state="disabled")
            self.combo_estado.config(state="disabled")
            self.txt_puerto.config(state="disabled")
            self.txt_token.config(state="disabled")
            self.txt_fecha_inicio.config(state="disabled")
            self.btn_nuevo.pack(side=tk.LEFT, before=self.btn_guardar, padx=(0, 5))


def inicializar_ventana_tk(ventana):
    global ventana_tk
    ventana_tk = ventana

# Función interna para mostrar y traer al frente
def _mostrar_y_traer_al_frente(root):
    root.deiconify()      # Mostrar ventana
    root.lift()           # Traer al frente
    root.focus_force()    # Dar foco
    root.attributes('-topmost', True)  # Asegurar que quede arriba
    root.after(100, lambda: root.attributes('-topmost', False))  # Reset topmost

def mostrar_ventana():
    global ventana_tk
    if ventana_tk:
        # Ejecutar en hilo principal de Tkinter
        ventana_tk.after(0, lambda: _mostrar_y_traer_al_frente(ventana_tk))

def salir_aplicacion(icon, item):
    global ventana_tk
    if ventana_tk:
        ventana_tk.after(0, ventana_tk.destroy)
    try:
        icon.stop()
    except Exception:
        pass

def crear_icono():
    # Icono de pystray
    try:
        return Image.open("icono.ico")
    except:
        # Icono genérico si falla
        image = Image.new('RGB', (64, 64), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill='blue')
        return image

# Ocultar la ventana a la bandeja
def ocultar_a_bandeja(root):
    global ventana_tk, icono_bandeja
    ventana_tk = root  # actualizamos la global
    root.withdraw()

    if icono_bandeja:
        try:
            icono_bandeja.stop()
        except:
            pass

    icono_bandeja = pystray.Icon("ZKTECO", crear_icono(), "ZKTECO", menu=pystray.Menu(
        pystray.MenuItem("Mostrar", lambda icon, item: mostrar_ventana()),
        pystray.MenuItem("Salir", salir_aplicacion)
    ))
    threading.Thread(target=icono_bandeja.run, daemon=True).start()


def crear_lock():
    # Si el lock ya existe, comprobar si el proceso sigue activo
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Verificar si el proceso con ese PID sigue activo
            if psutil.pid_exists(pid):
                print("⚠️ El programa ya está en ejecución.")
                return False
            else:
                # El proceso no existe, borrar el lock viejo
                os.remove(LOCK_FILE)
                print("🧹 Lock viejo eliminado (el proceso anterior ya no existe).")
        except Exception:
            # Si hay un error leyendo el lock, eliminarlo por seguridad
            os.remove(LOCK_FILE)
            print("⚠️ Lock corrupto eliminado.")

    # Crear un nuevo lock
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True


def eliminar_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    















