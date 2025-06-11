# core/ai_engine.py
"""
AI Engine para Gemini 1.5 Pro API - Versión mejorada y robusta.

Requisitos:
    pip install --upgrade google-generativeai
    .env con GOOGLE_API_KEY
"""

import os
import re
import json
from typing import Dict, List, Tuple, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────
MODEL_NAME = "models/gemini-1.5-pro-latest"

# API Key
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "Falta la variable de entorno GOOGLE_API_KEY. "
        "Crea una en https://aistudio.google.com/app/apikey y agrégala a tu archivo .env"
    )

try:
    genai.configure(api_key=API_KEY)
    # Test de conexión
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Error configurando Gemini API: {e}")

# ── Function definitions for the AI ─────────────────────────────────────────
SYSTEM_PROMPT = """
Eres un asistente AI especializado en gestión de presupuestos y finanzas personales.

COMANDOS DISPONIBLES:
Cuando el usuario quiera registrar, eliminar o consultar gastos, responde EXACTAMENTE con uno de estos comandos:

1. Para registrar un gasto:
FUNCTION_CALL: insert_payment
ARGUMENTS: {"amount": <número>, "category": "<categoría>", "description": "<descripción>", "date": "<YYYY-MM-DD>"}

2. Para eliminar un gasto:
FUNCTION_CALL: delete_payment  
ARGUMENTS: {"expense_id": <número>}

3. Para consultar gastos por categoría:
FUNCTION_CALL: query_expenses_by_category
ARGUMENTS: {"category": "<categoría>"}

CATEGORÍAS VÁLIDAS: "Groceries", "Electronics", "Entertainment", "Other"

IMPORTANTE: 
- Si el usuario solo quiere conversar, responde normalmente
- Si necesitas ejecutar una función, usa EXACTAMENTE el formato mostrado arriba
- Para las fechas, usa el formato YYYY-MM-DD (ej: 2025-06-11)
- Si no especifica fecha, usa la fecha de hoy: 2025-06-11

EJEMPLOS:
Usuario: "Registra un gasto de 50 dólares en supermercado"
Respuesta: 
FUNCTION_CALL: insert_payment
ARGUMENTS: {"amount": 50, "category": "Groceries", "description": "supermercado", "date": "2025-06-11"}

Usuario: "¿Cuánto he gastado en entretenimiento?"
Respuesta:
FUNCTION_CALL: query_expenses_by_category  
ARGUMENTS: {"category": "Entertainment"}

Usuario: "Hola, ¿cómo estás?"
Respuesta: ¡Hola! Estoy bien, gracias. Soy tu asistente de presupuestos. ¿En qué puedo ayudarte hoy?
"""

def chat_completion(history: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Gestiona una conversación con Gemini 1.5 Pro a partir de un historial.

    Args:
        history (list): Lista de tuplas con el formato [("user", "..."), ("assistant", "...")]

    Returns:
        dict: {"type": "text", "content": ...} o {"type": "function_call", "name": ..., "arguments": ...}
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)

        # Preparamos historial en el formato que Gemini espera
        gemini_history = []
        
        # Agregar system prompt como primer mensaje
        gemini_history.append({
            "role": "user", 
            "parts": [SYSTEM_PROMPT]
        })
        gemini_history.append({
            "role": "model", 
            "parts": ["Entendido. Soy tu asistente de presupuestos y estoy listo para ayudarte."]
        })

        # Convertir historial
        for role, content in history:
            gemini_role = "model" if role == "assistant" else "user"
            gemini_history.append({
                "role": gemini_role, 
                "parts": [content]
            })

        if not gemini_history or gemini_history[-1]["role"] != "user":
            raise ValueError("El historial está vacío o el último mensaje no es del usuario.")

        # Sacamos el último mensaje del usuario
        last_message = gemini_history.pop()

        # Creamos el chat con el historial previo
        chat = model.start_chat(history=gemini_history)

        # Enviamos el nuevo mensaje del usuario
        response = chat.send_message(last_message["parts"][0])
        reply_text = response.text.strip()

        # Detectar si es un function call
        if "FUNCTION_CALL:" in reply_text and "ARGUMENTS:" in reply_text:
            return _parse_function_call(reply_text)
        else:
            # Respuesta normal
            return {
                "type": "text",
                "content": reply_text,
            }

    except Exception as e:
        return {
            "type": "text",
            "content": f"Error al comunicarse con la API: {str(e)}. Por favor, intenta de nuevo.",
        }

def _parse_function_call(text: str) -> Dict[str, Any]:
    """
    Parsea una respuesta de function call del formato especificado.
    
    Args:
        text: Texto con formato "FUNCTION_CALL: nombre\nARGUMENTS: {json}"
    
    Returns:
        Dict con type, name y arguments
    """
    try:
        # Extraer nombre de función
        function_match = re.search(r'FUNCTION_CALL:\s*(\w+)', text)
        if not function_match:
            raise ValueError("No se encontró nombre de función")
        
        function_name = function_match.group(1)
        
        # Extraer argumentos JSON
        args_match = re.search(r'ARGUMENTS:\s*(\{.*\})', text, re.DOTALL)
        if not args_match:
            raise ValueError("No se encontraron argumentos")
        
        args_json = args_match.group(1)
        arguments = json.loads(args_json)
        
        # Validar función
        valid_functions = ["insert_payment", "delete_payment", "query_expenses_by_category"]
        if function_name not in valid_functions:
            raise ValueError(f"Función no válida: {function_name}")
        
        return {
            "type": "function_call",
            "name": function_name,
            "arguments": arguments,
        }
        
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "type": "text",
            "content": f"Error procesando comando: {str(e)}. Por favor, reformula tu solicitud.",
        }

def test_api_connection() -> bool:
    """
    Prueba la conexión con la API de Gemini.
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content("Di 'test'")
        return "test" in response.text.lower()
    except Exception:
        return False

if __name__ == "__main__":
    # Test básico
    if test_api_connection():
        print("✅ Conexión con Gemini API exitosa")
        
        # Test de chat básico
        test_history = [("user", "Hola, ¿cómo estás?")]
        result = chat_completion(test_history)
        print(f"Respuesta de prueba: {result}")