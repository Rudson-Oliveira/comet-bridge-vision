# Changelog - COMET Bridge Vision

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

## Próximas Versões

### Planejado para v1.1
- [ ] Integração completa com Obsidian (criar notas automáticas)
- [ ] Comandos de visão no chat do Obsidian
- [ ] Cache de análises recentes
- [ ] Seleção de monitor específico
- [ ] Suporte a região de captura

### Planejado para v2.0
- [ ] OCR integrado
- [ ] Detecção de elementos de UI
- [ ] Automação baseada em visão
- [ ] Integração com N8n
