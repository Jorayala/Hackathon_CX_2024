#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Chatbot101 with AWS Lambda Console Script.

Copyright (c) 2020 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

# This script will perform the following actions:
#   1. GET a joke from the icanhazdadjoke database of jokes.
#   2. POST the joke to the relevant Webex Teams Room

import requests
import json
import time

TOKEN = "MzkwNmRkMzQtZWE5Ni00MDM5LTgzMzEtZjU4Y2Q4ZDQyMGQ5NGUxZWUyYzgtMmYy_PF84_1eb65fdf-9643-417f-9974-ad72cae0e10f"

# Mapeo para las respuestas
RISK_MAPPING = {
    "6 - Closed Won": "Low Renewal Risk",
    "6 - Closed Lost": "High Renewal Risk"
}

#Step 1: GET joke from icanhazdadjoke database
def getJoke():

    url = "https://icanhazdadjoke.com"
    headers = {
        "Accept":"application/json"
    }
    
    response = requests.request("GET", url=url, headers=headers)
    print("consultandobroma")
    return response.json()["joke"]
    


#Step 2: POST that joke to Webex Teams Room
def postJoke(roomId,message):

    url = "https://webexapis.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",  # Bot's access token
        "Content-Type": "application/json"
    }
    payload = {
        "roomId": roomId,
        "text": message,
        

    }
    print("post")

    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)


#def main(event, context):
#    print(event["body"])
#    joke = getJoke()
#    postJoke(joke)
#    print(event)
#    return {
#        'statusCode': 200,
#        'body': json.dumps('Success, joke has been sent!')
#   }

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
        print(f"Failed to retrieve messages: {response.status_code}")
        print(response.json())
        return []

def modelo(Global_ID):
    url= "https://xwlyrf0dva.execute-api.us-east-1.amazonaws.com/default/predict"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "GLOBAL_ULTIMATE_ID": Global_ID
    }
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    print(response.json())
    return response.json()


def main(event, context):
    print(event["data"]["roomId"])
    sala = event["data"]["roomId"]
    print(sala)
    time.sleep(2)
    
    # Obtener los mensajes del room
    datos = get_messages_from_room(sala)
    print(type(datos))
    print(datos)
    
    texto = datos[0]["text"]
    
    if "Hola" in texto or "Hello" in texto:
        postJoke(sala, "Hi, here is CX_Hackaton_BOT, Could you provide the deal ID?")
    else:
        # Procesar el Deal ID desde el texto del mensaje
        texto = texto.split(" ")
        texto = texto[1]
        print("Ejemplo " + str(texto))
        
        # Consultar al modelo
        ejemplo = modelo(str(texto))
        prediction = ejemplo["prediction"]
        
        # Aplicar mapeo para las respuestas relevantes
        mapped_prediction = RISK_MAPPING.get(prediction, prediction)
        
        # Formar el mensaje con la predicción mapeada
        resultado = f"For the Deal: {texto}, the predicted result is: {mapped_prediction}"
        
        # Enviar el mensaje a Webex
        postJoke(sala, resultado)
    
    datos = ""
    texto = ""