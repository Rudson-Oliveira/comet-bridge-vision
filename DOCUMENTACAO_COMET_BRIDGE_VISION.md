# 🚀 COMET Bridge Vision v1.0 - Documentação Completa

---

## 1. Visão Geral

O **COMET Bridge Vision** é um sistema de visão computacional que permite ao seu ecossistema de IA "ver" e "entender" o que está acontecendo na sua tela. Ele captura a tela, analisa com IAs locais ou na nuvem, e se integra ao Obsidian e Hub Central.

### Arquitetura

```mermaid
graph TD
    subgraph Usuário
        A[Obsidian] --> B{/vision ...}
    end

    subgraph COMET Bridge Vision (localhost:5003)
        C[API REST] --> D[Captura de Tela]
        C --> E[Análise com IA]
    end

    subgraph IAs
        F[Ollama LLaVA] <--> E
        G[Claude/GPT-4/Gemini] <--> E
    end

    subgraph Sistema IA
        H[Hub Central] <--> C
        A <--> H
    end

    B --> C
    D --> E
```

## 2. Componentes

| Componente | Arquivo | Função |
|------------|---------|--------|
| **Captura de Tela** | `screen_capture.py` | Captura tela inteira, monitores ou regiões |
| **Análise com IA** | `vision_ai.py` | Integra com Ollama, Claude, GPT-4, Gemini |
| **Servidor API** | `vision_server.py` | Endpoints REST para controle |
| **Integração Obsidian** | `obsidian_integration.py` | Comandos `/vision` no chat |
| **Configuração** | `vision_config.json` | Configurações do sistema |

## 3. Instalação e Uso

### Pré-requisitos

1. **Python 3.10+**
2. **Ollama** instalado (https://ollama.ai)
3. **Modelo LLaVA** no Ollama:
   ```bash
   ollama pull llava
   ```

### Instalação

1. **Copie** a pasta `comet_bridge_vision` para `C:\Users\seu_usuario\`
2. **Instale** as dependências:
   ```bash
   pip install -r C:\Users\seu_usuario\comet_bridge_vision\requirements.txt
   ```
3. **Inicie** o servidor:
   ```bash
   python C:\Users\seu_usuario\comet_bridge_vision\vision_server.py
   ```

## 4. Comandos no Obsidian

Use os seguintes comandos no chat do Obsidian para interagir com o sistema:

| Comando | Descrição |
|---------|-----------|
| `/vision help` | Mostra esta ajuda |
| `/vision status` | Status do servidor Vision |
| `/vision providers` | Lista IAs disponíveis |
| `/vision capture` | Captura a tela inteira |
| `/vision ocr` | Extrai texto da tela |
| `/vision screen [pergunta]` | Captura e analisa com uma pergunta |
| `/vision analyze [prompt]` | Analisa a última captura com um prompt |
| `/vision doc [tipo]` | Analisa um documento na tela (invoice, form, etc) |

**Opção `--cloud`**: Adicione `--cloud` a qualquer comando para permitir o uso de APIs externas (Claude, GPT-4, Gemini) se o Ollama não for suficiente.

## 5. API REST (localhost:5003)

### Endpoints Principais

- `GET /health` - Status do servidor
- `GET /monitors` - Lista monitores
- `POST /capture` - Captura tela
- `POST /analyze` - Analisa imagem
- `POST /capture-and-analyze` - Captura e analisa
- `POST /ocr` - Extrai texto (OCR)
- `GET /providers` - Lista provedores de IA
- `GET /history` - Histórico de operações
- `POST /trigger` - Dispara gatilho no Hub Central

### Exemplo: Capturar e Analisar via API

```bash
curl -X POST http://localhost:5003/capture-and-analyze \
-H "Content-Type: application/json" \
-d '{
    "mode": "full",
    "prompt": "O que está acontecendo nesta tela?",
    "allow_cloud": false
}'
```

## 6. Configuração (`vision_config.json`)

| Chave | Descrição |
|-------|-----------|
| `ollama_host` | URL do seu servidor Ollama |
| `ollama_model` | Modelo de visão a ser usado (ex: `llava`) |
| `priority` | Ordem de preferência das IAs |
| `require_confirmation` | Perguntar antes de usar APIs cloud |
| `hub_central_url` | URL do seu Hub Central |
| `obsidian_api_url` | URL da API REST do Obsidian |
| `auto_save_to_obsidian` | Salvar análises automaticamente no Obsidian |
| `privacy` | Configurações de privacidade (blur, palavras-chave) |
| `api_keys` | Suas chaves de API para Claude, GPT-4, Gemini |

---
*Documentação gerada por Manus AI - 24/12/2024*
