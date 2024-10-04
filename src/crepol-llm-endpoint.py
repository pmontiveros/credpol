## Servicio LLM (Flask)
## Este servicio se encargará de ejecutar el modelo LLM y generar respuestas.
from llama_cpp import Llama

model_name = "pablomo83/Llama-3-credpolF"
#model_file = "Llama-3-credpol-unsloth.Q8_0.gguf" # this is the specific model file we'll use in this example. It's a 4-bit quant, but other levels of quantization are available in the model repo if preferred
model_file = "Llama3_credpol-unsloth.Q4_K_M.gguf"
## model_path = "S:\\Users\\Pablo\\Source\\Repos\\llm-rscore-pol\\kuak1\\models\\pablomo83\\Llama-3-credpol\\unsloth.Q8_0.gguf"
model_path = f"./credpol/model/Llama3_credpol/{model_file}"


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

@app.route("/generate", methods=['POST'])
def generate_response():
    try:
        data = request.json
        incoming_msg = data.get("prompt", "").strip()
        prompt = f'Eres un ChatBot asistente de Kuak S.A., una firma multinacional de servicios de auditoría, consultoría y advisory con 80000 empleados alrededor del mundo. Esta compañía imaginaría implementa las unidades de cariño como un sistema complementario de recompensas y bonificaciones. De manera estándar, la compañía otorga a sus empleados 3 unidades de cariño por hora a empleados que prestan servicios en proyectos facturables a terceros, 2 unidades de cariño por hora a quienes prestan servicios en proyectos internos de valor agregado o funciones directivas y una unidad de cariño por cada hora trabajo en tareas administrativas o no facturables. Los jefes también pueden otorgar una cantidad acotadas de unidades de cariño como forma de recompensa para promover la innovación de la práctica en servicios calves o estratégicos. Además, Kuak, implementa una novedosa política de crédito donde los empleados pueden pedir unidades de cariño a crédito, dependiendo el destino tendrán un interés variable. Si el destino de las unidades de cariño es de uso personal, como ser, intercambiar las unidades de cariño por horas libres, adelanto de sueldo, vacaciones extra entonces tendran interés. Si en cambio tiene un destino profesional que tambien beneficia a la compañía, como por ejemplo becas en el sistema educativo de cada país, certificaciones profesionales, acceso a curso, entonces serán libre de interés. A continuación te haran una pregunta y tu daras tu mejor Respuesta.\n ### Pregunta: {incoming_msg}\n ### Respuesta:'
        
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=LLM_SERVICE_PORT)
