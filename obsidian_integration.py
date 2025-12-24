"""
COMET Bridge Vision - Integração com Obsidian
==============================================
Comandos de chat e criação automática de notas no Obsidian.

Autor: Manus AI
Data: 24/12/2024
Versão: 1.0

Comandos suportados:
- /vision capture - Captura tela
- /vision analyze - Analisa última captura
- /vision ocr - Extrai texto da tela
- /vision screen [pergunta] - Captura e analisa com pergunta
- /vision doc [tipo] - Analisa documento na tela
- /vision help - Mostra ajuda
"""

import os
import re
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ObsidianIntegration")


class ObsidianVisionCommands:
    """
    Processador de comandos de visão para o Obsidian.
    
    Integra com o COMET Bridge Vision Server para executar
    comandos de captura e análise de tela.
    """
    
    # Padrões de comandos
    COMMAND_PATTERNS = {
        "capture": r"^/vision\s+capture(?:\s+(.+))?$",
        "analyze": r"^/vision\s+analyze(?:\s+(.+))?$",
        "ocr": r"^/vision\s+ocr(?:\s+(.+))?$",
        "screen": r"^/vision\s+screen(?:\s+(.+))?$",
        "doc": r"^/vision\s+doc(?:\s+(\w+))?(?:\s+(.+))?$",
        "help": r"^/vision\s+help$",
        "status": r"^/vision\s+status$",
        "providers": r"^/vision\s+providers$",
        "config": r"^/vision\s+config(?:\s+(.+))?$"
    }
    
    def __init__(self, vision_server_url: str = "http://localhost:5003",
                 obsidian_api_url: str = "http://localhost:27124",
                 obsidian_api_key: str = None):
        """
        Inicializa o processador de comandos.
        
        Args:
            vision_server_url: URL do COMET Bridge Vision Server
            obsidian_api_url: URL da API REST do Obsidian
            obsidian_api_key: Chave de API do Obsidian
        """
        self.vision_url = vision_server_url
        self.obsidian_url = obsidian_api_url
        self.obsidian_key = obsidian_api_key or os.getenv("OBSIDIAN_API_KEY", "")
        
        # Última captura (para comando analyze)
        self.last_capture = None
        
        logger.info(f"[OBSIDIAN] Inicializado: Vision={vision_server_url}")
    
    def is_vision_command(self, text: str) -> bool:
        """Verifica se o texto é um comando de visão."""
        return text.strip().lower().startswith("/vision")
    
    def parse_command(self, text: str) -> Tuple[str, List[str]]:
        """
        Analisa um comando e extrai o tipo e argumentos.
        
        Args:
            text: Texto do comando
        
        Returns:
            Tupla (tipo_comando, lista_argumentos)
        """
        text = text.strip()
        
        for cmd_type, pattern in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                args = [g for g in match.groups() if g]
                return cmd_type, args
        
        return "unknown", []
    
    def execute_command(self, text: str, allow_cloud: bool = None) -> Dict:
        """
        Executa um comando de visão.
        
        Args:
            text: Texto do comando
            allow_cloud: Permitir uso de APIs cloud
        
        Returns:
            Resultado da execução
        """
        cmd_type, args = self.parse_command(text)
        
        logger.info(f"[OBSIDIAN] Comando: {cmd_type} | Args: {args}")
        
        handlers = {
            "capture": self._handle_capture,
            "analyze": self._handle_analyze,
            "ocr": self._handle_ocr,
            "screen": self._handle_screen,
            "doc": self._handle_doc,
            "help": self._handle_help,
            "status": self._handle_status,
            "providers": self._handle_providers,
            "config": self._handle_config,
            "unknown": self._handle_unknown
        }
        
        handler = handlers.get(cmd_type, self._handle_unknown)
        return handler(args, allow_cloud=allow_cloud)
    
    def _handle_capture(self, args: List[str], **kwargs) -> Dict:
        """Comando: /vision capture [mode]"""
        mode = args[0] if args else "full"
        
        try:
            response = requests.post(
                f"{self.vision_url}/capture",
                json={"mode": mode, "include_base64": True},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.last_capture = result
                
                return {
                    "success": True,
                    "type": "capture",
                    "message": f"✅ Captura realizada!\n\n**Arquivo**: {result.get('filepath')}\n**Tamanho**: {result.get('size', {}).get('width')}x{result.get('size', {}).get('height')}",
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Erro na captura: {response.text}"
                }
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_analyze(self, args: List[str], allow_cloud: bool = None, **kwargs) -> Dict:
        """Comando: /vision analyze [prompt]"""
        if not self.last_capture:
            return {
                "success": False,
                "message": "❌ Nenhuma captura disponível. Use `/vision capture` primeiro."
            }
        
        prompt = args[0] if args else "Descreva esta imagem em detalhes."
        
        try:
            response = requests.post(
                f"{self.vision_url}/analyze",
                json={
                    "image_base64": self.last_capture.get("base64"),
                    "prompt": prompt,
                    "allow_cloud": allow_cloud
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("requires_confirmation"):
                    return {
                        "success": False,
                        "requires_confirmation": True,
                        "message": f"⚠️ {result.get('message')}\n\nResponda com `/vision analyze {prompt} --cloud` para confirmar.",
                        "data": result
                    }
                
                if result.get("success"):
                    analysis = result.get("analysis", "")
                    provider = result.get("provider", "unknown")
                    
                    return {
                        "success": True,
                        "type": "analyze",
                        "message": f"🔍 **Análise** (via {provider}):\n\n{analysis}",
                        "data": result
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Erro na análise: {result.get('error')}"
                    }
            else:
                return {"success": False, "message": f"❌ Erro: {response.text}"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_ocr(self, args: List[str], allow_cloud: bool = None, **kwargs) -> Dict:
        """Comando: /vision ocr"""
        # Primeiro captura, depois faz OCR
        capture_result = self._handle_capture(["full"])
        
        if not capture_result.get("success"):
            return capture_result
        
        try:
            response = requests.post(
                f"{self.vision_url}/ocr",
                json={
                    "image_base64": self.last_capture.get("base64"),
                    "allow_cloud": allow_cloud
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    text = result.get("analysis", "")
                    provider = result.get("provider", "unknown")
                    
                    return {
                        "success": True,
                        "type": "ocr",
                        "message": f"📝 **Texto Extraído** (via {provider}):\n\n```\n{text}\n```",
                        "data": result
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Erro no OCR: {result.get('error')}"
                    }
            else:
                return {"success": False, "message": f"❌ Erro: {response.text}"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_screen(self, args: List[str], allow_cloud: bool = None, **kwargs) -> Dict:
        """Comando: /vision screen [pergunta]"""
        question = args[0] if args else None
        
        try:
            prompt = f"Analise esta captura de tela e responda: {question}" if question else None
            
            response = requests.post(
                f"{self.vision_url}/capture-and-analyze",
                json={
                    "mode": "full",
                    "prompt": prompt or "Analise esta captura de tela e descreva o que você vê.",
                    "allow_cloud": allow_cloud,
                    "save_to_obsidian": True
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                self.last_capture = {"base64": None, "filepath": result.get("capture", {}).get("filepath")}
                
                if result.get("success"):
                    analysis = result.get("analysis", {}).get("response", "")
                    provider = result.get("analysis", {}).get("provider", "unknown")
                    
                    msg = f"🖥️ **Análise da Tela** (via {provider}):\n\n{analysis}"
                    
                    if result.get("obsidian", {}).get("success"):
                        msg += f"\n\n📝 Nota salva: `{result.get('obsidian', {}).get('note_path')}`"
                    
                    return {
                        "success": True,
                        "type": "screen",
                        "message": msg,
                        "data": result
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Erro: {result.get('analysis', {}).get('error', 'Desconhecido')}"
                    }
            else:
                return {"success": False, "message": f"❌ Erro: {response.text}"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_doc(self, args: List[str], allow_cloud: bool = None, **kwargs) -> Dict:
        """Comando: /vision doc [tipo]"""
        doc_type = args[0] if args else "general"
        
        # Primeiro captura
        capture_result = self._handle_capture(["full"])
        if not capture_result.get("success"):
            return capture_result
        
        # Prompts por tipo de documento
        prompts = {
            "general": "Analise este documento e extraia as informações principais.",
            "invoice": "Analise esta nota fiscal e extraia: número, data, fornecedor, itens, totais.",
            "form": "Analise este formulário e extraia todos os campos preenchidos.",
            "report": "Analise este relatório e extraia: título, métricas, conclusões.",
            "table": "Extraia os dados desta tabela em formato markdown.",
            "code": "Extraia e formate o código visível nesta imagem."
        }
        
        prompt = prompts.get(doc_type, prompts["general"])
        
        try:
            response = requests.post(
                f"{self.vision_url}/analyze",
                json={
                    "image_base64": self.last_capture.get("base64"),
                    "prompt": prompt,
                    "allow_cloud": allow_cloud
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    analysis = result.get("analysis", "")
                    provider = result.get("provider", "unknown")
                    
                    return {
                        "success": True,
                        "type": "doc",
                        "message": f"📄 **Análise de Documento** ({doc_type}, via {provider}):\n\n{analysis}",
                        "data": result
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Erro: {result.get('error')}"
                    }
            else:
                return {"success": False, "message": f"❌ Erro: {response.text}"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_help(self, args: List[str], **kwargs) -> Dict:
        """Comando: /vision help"""
        help_text = """# 🔍 COMET Bridge Vision - Comandos

## Captura
- `/vision capture` - Captura tela inteira
- `/vision capture monitor` - Captura monitor específico
- `/vision capture window` - Captura janela ativa

## Análise
- `/vision analyze [prompt]` - Analisa última captura
- `/vision screen [pergunta]` - Captura e analisa
- `/vision ocr` - Extrai texto da tela

## Documentos
- `/vision doc` - Análise geral de documento
- `/vision doc invoice` - Analisa nota fiscal
- `/vision doc form` - Analisa formulário
- `/vision doc report` - Analisa relatório
- `/vision doc table` - Extrai tabela
- `/vision doc code` - Extrai código

## Sistema
- `/vision status` - Status do servidor
- `/vision providers` - Lista provedores de IA
- `/vision help` - Esta ajuda

## Opções
- Adicione `--cloud` para permitir APIs externas
- Exemplo: `/vision screen O que está na tela? --cloud`
"""
        return {
            "success": True,
            "type": "help",
            "message": help_text
        }
    
    def _handle_status(self, args: List[str], **kwargs) -> Dict:
        """Comando: /vision status"""
        try:
            response = requests.get(f"{self.vision_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                providers = ", ".join(data.get("providers", [])) or "Nenhum"
                
                return {
                    "success": True,
                    "type": "status",
                    "message": f"""# 📊 Status do COMET Bridge Vision

- **Status**: ✅ Online
- **Versão**: {data.get('version', '?')}
- **Provedores**: {providers}
- **Capturas**: {data.get('captures_count', 0)}
- **Histórico**: {data.get('history_count', 0)} operações
""",
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "message": "❌ Servidor Vision não está respondendo"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Erro ao conectar: {e}\n\nVerifique se o COMET Bridge Vision está rodando."
            }
    
    def _handle_providers(self, args: List[str], **kwargs) -> Dict:
        """Comando: /vision providers"""
        try:
            response = requests.get(f"{self.vision_url}/providers", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                lines = ["# 🤖 Provedores de IA\n"]
                for p in data.get("providers", []):
                    status = "✅" if p.get("available") else "❌"
                    local = "🏠 Local" if p.get("local") else "☁️ Cloud"
                    lines.append(f"- {status} **{p.get('name')}** ({local})")
                    lines.append(f"  - {p.get('description')}")
                
                return {
                    "success": True,
                    "type": "providers",
                    "message": "\n".join(lines),
                    "data": data
                }
            else:
                return {"success": False, "message": "❌ Erro ao listar provedores"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_config(self, args: List[str], **kwargs) -> Dict:
        """Comando: /vision config"""
        try:
            response = requests.get(f"{self.vision_url}/config", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                config = data.get("config", {})
                
                lines = ["# ⚙️ Configurações\n"]
                for key, value in config.items():
                    lines.append(f"- **{key}**: `{value}`")
                
                return {
                    "success": True,
                    "type": "config",
                    "message": "\n".join(lines),
                    "data": data
                }
            else:
                return {"success": False, "message": "❌ Erro ao obter configurações"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Erro: {e}"}
    
    def _handle_unknown(self, args: List[str], **kwargs) -> Dict:
        """Comando desconhecido."""
        return {
            "success": False,
            "message": "❓ Comando não reconhecido. Use `/vision help` para ver os comandos disponíveis."
        }
    
    def create_note(self, title: str, content: str, folder: str = "COMET Vision") -> Dict:
        """
        Cria uma nota no Obsidian.
        
        Args:
            title: Título da nota
            content: Conteúdo em Markdown
            folder: Pasta de destino
        
        Returns:
            Resultado da operação
        """
        try:
            # Sanitizar título
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            note_path = f"{folder}/{safe_title}.md"
            
            response = requests.put(
                f"{self.obsidian_url}/vault/{note_path}",
                headers={
                    "Content-Type": "text/markdown",
                    "Authorization": f"Bearer {self.obsidian_key}"
                },
                data=content.encode("utf-8"),
                timeout=10
            )
            
            return {
                "success": response.status_code in [200, 201, 204],
                "note_path": note_path,
                "status_code": response.status_code
            }
            
        except Exception as e:
            logger.error(f"[OBSIDIAN] Erro ao criar nota: {e}")
            return {"success": False, "error": str(e)}


# Função de conveniência
def process_vision_command(text: str, **kwargs) -> Dict:
    """
    Processa um comando de visão.
    
    Args:
        text: Texto do comando
        **kwargs: Argumentos adicionais
    
    Returns:
        Resultado do comando
    """
    commands = ObsidianVisionCommands()
    return commands.execute_command(text, **kwargs)


# Teste do módulo
if __name__ == "__main__":
    print("=== COMET Bridge Vision - Obsidian Integration Test ===\n")
    
    commands = ObsidianVisionCommands()
    
    # Testar parsing de comandos
    test_commands = [
        "/vision help",
        "/vision capture",
        "/vision screen O que está na tela?",
        "/vision doc invoice",
        "/vision analyze Descreva em detalhes"
    ]
    
    for cmd in test_commands:
        cmd_type, args = commands.parse_command(cmd)
        print(f"'{cmd}' -> tipo={cmd_type}, args={args}")
    
    print("\n=== Teste concluído! ===")
