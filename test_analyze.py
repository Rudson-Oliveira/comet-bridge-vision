#!/usr/bin/env python3
"""
Teste simples de análise de imagem com LLaVA
"""
import requests
import sys

# Usar imagem existente
image_path = "C:/Users/rudpa/comet_bridge_vision/captures/capture_20251224_113242.png"
prompt = "Descreva em portugues o que voce ve nesta imagem"

print(f"Analisando: {image_path}")
print(f"Prompt: {prompt}")
print("Aguarde, isso pode levar 30-60 segundos...")

try:
    response = requests.post(
        "http://localhost:5003/analyze",
        json={
            "image_path": image_path,
            "prompt": prompt,
            "allow_cloud": False
        },
        timeout=180
    )
    result = response.json()
    
    if result.get("success"):
        print("\n" + "="*50)
        print("ANALISE COMPLETA!")
        print("="*50)
        print(f"Provedor: {result.get('analysis', {}).get('provider', 'N/A')}")
        print(f"Modelo: {result.get('analysis', {}).get('model', 'N/A')}")
        print("\nResposta:")
        print(result.get("analysis", {}).get("response", "Sem resposta"))
    else:
        print(f"Erro: {result.get('error')}")
except Exception as e:
    print(f"Erro de conexao: {e}")
