import requests
import json
import time
import boto3
from botocore.exceptions import ClientError
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings


# Variables globales
TOKEN = "MzkwNmRkMzQtZWE5Ni00MDM5LTgzMzEtZjU4Y2Q4ZDQyMGQ5NGUxZWUyYzgtMmYy_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f"
S3_BUCKET = "hackathon-cx-2024"
PDF_FILE = "Guide_to_Managing_Classification_Outcomes.pdf"

# Mapeo para las respuestas
RISK_MAPPING = {
    "6 - Closed Won": "Low Renewal Risk",
    "6 - Closed Lost": "High Renewal Risk"
}

# S3 Client
s3 = boto3.client('s3')

# Descargar PDF desde S3
def download_pdf_from_s3(bucket, file_name):
    try:
        s3.download_file(bucket, file_name, f"/tmp/{file_name}")
        print("PDF descargado con éxito.")
        return f"/tmp/{file_name}"
    except ClientError as e:
        print(f"Error al descargar el archivo PDF desde S3: {e}")
        return None

# Construir el índice FAISS a partir del PDF
def build_pdf_index(file_path):
    print("Cargando y procesando el archivo PDF...")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    print("Documentos cargados del PDF.")
    
    embeddings = BedrockEmbeddings(model="llama2-7b")  # Usar Llama en Bedrock
    print("Generando embeddings con Bedrock...")
    vectorstore = FAISS.from_documents(documents, embeddings)
    print("Índice FAISS construido correctamente.")
    return vectorstore

# Consultar al LLM mediante RetrievalQA
def consult_llm(vectorstore, query):
    print(f"Realizando consulta al LLM con la pregunta: {query}")
    qa = RetrievalQA.from_chain_type(llm="llama2-7b", retriever=vectorstore.as_retriever())
    response = qa.run(query)
    print(f"Respuesta del LLM: {response}")
    return response

# Obtener mensajes desde Webex
def get_messages_from_room(room_id, max_messages=1):
    url = f"https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    params = {
        "roomId": room_id,
        "max": max_messages,
        "mentionedPeople": "me"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        messages = response.json().get("items", [])
        return messages
    else:
        print(f"Error al obtener mensajes de Webex: {response.status_code}")
        print(response.json())
        return []

# Consultar al modelo existente
def modelo(Global_ID):
    url = "https://xwlyrf0dva.execute-api.us-east-1.amazonaws.com/default/predict"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "GLOBAL_ULTIMATE_ID": Global_ID
    }
    print(f"Enviando solicitud al modelo con GLOBAL_ULTIMATE_ID: {Global_ID}")
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    print(f"Respuesta del modelo: {response.json()}")
    return response.json()

# Enviar mensaje a Webex
def postJoke(roomId, message):
    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": roomId,
        "text": message,
    }
    print(f"Enviando mensaje a Webex: {message}")
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)

# Generar sugerencias complementarias basadas en RAG
def generate_suggestions(prediction):
    try:
        print("Iniciando generación de sugerencias...")
        file_path = download_pdf_from_s3(S3_BUCKET, PDF_FILE)
        if not file_path:
            print("Error: No se pudo acceder al archivo PDF.")
            return "Error: Could not access the PDF for suggestions."
        
        print(f"Archivo descargado: {file_path}")
        print("Construyendo el índice FAISS...")
        vectorstore = build_pdf_index(file_path)
        print("Índice FAISS construido correctamente.")
        
        if prediction == "6 - Closed Won":
            query = "What strategies can ensure customer retention and renewal?"
        elif prediction == "6 - Closed Lost":
            query = "What strategies can help reverse customer churn and encourage renewal?"
        else:
            query = f"What suggestions can you provide for the outcome '{prediction}'?"
        
        print(f"Consulta al LLM con query: {query}")
        response = consult_llm(vectorstore, query)
        print(f"Respuesta del LLM: {response}")
        return response
    except Exception as e:
        print(f"Error en generate_suggestions: {e}")
        return "Error generating suggestions."



# Main Lambda Handler
def main(event, context):
    #try:
    print("inicio de main")
    print(f"Evento recibido: {event}")
    event_body = json.loads(event.get('body', '{}'))
    room_id = event_body["data"]["roomId"]
    message = event_body["data"]["message"]
    
    print(f"Room ID: {room_id}, Mensaje: {message}")
    
    if "Hola" in message or "Hello" in message:
        postJoke(room_id, "Hi, here is CX_Hackaton_BOT, Could you provide the deal ID?")
    else:
        # Procesar el Deal ID desde el mensaje
        deal_id = message.split(" ")[-1]
        
        # Consultar el modelo existente
        print("Consultando el modelo...")
        prediction_response = modelo(deal_id)
        prediction = prediction_response.get("prediction", "Unknown")
        
        # Mapear la predicción a riesgos
        risk_level = RISK_MAPPING.get(prediction, "Unknown Risk Level")
        print(f"Predicción obtenida: {prediction} (Riesgo: {risk_level})")
        
        # Consultar al LLM para obtener sugerencias
        print("Generando sugerencias con RAG...")
        try:
            suggestions = generate_suggestions(prediction)
            print(f"Sugerencias generadas: {suggestions}")
        except Exception as e:
            print(f"Error al generar sugerencias: {e}")
            suggestions = "Error generating suggestions."
        
        # Formar el mensaje completo
        response_message = (f"For Deal {deal_id}, the predicted outcome is: {risk_level}.\n"
                            f"Suggestions: {suggestions}")
        print(f"Mensaje generado: {response_message}")
        
        # Enviar el mensaje a la sala de Webex
        postJoke(room_id, response_message)

    return {"statusCode": 200, "body": "Message processed successfully."}
    #except Exception as e:
        #print(f"Error durante la ejecución de la Lambda: {e}")
        #return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

