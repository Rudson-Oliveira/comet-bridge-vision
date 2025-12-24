# Changelog - COMET Bridge Vision

## [1.1.0] - 2025-12-24

### 🐦 Adicionado - Agente PicaPau
Nova funcionalidade de automação visual com execução de comandos em linguagem natural.

#### Módulos Criados
- **nlu_command_parser.py** - Parser de linguagem natural para comandos estruturados
  - Suporte a comandos em português
  - Extração automática de URLs, credenciais e ações
  - Padrões para login, navegação, pesquisa, clique, digitação
  
- **pica_pau_agent.py** - Executor de automação com Playwright
  - Navegação automática em sites
  - Preenchimento de formulários
  - Cliques em elementos
  - Captura de screenshots
  - Perfil de navegador persistente
  
- **visual_feedback_validator.py** - Validação visual com LLaVA
  - Verificação de sucesso de ações
  - Detecção de erros na tela
  - Feedback em linguagem natural
  
- **credentials_manager.py** - Gerenciador de credenciais seguro
  - Criptografia Fernet (AES-128)
  - Chave mestra gerada automaticamente
  - Armazenamento seguro de senhas
  
- **pica_pau_api.py** - API REST para o PicaPau
  - `GET /pica-pau/health` - Status do agente
  - `POST /pica-pau/execute` - Executa comando
  - `POST /pica-pau/parse` - Parse de comando
  - `POST /pica-pau/credentials` - Gerencia credenciais
  - `GET /pica-pau/history` - Histórico

### Modificado
- **vision_server.py** - Integração com PicaPau
  - Import condicional do módulo PicaPau
  - Registro automático do Blueprint
  - Log de inicialização do PicaPau

### Dependências Adicionadas
- playwright>=1.40.0
- cryptography>=41.0.0

---

## [1.0.1] - 2025-12-24

### Otimizado
- **Timeout aumentado de 120s para 300s** - Permite processamento de imagens grandes sem timeout
- **Redimensionamento automático de imagens** - Método `_resize_image` adicionado
  - Imagens maiores que 1920px são automaticamente redimensionadas
  - Mantém proporção usando algoritmo LANCZOS
  - Reduz significativamente o tempo de processamento do LLaVA

### Performance
| Métrica | Antes | Depois |
|---------|-------|--------|
| Timeout | 120s | 300s |
| Imagem 8800x1350 | Timeout/Falha | ~2-3 min |
| Tamanho máximo | Sem limite | 1920px |

### Correções
- Corrigido problema de timeout em imagens de múltiplos monitores
- Melhorada estabilidade do servidor Flask

---

## [1.0.0] - 2025-12-24

### Adicionado
- Sistema de visão computacional inicial
- Integração com Ollama/LLaVA
- Suporte a múltiplos provedores:
  - Ollama (LLaVA) - Local
  - Google Gemini
  - Anthropic Claude
  - OpenAI GPT-4o
- Captura de tela usando mss
- API REST com endpoints:
  - `GET /health` - Status do servidor
  - `GET /history` - Histórico de análises
  - `POST /capture-and-analyze` - Captura e analisa tela
- Integração preparada para Obsidian
- Histórico de análises em JSON

### Arquitetura
- `vision_server.py` - Servidor Flask (porta 5003)
- `vision_ai.py` - Módulo de análise com múltiplos provedores
- `screen_capture.py` - Captura de tela
- `obsidian_integration.py` - Integração com Obsidian

---

## Roadmap

### Planejado para v1.2
- [ ] Integração com N8n via webhooks
- [ ] Comandos de voz para PicaPau
- [ ] Gravação de macros visuais
- [ ] Dashboard web para monitoramento

### Planejado para v2.0
- [ ] Treinamento de ações customizadas
- [ ] Integração com Obsidian Chat
- [ ] Suporte a múltiplos navegadores
- [ ] API de agendamento de tarefas
- [ ] OCR integrado
- [ ] Detecção de elementos de UI

---

**Mantido por:** Manus AI  
**Repositório:** https://github.com/Rudson-Oliveira/comet-bridge-vision
