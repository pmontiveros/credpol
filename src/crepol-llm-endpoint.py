## Servicio LLM (Flask)
## Este servicio se encargará de ejecutar el modelo LLM y generar respuestas.
from llama_cpp import Llama

model_name = "pablomo83/Llama-3-credpolF"
#model_file = "Llama-3-credpol-unsloth.Q8_0.gguf" # this is the specific model file we'll use in this example. It's a 4-bit quant, but other levels of quantization are available in the model repo if preferred
model_file = "Llama3_credpol-unsloth.Q4_K_M.gguf"
## model_path = "S:\\Users\\Pablo\\Source\\Repos\\llm-rscore-pol\\kuak1\\models\\pablomo83\\Llama-3-credpol\\unsloth.Q8_0.gguf"
model_path = f"./model/Llama3_credpol/{model_file}"

prompt_path = './src/cfg/prompt.txt'


stop_token = "\n"
LLM_SERVICE_PORT=5001

## Instantiate model from downloaded file
llm = Llama(
    model_path=model_path,
    n_ctx=4096,  # Context length to use
    n_batch= 512,
    n_threads=4,            # Number of CPU threads to use
    n_gpu_layers=32,        # Number of model layers to offload to GPU
    input_prefix="[INST]",
    input_suffix= "[/INST]\\n",
    antiprompt= [
      "[INST]"
    ],
    pre_prompt= "Tu eres un asistente de politicas de creditos en Kuak S.A.",
    pre_prompt_suffix= "<</SYS>>[/INST]\\n",
    pre_prompt_prefix= "[INST]<<SYS>>\\n"
)

## Generation kwargs
generation_kwargs = {
    "max_tokens":1024,
    "stop":["\n"], 
    "echo":True, # Echo the prompt in the output
    "top_k":1 # This is essentially greedy decoding, since the model will always return the highest-probability token. Set this value > 1 for sampling decoding
}

from flask import Flask, request, jsonify
import requests
import logging
import traceback

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4096
app.config['JSON_AS_ASCII'] = False

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Configurar logging
logging.basicConfig(level=logging.WARNING)

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
    return "El servicio de LLM está vivo!"

@app.route("/identify", methods=['POST'])
def identify_response():
    try:
        data = request.json
        incoming_msg = data.get("prompt", "").strip()

        prompt = f'Eres un clasificador encargado de dada una cadena de caracteres asimilar la cadena "", debes responder la siguiente pregunta con el identificador de la cuenta \n ### Pregunta: {incoming_msg}\n ### Respuesta:'
        
        if prompt:
            response = llm(prompt, **generation_kwargs)  ## llama_cpp.generate(model, prompt=incoming_msg) ## llm(prompt, **generation_kwargs)
            # Extraer el texto generado del JSON
            generated_text = response['choices'][0]['text']
            response_clean = generated_text.replace(prompt, '').strip()
            return jsonify({"response": response_clean})
        else:
            return jsonify({"response": "No se recibió un prompt válido."}), 400
    except Exception as e:
        logging.error("Error en /identify: %s", e)
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        return jsonify({"response": "Ha ocurrido un error al generar la respuesta."}), 500

@app.route("/generate", methods=['POST'])
def generate_response():
    try:
        data = request.json
        incoming_msg = data.get("prompt", "").strip()

        root_prompt = ''
        with open(prompt_path, 'r') as f:
            root_prompt = f.readlines()
        prompt = f'{root_prompt}\n ### Pregunta: {incoming_msg}\n ### Respuesta:'
        
        if prompt:
            response = llm(prompt, **generation_kwargs)  ## llama_cpp.generate(model, prompt=incoming_msg) ## llm(prompt, **generation_kwargs)
            # Extraer el texto generado del JSON
            generated_text = response['choices'][0]['text']
            response_clean = generated_text.replace(prompt, '').strip()
            return jsonify({"response": response_clean})
        else:
            return jsonify({"response": "No se recibió un prompt válido."}), 400
    except Exception as e:
        logging.error("Error en /generate: %s", e)
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        return jsonify({"response": "Ha ocurrido un error al generar la respuesta."}), 500

@app.route("/classifier", methods=['POST'])
def generate_classification():
    try:
        data = request.json
        incoming_msg = data.get("prompt", "").strip()
        prompt = f'Eres Clasificador de preguntas. Debes identificar si la pregunta corresponde con una Solicitud de Crédito, o una Consulta General de las politicas de Credito o es un reclamo. Tu resupuesta será: "Solicitud Crédito" si la persona pide unidades de cariño o esta interesada en conseguir créditos; "Reclamo" Si la persona tuvo un problema con las unidades de cariño acreditadas, con el pago de se credito o con el saldo de sus pagos; Cualquier otra cosa se considera una Consulta General de las politicas de Credito y debes reposponder "Consulta políticas".\n ### Pregunta: {incoming_msg}\n ### Respuesta:'
        
        if prompt:
            response = llm(prompt, **generation_kwargs)  ## llama_cpp.generate(model, prompt=incoming_msg) ## llm(prompt, **generation_kwargs)
            # Extraer el texto generado del JSON
            generated_text = response['choices'][0]['text']
            response_clean = generated_text.replace(prompt, '').strip()
            return jsonify({"response": response_clean})
        else:
            return jsonify({"response": "No se recibió un prompt válido."}), 400
    except Exception as e:
        logging.error("Error en /classifier: %s", e)
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        return jsonify({"response": "Ha ocurrido un error al generar la respuesta."}), 500


@app.route("/sentiment", methods=['POST'])
def sentiment():
    try:
        data = request.json
        incoming_msg = data.get("prompt", "").strip()
        prompt = f'Eres un analizador de sentimiento de preguntas. Debes identificar enojo o felicidad y responder con un valor entre -1 y 1. No puedes reponder con palabras solo con esos valores. Tu respuesta será: un valor entre "0.1" y "0.33" si en la pregunta hay términos positivos como "bueno", "genial", "excelente", "me gusta"; un valor entre "0.33" y "0.99" si utiliza términos muy positivos como "muy bueno", "super genial", "¡¡excelente!!", "me gusta Mucho" o equivalente;un valor entre "-0.33" y "-0.1" si utiliza términos negativos como "no me gusta", "malo", "Problema";un valor entre "-0.99" y "-0.34" si utiliza términos muy negativos como "enojado", "muy malo", "gran problema" o equivalente; Finalmente si no corresponde con las anteriores, entonces es un comentario neutro y debe tener valor entre "-0.1" y "0.1" a criterio.\n ### Pregunta: {incoming_msg}\n ### Respuesta:'
        
        if prompt:
            response = llm(prompt, **generation_kwargs)  ## llama_cpp.generate(model, prompt=incoming_msg) ## llm(prompt, **generation_kwargs)
            # Extraer el texto generado del JSON
            generated_text = response['choices'][0]['text']
            response_clean = generated_text.replace(prompt, '').strip()
            return jsonify({"response": response_clean})
        else:
            return jsonify({"response": "No se recibió un prompt válido."}), 400
    except Exception as e:
        logging.error("Error en /sentiment: %s", e)
        print("Error")
        traceback.print_exc()  # Imprimir el traceback completo en la terminal
        return jsonify({"response": "Ha ocurrido un error al generar la respuesta."}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=LLM_SERVICE_PORT)
