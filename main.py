import sys
import tkinter as tk
from Models.asistencia_model import AsistenciaModel
from Models.database import init_db
from Models.marcador_model import MarcadorModel

from Controllers.marcador_controller import MarcadorController
from Controllers.sync_controller import SyncController 
from Utils.helpers import extraer, extraer_icono, mostrar_splash
from Views.app_view import MarcadorView, crear_lock, eliminar_lock

# ────────── Ejecutar Apps ──────────
if __name__ == "__main__":
    if not crear_lock():
        print("⚠ Ya hay una instancia ejecutándose.")
        sys.exit(0)

    try:
        init_db()
        extraer()
        extraer_icono()
        mostrar_splash("logo.png", 3000)

        root = tk.Tk()
        root.title("Gestión de Marcadores ZKTeco")

        model = MarcadorModel()
        asistencia_model = AsistenciaModel()
        view = MarcadorView(root)
        controller = MarcadorController(model, view)
        view.controller = controller
        sync_controller = SyncController(
            root,
            view,
            model,
            asistencia_model,
            view.notebook,
            view.textbox,
        )

        sync_controller.set_controller(controller)
        view.sync_controller = sync_controller

        root.mainloop()

    finally:
        eliminar_lock()
