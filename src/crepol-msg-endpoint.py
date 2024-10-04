## Servicio de Mensajería (Flask)
## Este servicio recibirá los mensajes de WhatsApp, llamará al Servicio LLM y manejará las excepciones si el Servicio LLM está caído o demora demasiado.

#from pymemcache.client import Client as CCache
from flask import Flask,g, request,jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
# from elasticsearch import Elasticsearch
# from elasticsearch.exceptions import NotFoundError
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from textblob import TextBlob
import requests
import logging
import traceback
import uuid
import time
import re
import random
#import redis
import os
import sqlite3
from cfg.credentials import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4096
app.config['JSON_AS_ASCII'] = False

account_sid = TWILIO_ACCOUNT_SID
auth_token = TWILIO_AUTH_TOKEN
client = Client(account_sid, auth_token)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configurar logging
logging.basicConfig(level=logging.INFO)

MSG_TIME_OUT=120
MSG_SERVICE_PORT = 81
MSG_SERVICE_DEBUG = True
LLM_SERVICE_URL = "http://localhost:5001/generate"  # URL del servicio LLM
SQLLite_DB_NAME = 'credpol.db'

@app.route('/')
def index():
    return 'Endpoint de mensajeria'

# Manejador de errores global
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error("Error general: %s", e)
    print("Error")
    traceback.print_exc()
    return "Ha ocurrido un error en el servidor.", 500

@app.route("/ping", methods=['GET'])
def ping():
    return "El servicio de mensajeria está vivo!"


# Conexión a Memcached
#cache = CCache('localhost:11211')

# Conexión a Redis
#cache = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

#Coneeción a es
#es = Elasticsearch()

# Diccionario para almacenar el historial en Memcached
cache_history = 'crepol-msg-endpoint-history'

# Análisis de Sentimiento
# Implementadas con TextBlob que es simple de usar y buena para prototipos rápidos.
'''
def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # Escala de -1 (negativo) a 1 (positivo)
    return sentiment
'''


# Diccionario de palabras clave y tipos de solicitud
request_types = {
    'quiero': 'Solicitud Crédito',
    'necesito': 'Solicitud Crédito',
    'solicitar': 'Solicitud Crédito',
    'acreditación': 'Consulta políticas',
    'que es': 'Consulta políticas',
    'que Son': 'Consulta políticas',
    'usar': 'Consulta políticas',
    'impago': 'Reclamo',
    'impaga': 'Reclamo',
    'malo': 'Reclamo',
    'reclamar': 'Reclamo',
    'debito': 'Reclamo',
    'reclamo': 'Reclamo'
}

def analyze_request_type(text):
    # Convertir el texto a minúsculas para una comparación case-insensitive
    text = text.lower()
    
    # Recorrer las claves del diccionario para encontrar una coincidencia en el texto
    for keyword, request_type in request_types.items():
        if re.search(rf'\b{keyword}\b', text):
            return request_type
    
    # Si no se encuentra ninguna coincidencia, devolver None o un valor por defecto
    return 'Consulta políticas'



# analyze_sentiment Listas de palabras
palabras_positivas = ['bueno', 'buenos', 'genial', 'espectacular']
palabras_negativas = ['malo', 'feo', 'inutil']
antepuesto_amplificador = ['muy', 'super', 'mucho']

def analyze_sentiment(text):
    # Convertir el texto a minúsculas para una comparación case-insensitive
    text = text.lower()
    
    # Detectar si hay una palabra amplificadora antes de una palabra positiva o negativa
    for amplificador in antepuesto_amplificador:
        for palabra in palabras_positivas:
            if re.search(rf'\b{amplificador}\s+{palabra}\b', text):
                return random.uniform(0.7, 1.0)
        for palabra in palabras_negativas:
            if re.search(rf'\b{amplificador}\s+{palabra}\b', text):
                return random.uniform(-1.0, -0.7)
    
    # Detectar palabras positivas o negativas sin amplificadores
    for palabra in palabras_positivas:
        if re.search(rf'\b{palabra}\b', text):
            return random.uniform(0.3, 0.7)
    
    for palabra in palabras_negativas:
        if re.search(rf'\b{palabra}\b', text):
            return random.uniform(-0.7, -0.3)
    
    # Si no se detecta ninguna palabra relevante, devuelve 0
    return 0
    

# Dado un texto, retorna el primer UUID que coincida con el patrón o None//////////////////
def get_uuid(text):
    # Definir el patrón regex para un UUID uuid4
    uuid_pattern = r'\b[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}\b'
    
    # Buscar el primer UUID que coincida con el patrón
    match = re.search(uuid_pattern, text, re.IGNORECASE)
    
    # Si se encuentra una coincidencia, devolverla. Si no, devolver None
    return match.group(0) if match else None



