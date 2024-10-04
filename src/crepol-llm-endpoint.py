## Servicio LLM (Flask)
## Este servicio se encargará de ejecutar el modelo LLM y generar respuestas.
from llama_cpp import Llama

model_name = "pablomo83/Llama-3-credpolF"
model_file = "Llama-3-credpol-unsloth.Q8_0.gguf" # this is the specific model file we'll use in this example. It's a 4-bit quant, but other levels of quantization are available in the model repo if preferred
## model_path = "S:\\Users\\Pablo\\Source\\Repos\\llm-rscore-pol\\kuak1\\models\\pablomo83\\Llama-3-credpol\\unsloth.Q8_0.gguf"
model_path = "S:\\Users\\Pablo\\Source\\Repos\\llm-rscore-pol\\kuak1\\models\\pablomo83\\Llama-3-credpol\\Llama-3-credpol-unsloth.Q4_K_M.gguf"


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
