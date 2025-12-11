
# Utils/api_client.py

from datetime import datetime
import requests, certifi

API_URL = "https://allica.pe/api/recursos-humanos/asistencia/marcador-local/desatendido/sync-marcacion-biometrico-masivo-alt"

def enviar_asistencia_api(lote):

    if not lote:
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    token = lote[0][2] if lote else ""

    data = [
        {
            "codTrabajador": user_id,
            "fecHora": ts,
            "fecUsureg": now_str
        }
        for user_id, ts, _ in lote
    ]

    payload = {
        "codDispositivoEncrypted": token,
        "data": data
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            timeout=180,
            verify=False
        )

        if resp.status_code == 201:
            print(f"✔ Lote enviado correctamente: {len(data)} registros")
            return True  

        else:
            print(f"✖ Error al enviar lote: {resp.status_code} - {resp.text}")
            return False

    except Exception as e:
        print(f"⚠ Error de conexión al enviar lote: {e}")
        return False
