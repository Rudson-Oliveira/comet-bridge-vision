# COMET Bridge Vision

Sistema de visão computacional para o ecossistema COMET, permitindo captura e análise de tela usando modelos de IA multimodais.

## 🎯 Visão Geral

O COMET Bridge Vision é um servidor que:
- **Captura screenshots** da tela do Windows
- **Analisa imagens** usando modelos de visão (LLaVA, Gemini, Claude, GPT-4o)
- **Integra com Obsidian** para criar notas automaticamente
- **Expõe API REST** para integração com N8n e outros sistemas

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    COMET Bridge Vision                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Screen    │  │   Vision    │  │     Obsidian        │ │
│  │   Capture   │──│     AI      │──│   Integration       │ │
│  │   (mss)     │  │  (LLaVA)    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │                │                    │             │
│         └────────────────┼────────────────────┘             │
│                          │                                  │
│                  ┌───────┴───────┐                         │
│                  │ Vision Server │                         │
│                  │  (Flask API)  │                         │
│                  │  Port: 5003   │                         │
│                  └───────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Componentes

| Arquivo | Descrição |
|---------|-----------|
| `vision_server.py` | Servidor Flask com API REST |
| `vision_ai.py` | Módulo de análise com múltiplos provedores |
| `screen_capture.py` | Captura de tela usando mss |
| `obsidian_integration.py` | Integração com Obsidian vault |
| `vision_config.json` | Configurações do sistema |

## 🚀 Instalação

### Pré-requisitos

- Python 3.10+
- Ollama com modelo LLaVA instalado
- Windows 10/11

### Passos

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/comet-bridge-vision.git
cd comet-bridge-vision
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Instale o LLaVA no Ollama:
```bash
ollama pull llava
```

4. Inicie o servidor:
```bash
python vision_server.py
```

Ou use o arquivo batch:
```bash
Iniciar_Vision.bat
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Captura e Análise
```http
POST /capture-and-analyze
Content-Type: application/json

{
    "prompt": "Descreva o que você vê nesta tela",
    "provider": "ollama"
}
```

### Histórico
```http
GET /history
```

### Status
```http
GET /status
```

## ⚙️ Configuração

Edite `vision_config.json`:

```json
{
    "providers": {
        "ollama": {
            "enabled": true,
            "base_url": "http://localhost:11434",
            "model": "llava",
            "timeout": 300
        }
    },
    "capture": {
        "output_dir": "captures",
        "format": "png"
    }
}
```

## 🔧 Otimizações Implementadas

### Timeout Aumentado
- Timeout padrão: **300 segundos** (antes era 120s)
- Permite processamento de imagens grandes

### Redimensionamento Automático
- Imagens maiores que 1920px são redimensionadas
- Reduz tempo de processamento do LLaVA
- Mantém qualidade com LANCZOS

### Exemplo de Melhoria de Performance
| Antes | Depois |
|-------|--------|
| ~4 min (timeout) | ~2-3 min |
| Imagem 8800x1350 | Redimensionada para ~1920x294 |

## 🔗 Integração com Ecossistema COMET

### COMET Bridge (Porta 5000)
- Automação Windows via PowerShell
- Execução de comandos remotos

### COMET Bridge Vision (Porta 5003)
- Análise de visão com LLaVA
- Captura de tela

### N8n
- Workflows de automação
- Integração via webhooks

## 📝 Exemplos de Uso

### Python
```python
import requests

response = requests.post(
    "http://localhost:5003/capture-and-analyze",
    json={
        "prompt": "O que você vê nesta tela?",
        "provider": "ollama"
    },
    timeout=300
)

print(response.json())
```

### PowerShell
```powershell
$body = @{
    prompt = "Descreva a tela"
    provider = "ollama"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5003/capture-and-analyze" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 300
```

### cURL
```bash
curl -X POST http://localhost:5003/capture-and-analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "O que você vê?", "provider": "ollama"}'
```

## 📄 Licença

MIT License

## 🤝 Contribuição

Parte do ecossistema COMET - Cognitive Operational Management & Execution Technology

---

**Desenvolvido com 🧠 por Manus AI**
