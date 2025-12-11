from Models.database import get_connection
from Utils.helpers import fecha_valida

class MarcadorModel:
    def __init__(self):
        self.conn = get_connection()

    def listar(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM marcadores ORDER BY id;")
        return cur.fetchall()

    def insertar(self, ip, name, estado, puerto, token, fecha_inicio, mostrar_conteo):
        cur = self.conn.cursor()
        estado_text = "ACTIVO" if estado == 1 else "INACTIVO"
        cur.execute("""
            INSERT INTO marcadores (ip, name, estado, puerto, token, fecha_inicio, mostrar_conteo)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (ip, name, estado_text, puerto, token, fecha_inicio, mostrar_conteo))
        self.conn.commit()


    def actualizar(self, id_, ip, name, estado, puerto, token, fecha_inicio, mostrar_conteo):
        cur = self.conn.cursor()
        estado_text = "ACTIVO" if estado == 1 else "INACTIVO"
        cur.execute("""
            UPDATE marcadores SET
                ip = ?,
                name = ?,
                estado = ?,
                puerto = ?,
                token = ?,
                fecha_inicio = ?,
                mostrar_conteo = ?
            WHERE id = ?;
        """, (ip, name, estado_text, puerto, token, fecha_inicio, mostrar_conteo, id_))
        self.conn.commit()


    def eliminar(self, id_):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM marcadores WHERE id = ?;", (id_,))
        self.conn.commit()

    def marcadores_activos(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, ip, name , puerto, mostrar_conteo
            FROM marcadores 
            WHERE estado = 'ACTIVO'
            ORDER BY id;
        """)
        return cur.fetchall() 
    
    def buscar1(self, id_):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT fecha_registro, fecha_actualizacion
            FROM marcadores
            WHERE id = ?;
        """, (id_,))
        return cur.fetchone()

    
    def buscar2(self, id_):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT ip, name, puerto, fecha_registro, fecha_actualizacion
            FROM marcadores
            WHERE id = ?;
        """, (id_,))
        return cur.fetchone()
   
    
    def obtener_fecha_inicio(self, id_):
        cur = self.conn.cursor()
        cur.execute("SELECT fecha_inicio FROM marcadores WHERE id = ?;", (id_,))
        return cur.fetchone()

    
    def nuevas_Actualizar(self, id_,fecha_registro,fecha_actualizacion):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE marcadores SET
                fecha_registro = ?,
                fecha_actualizacion = ?
            WHERE id = ?;           
        """, (fecha_registro, fecha_actualizacion, id_))
        self.conn.commit()

    def solo_Actualizar(self, id_,fecha_actualizacion):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE marcadores SET
                fecha_actualizacion = ?
            WHERE id = ?;           
        """, (fecha_actualizacion, id_))
        self.conn.commit()
        

    def obtener_primer_registro(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT fecha_inicio FROM marcadores WHERE id = ?;", (id,))
        (min_ts,) = cur.fetchone()
        return fecha_valida(min_ts)