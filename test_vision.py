#!/usr/bin/env python3
"""
Teste do COMET Bridge Vision
"""
import requests
import json

url = "http://localhost:5003/capture-and-analyze"
data = {
    "mode": "full",
    "prompt": "Descreva em portugues o que voce ve nesta tela. Identifique programas e janelas.",
    "allow_cloud": False
}

print("Capturando e analisando tela...")
response = requests.post(url, json=data, timeout=120)
result = response.json()

if result.get("success"):
    print("\n=== ANALISE DA TELA ===")
    print(result.get("analysis", {}).get("response", "Sem resposta"))
else:
    print("Erro:", result.get("error"))