# Funciónes para crear y manipular el repositorio de promts and responses
def setup_repo():
    if not os.path.exists(SQLLite_DB_NAME):
        conn = sqlite3.connect(SQLLite_DB_NAME)
        c = conn.cursor()

        # Crear la tabla prompt_responses si no existe
        c.execute('''CREATE TABLE IF NOT EXISTS prompt_responses
                     (prompt_uuid TEXT PRIMARY KEY, prompt TEXT, response TEXT, start_time TEXT, end_time TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS msg_chanel
             (idx INTEGER PRIMARY KEY AUTOINCREMENT, chanel TEXT, fechaRegistro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()

def set_response(prompt_uuid,prompt, response_text,start_time,end_time):
    try:
        conn = sqlite3.connect(SQLLite_DB_NAME)
        c = conn.cursor()
        logging.info("set_response (prompt_uuid,prompt, response,start_time,end_time): %s,%s,%s,%s,%s", prompt_uuid,prompt,response_text,start_time,end_time)
        sentiment_score = analyze_sentiment(prompt)
        request_type=analyze_request_type(prompt)
        c.execute("INSERT OR REPLACE INTO prompt_responses (prompt_uuid,prompt, response,sentiment_score,request_type,start_time,end_time) VALUES (?,?, ?, ?,?, ?, ?)", (prompt_uuid,prompt,response_text,sentiment_score,request_type ,start_time,end_time))  
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("Error al escribir persistir el prompt: %s", e)


def set_chanel(chanel):
    try:
        conn = sqlite3.connect(SQLLite_DB_NAME)
        c = conn.cursor()
        logging.info("set_chanel: %s",chanel)
        c.execute("INSERT INTO msg_chanel (chanel) VALUES (?)", (chanel,))  
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("Error set_chanel: %s", e)


def get_response(prompt_uuid):
    conn = sqlite3.connect(SQLLite_DB_NAME)
    c = conn.cursor()
    logging.info("get_response para %s", prompt_uuid)
    sql=f'SELECT response FROM prompt_responses WHERE prompt_uuid="{prompt_uuid}"'
    c.execute(sql)
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else None

def long_running_task(prompt_uuid, prompt):
    start_time = datetime.now()
    try:              
        logging.info("llm long_running_task call para /whatsapp prompt_uuid %s", prompt_uuid)
        response_text= f"Respuesta {prompt_uuid} en proceso"
        set_response(prompt_uuid,prompt, response_text,start_time,None)
    except Exception as e:
        traceback.print_exc()
        response_text=f"Error general al inicializar long_running_task{e}"
        logging.error(response_text)
        return response_text
    try:
        response = requests.post(LLM_SERVICE_URL, json={"prompt": prompt}, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        response_text = response_data.get('response', 'No se pudo generar una respuesta.')
        logging.info("llm long_running_task response_text para /whatsapp prompt_uuid %s: %s", prompt_uuid, response_text)
    except exceptions.RequestException as e:
        logging.error("Error al llamar al servicio LLM: %s", e)
        response_text = "Error al procesar la solicitud."
    
    end_time = datetime.now()
    set_response(prompt_uuid,prompt, response_text,start_time,end_time)
    return response_text

# Iniciar repo si no existe
setup_repo()

# Iniciar Executor para manejar mensajes asincronos ## Migrar a Kafka o similar?
executor = ThreadPoolExecutor(max_workers=4)

# Procesar Mensaje:
def process_incoming_msg(incoming_msg):
    if incoming_msg:
        if (prompt_uuid := get_uuid(incoming_msg)) is not None:
            logging.info("process_incoming_msg: Se detecto un posible prompt_uuid: %s", prompt_uuid)
            if (response_text := get_response(prompt_uuid)) is not None: return response_text
        else:
            prompt_uuid  = str(uuid.uuid4())      
            try:    
                future = executor.submit(long_running_task, prompt_uuid , incoming_msg)
                # Esperar MSG_TIME_OUT segundos para ver si la tarea se completa
                logging.info("llm wating future.result response_text para /whatsapp prompt_uuid  %s. Time out: %i seconds", prompt_uuid ,MSG_TIME_OUT)
                result = future.result(timeout=MSG_TIME_OUT)
                response_text = result
            except TimeoutError as e:
                logging.info("llm future.result MSG_TIME_OUT para /whatsapp prompt_uuid  %s.", prompt_uuid )
                response_text = f"El procesamiento está demorando. Tu ID de seguimiento es {prompt_uuid }. Pregunta sobre este ID en unos momentos."
            except Exception as e:
                logging.error("llm future.result: %s. Detectado para /whatsapp prompt_uuid  %s.",e, prompt_uuid )
                traceback.print_exc()  # Imprimir el traceback completo en la terminal
                response_text = f"Error al procesar {prompt_uuid }."
    else:
        response_text="No entendí tu mensaje. ¿Puedes repetirlo?"
    return response_text

# Enpoint de WhatsApp
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        resp = MessagingResponse()
        msg = resp.message()
        response_text=process_incoming_msg(incoming_msg)
        msg.body(response_text)
        sChanel="whatsapp"
        set_chanel(sChanel)
        return str(resp)
    except Exception as e:
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        logging.error("Error en /whatsapp: %s", e)
        return str(MessagingResponse().message("Ha ocurrido un error. Inténtalo nuevamente."))

# Enpoint Cliente Web
@app.route("/webmsg", methods=['POST'])
def webmsg_reply():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        resp = MessagingResponse()
        msg = resp.message()
        response_text=process_incoming_msg(incoming_msg)
        msg.body(response_text)
        sChanel="webmsg"
        set_chanel(sChanel)
        return str(resp)
    except Exception as e:
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        logging.error("Error en /whatsapp: %s", e)
        return str(MessagingResponse().message("Ha ocurrido un error. Inténtalo nuevamente."))


@app.route("/status", methods=['POST'])
def check_status():
    try:
        uuid_str = request.json.get('uuid', '').strip()

        if uuid_str in results:
            response_text = results.pop(uuid_str)
        else:
            response_text = f"Tu solicitud con ID {uuid_str} está en proceso. Intenta más tarde."
        
        return jsonify({"response": response_text})
    except Exception as e:
        logging.error("Error en /status: %s", e)
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        return jsonify({"response": "Ha ocurrido un error. Inténtalo nuevamente."}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=MSG_SERVICE_PORT) 
