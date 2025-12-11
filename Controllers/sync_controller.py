import sqlite3
import threading
import time
import tkinter as tk
from tkinter import messagebox
from datetime import date, datetime
from pathlib import Path
import urllib.request

from zk import ZK
#from pyzk import ZK


from Utils.api_client import enviar_asistencia_api
from Utils.helpers import fecha_valida, ping_host, redondear_timestamp


class SyncController:

    def __init__(self, root, view, model_marcador, asistencia_model, notebook, textbox):
        self.root = root
        self.view = view
        self.notebook = notebook
        self.textbox = textbox

        self.running = False
        self.thread = None
        self.ultimas_fechas_inicio = {}

        self.controller = None
        self.model_marcador = model_marcador
        self.asistencia_model = asistencia_model

        self.btn_start = self.view.btn_start
        self.btn_stop = self.view.btn_stop
        self.btn_start.config(command=self.start)
        self.btn_stop.config(command=self.stop)

    def set_controller(self, controller):
        self.controller = controller

    # ------------------------------------------------------------
    # Logging (seguro para hilos)
    # ------------------------------------------------------------
    def log(self, mensaje, end="\n"):
        def escribir():
            try:
                if self.textbox.winfo_exists():
                    self.textbox.configure(state='normal')
                    self.textbox.insert("end", mensaje + end)
                    self.textbox.see("end")
                    self.textbox.configure(state='disabled')
            except Exception as e:
                print(f"[ERROR al escribir en textbox] {e}")

            if hasattr(self, 'log_file') and self.log_file:
                try:
                    self.log_file.write(mensaje + end)
                    self.log_file.flush()
                except Exception as e:
                    print(f"[ERROR al escribir log en archivo] {e}")

        try:
            self.textbox.after(0, escribir)
        except Exception:
            print(mensaje)

    # ------------------------------------------------------------
    # Obtener IPs (mejor si lo delegas al model_marcador)
    # ------------------------------------------------------------
    def obtener_ips(self):
        try:
            conn = sqlite3.connect("zkteco.db")
            cur = conn.cursor()
            cur.execute("SELECT ip FROM marcadores WHERE estado = 'ACTIVO'")
            rows = cur.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            self.log(f"❌ Error al consultar IPs: {e}")
            return []

    # ------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------
    def start(self):
        # Evitar doble ejecución
        if self.thread and self.thread.is_alive():
            self.log("⚠️ Ya hay una sincronización en curso.")
            return

        ips = self.obtener_ips()
        if not ips:
            messagebox.showwarning("Advertencia", "Aún no hay marcadores registrados o están inactivos.")
            return

        self.running = True
        # Actualizaciones de GUI con after
        self.root.after(0, lambda: self.btn_start.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_stop.config(state=tk.NORMAL))
        # deshabilitar pestaña de gestión (asumo que la pestaña índices 1 es la de marcadores)
        try:
            self.root.after(0, lambda: self.notebook.tab(1, state="disabled"))
        except Exception:
            pass

        # Lanzar hilo de sincronización
        self.thread = threading.Thread(target=self.sync_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.log("\n⛔ Deteniendo...")
        # Deshabilitar botones mientras se detiene (se re-habilitarán al terminar)
        self.root.after(0, lambda: self.btn_start.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

    def sync_finished(self):
        try:
            if getattr(self, "controller", None) and hasattr(self.controller, "refrescar_lista"):
                # refrescar lista desde hilo principal
                self.root.after(0, self.controller.refrescar_lista)
            else:
                self.log("⚠️ sync_finished: controller no asignado.")
        except Exception as e:
            self.log(f"❌ Excepción en sync_finished: {e}")

    # ------------------------------------------------------------
    # Bucle principal de sincronización
    # ------------------------------------------------------------
    def sync_loop(self):
        dia_actual = date.today()
        ruta_log = Path(f"Marcaciones_{dia_actual.strftime('%d-%m-%Y')}.txt")
        self.log_file = ruta_log.open("a", encoding="utf-8")

        try:
            while self.running:
                hoy = date.today()
                if hoy != dia_actual:
                    try:
                        self.log_file.close()
                    except Exception:
                        pass
                    dia_actual = hoy
                    ruta_log = Path(f"Marcaciones_{dia_actual.strftime('%d-%m-%Y')}.txt")
                    self.log_file = ruta_log.open("a", encoding="utf-8")

                if not self.running:
                    self.log("🛑 Sincronización interrumpida.")
                    self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))
                    self.root.after(0, lambda: self.notebook.tab(1, state="normal"))
                    return
                

                SLEEP_SEG = 60
                self.log("\n📋 Inicio de sincronización de asistencia")
                self.log("_" * 100)
                
                marcadores_activos = self.model_marcador.marcadores_activos()
                dispositivos = {row[0]: {"ip": row[1], "name": row[2],"puerto":row[3],"mostrar_conteo":row[4]} for row in marcadores_activos}


                for id_marc, info in dispositivos.items():

                    ip, nombre,puerto,mostrar_conteo = info["ip"], info["name"],info["puerto"],info["mostrar_conteo"]
                    self.log(f"\n Verificando conexión al dispositivo: {ip} || {nombre}")
 

                    # --- obtener fecha_registro y fecha_actualizacion ---
                    row = self.model_marcador.buscar1(id_marc)
                    if row:
                        fecha_registro_str, fecha_actualizacion_str = row
                    else:
                        fecha_registro_str = fecha_actualizacion_str = None

                    ts_registro_limite = fecha_valida(fecha_registro_str) or datetime(1970, 1, 1)
                    ts_ejecucion_prev  = fecha_valida(fecha_actualizacion_str) or ts_registro_limite
                    es_primera_vez = fecha_actualizacion_str is None


                    # --- obtener datos completos del marcador ---
                    fila = self.model_marcador.buscar2(id_marc)

                    if fila:
                        ip, nombre, puerto, fecha_registro_str, fecha_actualizacion_str = fila
                        ts_registro_limite = fecha_valida(fecha_registro_str) or datetime(1970, 1, 1)
                        ts_ejecucion_prev  = fecha_valida(fecha_actualizacion_str) or ts_registro_limite
                        es_primera_vez = fecha_actualizacion_str is None
                    else:
                        # Si no hay fila, se omite el dispositivo
                        self.log(f"❌ ERROR: No existe configuración para el marcador ID {id_marc}")
                        continue


                    if not ping_host(ip):
                            self.log(f"❌ Error en la conexión")
                            self.log("_" * 100)
                            continue
                    else:
                            print("✅ Conexión exitosa")


                    try:
                        ts_rango_fin = datetime.now()
                        zk = ZK(ip, port=puerto, timeout=300, ommit_ping=True)
                        dev = zk.connect()
                        dev.disable_device()

                        registros = list(dev.get_attendance())
                        self.log("✅ Conexión exitosa")
                        if(mostrar_conteo==1):
                            total_registros = len(registros)
                            self.log(f"Total registros: {total_registros}")
                        

                        time.sleep(3)
                        self.log("-" * 30 + " Insertando registros en la base de datos local " + "-" * 22)

                        nuevas = 0
                        ts_nuevo_max = None
                        ts_rango_ini = ts_ejecucion_prev
                        #- fecha ultimo Update
                        

                        # ───── Obtener fecha de inicio desde DB o selector ─────
                        fila = self.model_marcador.obtener_fecha_inicio(id_marc)

                        if fila and fila[0]:
                            fecha_inicio_bd = datetime.fromisoformat(fila[0])
                            ts_rango_ini = fecha_inicio_bd
                        else:
                            fecha_inicio_bd = ts_ejecucion_prev
                            ts_rango_ini = ts_ejecucion_prev


                        #fecha_sinc = datetime.now()
                        if nuevas > 0:
                            self.model_marcador.nuevas_Actualizar(id_marc,ts_nuevo_max.isoformat(),ts_rango_fin.isoformat())

                        else:
                            self.model_marcador.solo_Actualizar(id_marc,ts_rango_fin.isoformat())


                        # ───── Detectar cambio manual de fecha_inicio ─────
                        self.ultimas_fechas_inicio = getattr(self, "ultimas_fechas_inicio", {})

                        # Leer la fecha_inicio actual desde la BD
                        #cur.execute("SELECT fecha_inicio FROM marcadores WHERE id = ?", (id_marc,))
                        fila = self.model_marcador.obtener_fecha_inicio(id_marc)
                        fecha_inicio_actual = None

                        if fila and fila[0]:
                            try:
                                fecha_inicio_actual = datetime.fromisoformat(fila[0])
                            except:
                                fecha_inicio_actual = None

                        fecha_inicio_prev = self.ultimas_fechas_inicio.get(id_marc)

                        if fecha_inicio_prev and fecha_inicio_actual and fecha_inicio_prev != fecha_inicio_actual:
                            es_primera_vez = True

                        self.ultimas_fechas_inicio[id_marc] = fecha_inicio_actual

                        # ───── Continuar con la sincronización ─────
                        primer_reg = self.model_marcador.obtener_primer_registro(id_marc)
                        if es_primera_vez:
                            ts_rango_ini = primer_reg or datetime(1970, 1, 1)
                            self.log(f"🔄 desde {ts_rango_ini.strftime('%d/%m/%Y')} ({ts_rango_ini.strftime('%H:%M:%S')}) "
                                    f"hasta {ts_rango_fin.strftime('%d/%m/%Y')} ({ts_rango_fin.strftime('%H:%M:%S')})")
                        else:
                            ts_rango_ini = ts_ejecucion_prev
                            self.log(f"🔄 desde {ts_rango_ini.strftime('%d/%m/%Y')} ({ts_rango_ini.strftime('%H:%M:%S')}) "
                                    f"hasta {ts_rango_fin.strftime('%d/%m/%Y')} ({ts_rango_fin.strftime('%H:%M:%S')})")

                        #------VALIDAR REGISTROS EXISTENTES Y FECHAS DENTRO DEL RANGO------#
                        # ───── Procesar asistencias ─────
                        #fecha_actual = datetime.now()

                        #self.log(
                        #                f"🔄 INICIO {fecha_inicio_bd} FINAL {ts_rango_fin}"
                        #            ) 
                        for rec in registros:
                            ts = redondear_timestamp(rec.timestamp) if rec.timestamp else None
                            if not ts:
                                continue
                            if fecha_inicio_bd <= ts <= ts_rango_fin:

                                existe=self.asistencia_model.existe_asistencia(rec.user_id, ts.isoformat())
                                if existe:
                                    continue
                                self.asistencia_model.insertar_asistencia(
                                        rec.user_id,
                                        ts.isoformat(),
                                        rec.status,
                                        rec.punch,
                                        id_marc
                                    )
                                nuevas += 1
                                if ts_nuevo_max is None:
                                    # Si es el primer registro, lo asignamos
                                    ts_nuevo_max = ts
                                elif ts > ts_nuevo_max:
                                    # Si el registro actual es más reciente, lo actualizamos
                                    ts_nuevo_max = ts
                                else:
                                    # Si no es más reciente, no cambiamos nada
                                    ts_nuevo_max = ts_nuevo_max
          
                        ts_rango_fin = ts_rango_fin
                        ts_rango_ini = primer_reg or ts_rango_ini

                        
                        self.log(f"📥 Total de Registros insertados {nuevas:,}")
                        time.sleep(3)
                        # ───── Enviar a la nube si hay registros nuevos ─────#
                        if nuevas > 0:
                            self.log(f"{'-'*30} Insertando registros BD Cloud {'-'*39}") 
                            # ───── Verificación de conexión a internet ─────
                            self.log("Verificando conexión a internet")
                            try:
                                urllib.request.urlopen("https://www.allica.pe", timeout=5)
                                self.log("✅ Conexión exitosa")
                            except Exception:
                                self.log("❌ Error en la conexión")
                                self.log(f"{'_' * 100}")
                                continue

                            pendientes = self.asistencia_model.enviar_asistencias_api(
                                ip,
                                ts_rango_ini.isoformat(),
                                ts_rango_fin.isoformat()
                            )
                            #self.log(
                            #            f"🔄 INICIO {ts_rango_ini} FINAL {ts_rango_fin}"
                            #        ) 

                            total_pendientes = len(pendientes)
                            BATCH_SIZE = 1000  # 🔹 Solo enviar 1000 registros por ejecución

                            if total_pendientes == 0:
                                time.sleep(2)
                                self.log("🔄 No hay registros pendientes por enviar.")
                            else:
                                enviados = 0

                                for i in range(0, total_pendientes, BATCH_SIZE):

                                    lote = pendientes[i:i + BATCH_SIZE]
                                    

                                    ok = enviar_asistencia_api(lote)

                                    # ✅ Solo marcar como enviadas si el API respondió OK
                                    if ok:
                                        enviados += len(lote)
                                        self.asistencia_model.marcar_enviadas(
                                            [(row[0], row[1]) for row in lote]
                                        )
                                        print("✅ Se marcaron registros como enviadas.")
                                    else:
                                        print("❌ Error, al insertar registros")

                                    # ✅ Log de progreso
                                    self.log(
                                        f"🔄 Total enviados {enviados:,} de {total_pendientes:,}"
                                    )

                                self.log(f"{'_' * 100}")

                                dev.enable_device()
                                dev.disconnect()

                        else:
                            self.log(f"{'_' * 100}")

                    except Exception as e:
                        self.log(f"❌ Error al sincronizar con {nombre} ({ip})")
                        self.log("⚠️  Interrupción inesperada: No se pudieron descargar los registros.")
                        self.log(f"📛 Motivo: {str(e)}")
                        #conn.rollback()
                        self.log("_" * 100)


                self.log_file.flush()
                self.root.after(0, lambda: self.sync_finished())


                for _ in range(SLEEP_SEG):
                    if not self.running:
                        break
                    time.sleep(1)

                if not self.running:
                    self.log("🛑 Sincronización interrumpida.")
                    self.log("_" * 100)
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    self.notebook.tab(1, state="normal")
                    

        finally:
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.close()
           # cur.close()
            #conn.close()
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
