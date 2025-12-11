# controller_marcador.py
import datetime
import tkinter as tk
from tkinter import messagebox

class MarcadorController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.marcador_seleccionado = None

        self.view.btn_guardar.config(command=self.guardar_o_actualizar)
        self.view.btn_eliminar.config(command=self.eliminar)
        self.view.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refrescar_lista()

    # -----------------------------------------------------
    # GUARDAR O ACTUALIZAR
    # -----------------------------------------------------
    def guardar_o_actualizar(self):
        datos = self.view.obtener_datos()

        # ── Validar campos obligatorios ──
        if not datos["ip"]:
            messagebox.showwarning("Campo vacío", "El campo IP no puede estar vacío.")
            return
        if not datos["name"]:
            messagebox.showwarning("Campo vacío", "El campo Nombre no puede estar vacío.")
            return
        if not datos["puerto"]:
            messagebox.showwarning("Campo vacío", "El campo Puerto no puede estar vacío.")
            return
        if not datos["token"]:
            messagebox.showwarning("Campo vacío", "El campo Token no puede estar vacío.")
            return

        # ── Guardar o actualizar ──
        if self.marcador_seleccionado is None:
            self.model.insertar(**datos)
            messagebox.showinfo("Éxito", "Marcador registrado.")
        else:
            self.model.actualizar(self.marcador_seleccionado, **datos)
            messagebox.showinfo("Éxito", "Marcador actualizado.")

        # Limpiar formulario
        self.view.limpiar_campos()
        self.marcador_seleccionado = None
        self.view.btn_eliminar.config(state=tk.DISABLED)
        self.refrescar_lista()

    # -----------------------------------------------------
    # SELECCIONAR MARCADOR
    # -----------------------------------------------------
    def on_select(self, event):
        sel = self.view.tree.selection()
        if not sel:
            return

        valores = self.view.tree.item(sel[0], "values")

        self.marcador_seleccionado = int(valores[0])  # ID

        # Convertir estado de texto a número para el formulario
        estado_valor = 1 if valores[5] == "ACTIVO" else 0

        # Rellenar formulario
        self.view.llenar_form()

        self.view.btn_eliminar.config(state=tk.NORMAL)
    # -----------------------------------------------------
    # ELIMINAR
    # -----------------------------------------------------
    def eliminar(self):
        if self.marcador_seleccionado is None:
            return

        self.model.eliminar(self.marcador_seleccionado)
        messagebox.showinfo("Eliminado", "Marcador eliminado correctamente.")
        self.view.limpiar_campos()
        self.marcador_seleccionado = None
        self.view.btn_eliminar.config(state=tk.DISABLED)
        self.refrescar_lista()

    # -----------------------------------------------------
    # REFRESCAR TREEVIEW
    # -----------------------------------------------------
    def refrescar_lista(self):
        # Limpiar Treeview
        for item in self.view.tree.get_children():
            self.view.tree.delete(item)

        # Obtener registros
        registros = self.model.listar()

        # ----- Formatos -----
        def formato_fecha(fecha_str):
            if not fecha_str or fecha_str == "None":
                return ""
            try:
                # ISO: YYYY-MM-DDTHH:MM:SS
                return datetime.datetime.fromisoformat(fecha_str).strftime("%d-%m-%Y")
            except:
                pass
            try:
                # Solo fecha: YYYY-MM-DD
                return datetime.datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%d-%m-%Y")
            except:
                return fecha_str

        def formato_fecha_hora(fecha_str):
            if not fecha_str or fecha_str == "None":
                return ""
            try:
                # ISO con hora
                return datetime.datetime.fromisoformat(fecha_str).strftime("%d-%m-%Y %H:%M:%S")
            except:
                pass
            try:
                # Si viniera solo fecha, poner 00:00:00
                dt = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
                return dt.strftime("%d-%m-%Y 00:00:00")
            except:
                return fecha_str

        # Insertar registros en la grilla
        for fila in registros:
            id_, ip, name, f_reg, f_act, estado, puerto, token, fecha_inicio, mostrar_conteo = fila


            self.view.tree.insert(
                "",
                tk.END,
                values=(
                    id_,
                    ip,
                    name,
                    formato_fecha(f_reg),           # ✅ solo fecha
                    formato_fecha_hora(f_act),      # ✅ fecha + hora
                    estado,                         # o "Activo/Inactivo"
                    puerto,
                    token,
                    formato_fecha(fecha_inicio),     # ✅ solo fecha
                    "SI" if mostrar_conteo == 1 else "NO"
                )
            )


