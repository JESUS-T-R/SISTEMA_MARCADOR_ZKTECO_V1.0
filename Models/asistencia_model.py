from Models.database import get_connection
from Utils.helpers import fecha_valida

class AsistenciaModel:
    def __init__(self):
        self.conn = get_connection()

    def marcar_enviadas(self, data):
        conn = get_connection()
        cur = conn.cursor()
        cur.executemany(
                """
                UPDATE asistencias
                SET enviado = 1
                WHERE user_id = ? AND timestamp = ?;
                """,
                data
        )
        conn.commit() 


    def obtener_ultimo_registro(self,id_):
        cur = self.conn.cursor()
        cur.execute("SELECT MAX(timestamp) FROM asistencias WHERE marcador_id = ?;", (id_,))
        (max_ts,) = cur.fetchone()
        return fecha_valida(max_ts)
    
    def existe_asistencia(self, user_id, timestamp):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 1 
            FROM asistencias 
            WHERE user_id = ? AND timestamp = ?;
        """, (user_id, timestamp))
        return cur.fetchone() is not None

    def insertar_asistencia(self, user_id, timestamp, status, punch, marcador_id):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO asistencias (user_id, timestamp, status, punch, marcador_id, enviado)
            VALUES (?, ?, ?, ?, ?, 0);
        """, (user_id, timestamp, status, punch, marcador_id))
        self.conn.commit()
 
 
    def enviar_asistencias_api(self, ip, ts_inicio, ts_fin):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT a.user_id, a.timestamp, m.token
            FROM asistencias a
            INNER JOIN marcadores m ON a.marcador_id = m.id
            WHERE a.enviado = 0
              AND m.ip = ?
              AND a.timestamp BETWEEN ? AND ?;
        """, (ip, ts_inicio, ts_fin))
        return cur.fetchall()