# 🦜 Agente PicaPau

**Executor de comandos visuais com feedback inteligente**

Parte do COMET Bridge Vision - Extensão para automação de navegador com validação visual.

## 📋 Visão Geral

O Agente PicaPau permite executar comandos em linguagem natural para automatizar tarefas no navegador, com validação visual usando LLaVA.

### Fluxo de Execução

```
Comando Natural → NLU Parser → Playwright Executor → Visual Validator → Resultado
```

## 🚀 Instalação

```bash
# Executar o instalador
install.bat

# Ou manualmente:
pip install playwright cryptography
playwright install chromium
```

## 📖 Uso

### Exemplos de Comandos

```
PicaPau entre no Hotmail com rud.pa@hotmail.com senha Rudson2323##, salvar senha
PicaPau navegue para google.com
PicaPau clique no botão Enviar
PicaPau preencha o formulário com nome João e email joao@email.com
```

### API Endpoints

#### POST /pica-pau/execute-command
Executa um comando em linguagem natural.

```json
{
    "command": "PicaPau entre no Hotmail com email@example.com senha 123456",
    "use_vision_feedback": true,
    "save_credentials": true
}
```

**Resposta:**
```json
{
    "success": true,
    "command": "...",
    "parsed": {...},
    "execution": {
        "actions_executed": 5,
        "actions_failed": 0,
        "total_duration_ms": 15000
    },
    "validation": {
        "status": "success",
        "confidence": 0.85,
        "message": "Login realizado com sucesso"
    },
    "screenshot": "base64...",
    "actions_log": [...]
}
```

#### POST /pica-pau/parse-command
Apenas faz o parse sem executar (preview).

#### GET /pica-pau/credentials
Lista serviços com credenciais armazenadas.

#### POST /pica-pau/credentials
Armazena uma nova credencial.

#### DELETE /pica-pau/credentials/{service}
Remove uma credencial.

#### GET /pica-pau/audit-log
Exporta log de auditoria (LGPD compliant).

## 🔒 Segurança

- **Criptografia Fernet (AES-128-CBC)** para todas as credenciais
- **Derivação de chave PBKDF2** com 100.000 iterações
- **Logs de auditoria** sem dados sensíveis
- **Perfil de navegador persistente** para manter sessões
- **Senhas nunca são logadas** em texto plano

## 📁 Estrutura

```
pica_pau/
├── __init__.py              # Exports do pacote
├── nlu_command_parser.py    # Parser de linguagem natural
├── pica_pau_agent.py        # Executor Playwright
├── visual_feedback_validator.py  # Validador visual
├── credentials_manager.py   # Gerenciador de credenciais
├── pica_pau_api.py          # Endpoints Flask
├── requirements.txt         # Dependências
├── install.bat              # Instalador Windows
├── browser_profiles/        # Perfis de navegador
├── screenshots/             # Screenshots capturados
└── README.md                # Esta documentação
```

## 🎯 Ações Suportadas

| Ação | Verbos | Exemplo |
|------|--------|---------|
| LOGIN | entre, entrar, login, logar | "PicaPau entre no Gmail" |
| NAVIGATE | navegue, acesse, abra, vá | "PicaPau navegue para google.com" |
| CLICK | clique, pressione, aperte | "PicaPau clique no botão Enviar" |
| TYPE | digite, escreva, insira | "PicaPau digite Olá mundo" |
| FILL_FORM | preencha | "PicaPau preencha nome João" |
| SCROLL | role, desça, suba | "PicaPau desça a página" |
| WAIT | espere, aguarde | "PicaPau aguarde 5 segundos" |
| SCREENSHOT | capture, screenshot | "PicaPau capture a tela" |

## 🌐 Sites Conhecidos

O parser reconhece automaticamente:
- Hotmail/Outlook
- Gmail
- Google
- Facebook
- Instagram
- Twitter/X
- LinkedIn
- YouTube
- GitHub
- WhatsApp Web
- Telegram Web

## 📊 Validação Visual

O validador usa COMET Vision (LLaVA) para verificar:

- **Login**: Detecta inbox, erros, captchas
- **Navegação**: Verifica carregamento, erros 404
- **Formulários**: Valida campos preenchidos, erros
- **Cliques**: Detecta mudanças na página

## 🔧 Configuração

Edite `vision_config.json` para ajustar:

```json
{
    "pica_pau": {
        "headless": false,
        "slow_mo": 100,
        "timeout": 30000
    }
}
```

## 📝 Licença

MIT License - COMET Bridge Vision Project
