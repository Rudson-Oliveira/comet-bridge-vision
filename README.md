# COMET Bridge Vision

Sistema de visão computacional para o ecossistema COMET, permitindo captura e análise de tela usando modelos de IA multimodais, **agora com Agente PicaPau para automação visual**.

## 🎯 Visão Geral

O COMET Bridge Vision é um servidor que:
- **Captura screenshots** da tela do Windows
- **Analisa imagens** usando modelos de visão (LLaVA, Gemini, Claude, GPT-4o)
- **Integra com Obsidian** para criar notas automaticamente
- **Expõe API REST** para integração com N8n e outros sistemas
- **🆕 Agente PicaPau** - Executor de comandos visuais com Playwright

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                      COMET Bridge Vision v1.1                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │   Screen    │  │   Vision    │  │        PicaPau Agent        │ │
│  │   Capture   │──│     AI      │──│  (Automação Visual)         │ │
│  │   (mss)     │  │  (LLaVA)    │  │  ┌─────┐ ┌─────┐ ┌───────┐ │ │
│  └─────────────┘  └─────────────┘  │  │ NLU │ │Play-│ │Visual │ │ │
│         │                │         │  │Parse│ │wright│ │Valid. │ │ │
│         │                │         │  └─────┘ └─────┘ └───────┘ │ │
│         │                │         └─────────────────────────────┘ │
│         └────────────────┼───────────────────────┘                 │
│                          │                                          │
│                  ┌───────┴───────┐                                 │
│                  │ Vision Server │                                 │
│                  │  (Flask API)  │                                 │
│                  │  Port: 5003   │                                 │
│                  └───────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## 📦 Componentes

### Core
| Arquivo | Descrição |
|---------|-----------|
| `vision_server.py` | Servidor Flask com API REST |
| `vision_ai.py` | Módulo de análise com múltiplos provedores |
| `screen_capture.py` | Captura de tela usando mss |
| `obsidian_integration.py` | Integração com Obsidian vault |
| `vision_config.json` | Configurações do sistema |

### 🐦 Agente PicaPau (NOVO!)
| Arquivo | Descrição |
|---------|-----------|
| `pica_pau/nlu_command_parser.py` | Parse de linguagem natural → JSON |
| `pica_pau/pica_pau_agent.py` | Executor Playwright (clica, digita, navega) |
| `pica_pau/visual_feedback_validator.py` | Validação de sucesso via COMET Vision |
| `pica_pau/credentials_manager.py` | Credenciais criptografadas (Fernet) |
| `pica_pau/pica_pau_api.py` | API REST integrada ao vision_server |

## 🚀 Instalação

### Pré-requisitos

- Python 3.10+
- Ollama com modelo LLaVA instalado
- Windows 10/11

### Passos

1. Clone o repositório:
```bash
git clone https://github.com/Rudson-Oliveira/comet-bridge-vision.git
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

4. **Instale o PicaPau (opcional):**
```bash
cd pica_pau
pip install -r requirements.txt
playwright install chromium
```

5. Inicie o servidor:
```bash
python vision_server.py
```

## 📡 API Endpoints

### Vision API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Status do servidor |
| POST | `/capture-and-analyze` | Captura e analisa tela |
| GET | `/history` | Histórico de análises |
| GET | `/providers` | Provedores disponíveis |

### 🐦 PicaPau API (NOVO!)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/pica-pau/health` | Status do agente |
| POST | `/pica-pau/execute` | Executa comando em linguagem natural |
| POST | `/pica-pau/parse` | Apenas faz parse do comando |
| POST | `/pica-pau/credentials` | Gerencia credenciais |
| GET | `/pica-pau/history` | Histórico de execuções |

## 🐦 Agente PicaPau - Guia de Uso

### O que é?
O PicaPau é um agente de automação visual que:
1. **Entende comandos em português** (linguagem natural)
2. **Executa ações no navegador** via Playwright
3. **Valida o resultado** usando visão computacional (LLaVA)

### Exemplo de Comando
```
"PicaPau entre no Hotmail com rud.pa@hotmail.com senha Rudson2323##, salvar senha"
```

### Fluxo de Execução
```
Comando → NLU Parser → JSON → Playwright → Ação → LLaVA → Validação
```

### Exemplo de Requisição
```bash
curl -X POST http://localhost:5003/pica-pau/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "PicaPau abra o Google e pesquise por clima São Paulo",
    "use_vision_feedback": true
  }'
```

### Resposta
```json
{
  "success": true,
  "command_parsed": {
    "action": "navigate_and_search",
    "target": "google.com",
    "search_term": "clima São Paulo"
  },
  "actions_log": [
    {"action": "navigate", "url": "https://google.com", "status": "success"},
    {"action": "type", "selector": "input[name=q]", "text": "clima São Paulo"},
    {"action": "click", "selector": "input[type=submit]"}
  ],
  "vision_validation": {
    "success": true,
    "description": "Página de resultados do Google mostrando clima de São Paulo"
  },
  "screenshot": "captures/pica_pau_20241224_140000.png"
}
```

### Ações Suportadas

| Ação | Exemplo de Comando |
|------|-------------------|
| **Login** | "PicaPau entre no Gmail com email@gmail.com senha 123456" |
| **Navegação** | "PicaPau abra o site youtube.com" |
| **Pesquisa** | "PicaPau pesquise no Google por receita de bolo" |
| **Clique** | "PicaPau clique no botão Entrar" |
| **Digitação** | "PicaPau digite 'Olá mundo' no campo de busca" |
| **Scroll** | "PicaPau role a página para baixo" |
| **Screenshot** | "PicaPau tire uma foto da tela" |

### Segurança

- **Credenciais criptografadas** com Fernet (AES-128)
- **Perfil de navegador persistente** em `browser_profiles/`
- **Logs de auditoria** LGPD compliant
- **Chave mestra** gerada automaticamente

## ⚙️ Configuração

### vision_config.json
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
    },
    "pica_pau": {
        "headless": false,
        "browser_profile": "browser_profiles/default",
        "timeout": 30
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

### Performance
| Antes | Depois |
|-------|--------|
| ~4 min (timeout) | ~2-3 min |
| Imagem 8800x1350 | Redimensionada para ~1920x294 |

## 🔗 Integração com Ecossistema COMET

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| COMET Bridge | 5000 | Automação Windows via PowerShell |
| Obsidian Agent | 5001 | Agente inteligente Obsidian |
| Hub Central | 5002 | Orquestrador de gatilhos |
| **COMET Vision** | **5003** | **Visão + PicaPau** |
| Frontend | 5173 | Interface web |

## 📝 Exemplos de Uso

### Python - Análise de Tela
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

### Python - PicaPau
```python
import requests

response = requests.post(
    "http://localhost:5003/pica-pau/execute",
    json={
        "command": "PicaPau abra o YouTube e pesquise por música relaxante",
        "use_vision_feedback": True
    },
    timeout=60
)
print(response.json())
```

### PowerShell
```powershell
$body = @{
    command = "PicaPau abra o Google"
    use_vision_feedback = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5003/pica-pau/execute" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

## 📄 Licença

MIT License

## 🤝 Contribuição

Parte do ecossistema COMET - Cognitive Operational Management & Execution Technology

---

**Desenvolvido com 🧠 por Manus AI**

**Versão:** 1.1.0 (com Agente PicaPau)
**Data:** 24/12/2024
