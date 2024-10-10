from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import logging
import requests
import os

app = Flask(__name__)

CLIENT_SERVICE_PORT = 5002

# URLs de los servicios
MESSAGING_SERVICE_URL = "http://localhost:8081/webmsg"
LLM_SERVICE_URL = "http://localhost:5001/ping"
MESSAGING_SERVICE_PING_URL = "http://localhost:8081/ping"
STATUS_CHECK_URL = "http://localhost:8081/status"
INDEX_PATH = "index.html"
SQLLite_DB_NAME = 'credpol.db'

wd = os.getcwd()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

print('Directorio: ',wd)
# Configurar logging
logging.basicConfig(level=logging.INFO)
#logging.info('Working Directory: %s', wd)

# Funciónes para crear y manipular el repositorio de series temporales
def setup_repo():
    try:
        conn = sqlite3.connect(SQLLite_DB_NAME)
        c = conn.cursor()
        # Crear la tabla prompt_responses si no existe
        logging.info("Seteabdo tabla indicadores en %s", SQLLite_DB_NAME)
        c.execute('''CREATE TABLE IF NOT EXISTS indicadores(idx INTEGER PRIMARY KEY AUTOINCREMENT, uuidref TEXT, Indicador TEXT,tValor TEXT, iValor INTEGER, dValor DECIMAL, fechaValor TIMESTAMP, fechaRegistro TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')       
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("Error al crear tabla indicadores: %s", e)

def ins_indicador(indicador,t_valor=None, i_valor=None, d_valor=None, fecha_valor=None):
    # Conectar a la base de datos
    conn = sqlite3.connect(SQLLite_DB_NAME)
    cursor = conn.cursor()
    
    # Convertir fecha_valor a timestamp si se proporciona
    if fecha_valor:
        fecha_valor = datetime.strptime(fecha_valor, '%Y-%m-%d %H:%M:%S')
    
    # Insertar los datos en la tabla
    cursor.execute('''
        INSERT INTO indicadores (Indicador, tValor, iValor, dValor, fechaValor)
        VALUES (?, ?, ?, ?, ?)
    ''', (indicador,t_valor, i_valor, d_valor, fecha_valor))
    
    # Confirmar la transacción
    conn.commit()
    
    # Cerrar la conexión
    conn.close()


setup_repo()

ins_indicador('Simple Client Start','Ok',1)

@app.route("/")
def index():
    return render_template(INDEX_PATH)

@app.route("/send_message", methods=['POST'])
def send_message():
    message = request.json.get("message")
    response = requests.post(MESSAGING_SERVICE_URL, data={"Body": message, "From": "web-client"})
    return jsonify({"response": response.text})

@app.route("/check_status", methods=['POST'])
def check_status():
    uuid = request.json.get("uuid")
    response = requests.post(STATUS_CHECK_URL, data={"Body": uuid})
    return jsonify({"response": response.text})

@app.route("/service_status", methods=['GET'])
def service_status():
    try:
        messaging_service_status = requests.get(MESSAGING_SERVICE_PING_URL).text
        ins_indicador('Messaging service status','Ok',1)
    except requests.exceptions.RequestException:
        messaging_service_status = "Error"
        ins_indicador('Messaging service status','Error',-1)

    try:
        llm_service_status = requests.get(LLM_SERVICE_URL).text
        ins_indicador('Llm service status','Ok',1)
    except requests.exceptions.RequestException:
        llm_service_status = "Error"
        ins_indicador('Llm service status','Error',-1)

    return jsonify({
        "messaging_service_status": messaging_service_status,
        "llm_service_status": llm_service_status
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=CLIENT_SERVICE_PORT, debug=True)
