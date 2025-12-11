import sqlite3

DB_PATH = "zkteco.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS marcadores (
            id INTEGER PRIMARY KEY,
            ip TEXT,
            name TEXT,
            fecha_registro TEXT,
            fecha_actualizacion TEXT,
            estado INTEGER DEFAULT 1,
            puerto INTEGER,
            token TEXT,       
            fecha_inicio TEXT,
            mostrar_conteo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TEXT,
            status INTEGER,
            punch INTEGER,
            marcador_id INTEGER,
            enviado INTEGER DEFAULT 0,
            UNIQUE (user_id, timestamp)
        );
    """)
    conn.commit()
    conn.close()
