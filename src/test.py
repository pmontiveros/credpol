from llama_stack_client import LlamaStackClient

# Initialize the client
client = LlamaStackClient(base_url="http://172.206.51.85:5000")

# Create a chat completion request
response = client.inference.chat_completion(
    messages=[
        {"role": "system", "content": "You are a friendly assistant."},
        {"role": "user", "content": "Write a two-sentence poem about llama."}
    ],
    model='Llama3.2-3B-Instruct',
)
# Print the response
print(response.completion_message.content)