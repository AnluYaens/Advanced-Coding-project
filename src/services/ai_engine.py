import openai

openai.api_key = 'your_api_key'

def generar_recomendacion(transacciones):
    prompt = f"Analyze the following transactions and provide recommendations to optimize the budget: {transacciones}"
    respuesta = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return respuesta.choices[0].text.strip()
