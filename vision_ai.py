"""
COMET Bridge Vision - MÃ³dulo de AnÃ¡lise de Imagem por IA
=========================================================
IntegraÃ§Ã£o com mÃºltiplas IAs de visÃ£o: Ollama LLaVA (primÃ¡rio) + Claude/GPT-4 (fallback)

Autor: Manus AI
Data: 24/12/2024
VersÃ£o: 1.0
"""

import os
import sys
import json
import base64
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Union
from abc import ABC, abstractmethod

# ConfiguraÃ§Ã£o de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisionAI")


class VisionProvider(ABC):
    """Classe base abstrata para provedores de visÃ£o."""
    
    @abstractmethod
    def analyze(self, image_base64: str, prompt: str) -> Dict:
        """Analisa uma imagem com um prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provedor estÃ¡ disponÃ­vel."""
        pass


class OllamaVision(VisionProvider):
    """
    Provedor de visÃ£o usando Ollama com modelos multimodais (LLaVA, Llama Vision).
    
    Modelos suportados:
    - llava: LLaVA (Large Language and Vision Assistant)
    - llava:13b: VersÃ£o maior do LLaVA
    - bakllava: BakLLaVA
    - llama3.2-vision: Llama 3.2 com visÃ£o
    """
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llava"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"
        logger.info(f"[OLLAMA] Inicializado: {host} | Modelo: {model}")
    
    def is_available(self) -> bool:
        """Verifica se Ollama estÃ¡ rodando e o modelo estÃ¡ disponÃ­vel."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                available = self.model.split(":")[0] in model_names
                logger.info(f"[OLLAMA] DisponÃ­vel: {available} | Modelos: {model_names}")
                return available
            return False
        except Exception as e:
            logger.warning(f"[OLLAMA] NÃ£o disponÃ­vel: {e}")
            return False
    

    def _resize_image(self, image_base64, max_size=1920):
        try:
            from PIL import Image
            from io import BytesIO
            import base64 as b64
            img = Image.open(BytesIO(b64.b64decode(image_base64)))
            if max(img.size) > max_size:
                print(f"[RESIZE] {img.size} -> {ns}")
                img = img.resize(ns, Image.Resampling.LANCZOS)
                img = img.resize(ns, Image.Resampling.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                return b64.b64encode(buf.getvalue()).decode("utf-8")
            return image_base64
        except:
            return image_base64

    def analyze(self, image_base64: str, prompt: str, 
                stream: bool = False) -> Dict:
        """
        Analisa uma imagem usando Ollama.
        
        Args:
            image_base64: Imagem em Base64
            prompt: Pergunta ou instruÃ§Ã£o sobre a imagem
            stream: Se deve fazer streaming da resposta
        
        Returns:
            DicionÃ¡rio com resultado da anÃ¡lise
        """
        image_base64 = self._resize_image(image_base64)
        logger.info(f"[OLLAMA] Analisando imagem com prompt: {prompt[:50]}...")
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": stream
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300  # Timeout maior para anÃ¡lise de imagem
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "")
                
                logger.info(f"[OLLAMA] AnÃ¡lise concluÃ­da: {len(analysis)} chars")
                
                return {
                    "success": True,
                    "provider": "ollama",
                    "model": self.model,
                    "analysis": analysis,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "local": True,
                    "cost": 0.0
                }
            else:
                logger.error(f"[OLLAMA] Erro: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "provider": "ollama",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"[OLLAMA] ExceÃ§Ã£o: {e}")
            return {
                "success": False,
                "provider": "ollama",
                "error": str(e)
            }
    
    def list_models(self) -> List[str]:
        """Lista modelos disponÃ­veis no Ollama."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]
            return []
        except:
            return []


class ClaudeVision(VisionProvider):
    """
    Provedor de visÃ£o usando Claude (Anthropic).
    
    Modelos suportados:
    - claude-3-opus-20240229
    - claude-3-sonnet-20240229
    - claude-3-haiku-20240307
    - claude-3-5-sonnet-20241022
    """
    
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
        logger.info(f"[CLAUDE] Inicializado | Modelo: {model}")
    
    def is_available(self) -> bool:
        """Verifica se a API key estÃ¡ configurada."""
        available = bool(self.api_key)
        logger.info(f"[CLAUDE] DisponÃ­vel: {available}")
        return available
    
    def analyze(self, image_base64: str, prompt: str, 
                media_type: str = "image/png") -> Dict:
        """
        Analisa uma imagem usando Claude.
        
        Args:
            image_base64: Imagem em Base64
            prompt: Pergunta ou instruÃ§Ã£o sobre a imagem
            media_type: Tipo MIME da imagem
        
        Returns:
            DicionÃ¡rio com resultado da anÃ¡lise
        """
        if not self.api_key:
            return {
                "success": False,
                "provider": "claude",
                "error": "API key nÃ£o configurada"
            }
        
        logger.info(f"[CLAUDE] Analisando imagem com prompt: {prompt[:50]}...")
        
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("content", [{}])[0].get("text", "")
                
                logger.info(f"[CLAUDE] AnÃ¡lise concluÃ­da: {len(analysis)} chars")
                
                return {
                    "success": True,
                    "provider": "claude",
                    "model": self.model,
                    "analysis": analysis,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "local": False,
                    "cost": self._estimate_cost(image_base64, analysis)
                }
            else:
                logger.error(f"[CLAUDE] Erro: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "provider": "claude",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"[CLAUDE] ExceÃ§Ã£o: {e}")
            return {
                "success": False,
                "provider": "claude",
                "error": str(e)
            }
    
    def _estimate_cost(self, image_base64: str, response: str) -> float:
        """Estima o custo da chamada (aproximado)."""
        # Estimativa baseada em tokens
        image_tokens = len(image_base64) // 4 // 750  # ~750 chars por token de imagem
        response_tokens = len(response) // 4
        
        # PreÃ§os aproximados do Claude 3.5 Sonnet
        input_cost = image_tokens * 0.003 / 1000
        output_cost = response_tokens * 0.015 / 1000
        
        return round(input_cost + output_cost, 6)


class OpenAIVision(VisionProvider):
    """
    Provedor de visÃ£o usando OpenAI GPT-4 Vision.
    
    Modelos suportados:
    - gpt-4-vision-preview
    - gpt-4o
    - gpt-4o-mini
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o", 
                 base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.api_url = f"{self.base_url}/chat/completions"
        logger.info(f"[OPENAI] Inicializado | Modelo: {model}")
    
    def is_available(self) -> bool:
        """Verifica se a API key estÃ¡ configurada."""
        available = bool(self.api_key)
        logger.info(f"[OPENAI] DisponÃ­vel: {available}")
        return available
    
    def analyze(self, image_base64: str, prompt: str,
                media_type: str = "image/png") -> Dict:
        """
        Analisa uma imagem usando GPT-4 Vision.
        
        Args:
            image_base64: Imagem em Base64
            prompt: Pergunta ou instruÃ§Ã£o sobre a imagem
            media_type: Tipo MIME da imagem
        
        Returns:
            DicionÃ¡rio com resultado da anÃ¡lise
        """
        if not self.api_key:
            return {
                "success": False,
                "provider": "openai",
                "error": "API key nÃ£o configurada"
            }
        
        logger.info(f"[OPENAI] Analisando imagem com prompt: {prompt[:50]}...")
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logger.info(f"[OPENAI] AnÃ¡lise concluÃ­da: {len(analysis)} chars")
                
                return {
                    "success": True,
                    "provider": "openai",
                    "model": self.model,
                    "analysis": analysis,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "local": False,
                    "cost": self._estimate_cost(image_base64, analysis)
                }
            else:
                logger.error(f"[OPENAI] Erro: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "provider": "openai",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"[OPENAI] ExceÃ§Ã£o: {e}")
            return {
                "success": False,
                "provider": "openai",
                "error": str(e)
            }
    
    def _estimate_cost(self, image_base64: str, response: str) -> float:
        """Estima o custo da chamada (aproximado)."""
        # GPT-4o pricing aproximado
        image_tokens = 765  # Tokens fixos por imagem (low detail)
        response_tokens = len(response) // 4
        
        input_cost = image_tokens * 0.005 / 1000
        output_cost = response_tokens * 0.015 / 1000
        
        return round(input_cost + output_cost, 6)


class GeminiVision(VisionProvider):
    """
    Provedor de visÃ£o usando Google Gemini.
    
    Modelos suportados:
    - gemini-1.5-flash
    - gemini-1.5-pro
    - gemini-2.0-flash-exp
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        logger.info(f"[GEMINI] Inicializado | Modelo: {model}")
    
    def is_available(self) -> bool:
        """Verifica se a API key estÃ¡ configurada."""
        available = bool(self.api_key)
        logger.info(f"[GEMINI] DisponÃ­vel: {available}")
        return available
    
    def analyze(self, image_base64: str, prompt: str,
                media_type: str = "image/png") -> Dict:
        """
        Analisa uma imagem usando Gemini.
        """
        if not self.api_key:
            return {
                "success": False,
                "provider": "gemini",
                "error": "API key nÃ£o configurada"
            }
        
        logger.info(f"[GEMINI] Analisando imagem com prompt: {prompt[:50]}...")
        
        try:
            url = f"{self.api_url}?key={self.api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(url, json=payload, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                logger.info(f"[GEMINI] AnÃ¡lise concluÃ­da: {len(analysis)} chars")
                
                return {
                    "success": True,
                    "provider": "gemini",
                    "model": self.model,
                    "analysis": analysis,
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "local": False,
                    "cost": 0.0  # Gemini Flash Ã© gratuito para uso limitado
                }
            else:
                logger.error(f"[GEMINI] Erro: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "provider": "gemini",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"[GEMINI] ExceÃ§Ã£o: {e}")
            return {
                "success": False,
                "provider": "gemini",
                "error": str(e)
            }


class VisionAI:
    """
    Gerenciador de provedores de visÃ£o com fallback automÃ¡tico.
    
    Ordem de prioridade (configurÃ¡vel):
    1. Ollama LLaVA (local, gratuito, privado)
    2. Gemini (cloud, gratuito limitado)
    3. Claude (cloud, pago, alta qualidade)
    4. OpenAI GPT-4 (cloud, pago, alta qualidade)
    """
    
    def __init__(self, config: Dict = None):
        """
        Inicializa o gerenciador de visÃ£o.
        
        Args:
            config: ConfiguraÃ§Ãµes dos provedores
        """
        self.config = config or {}
        
        # Inicializar provedores
        self.providers = {
            "ollama": OllamaVision(
                host=self.config.get("ollama_host", "http://localhost:11434"),
                model=self.config.get("ollama_model", "llava")
            ),
            "gemini": GeminiVision(
                api_key=self.config.get("gemini_api_key"),
                model=self.config.get("gemini_model", "gemini-2.0-flash-exp")
            ),
            "claude": ClaudeVision(
                api_key=self.config.get("claude_api_key"),
                model=self.config.get("claude_model", "claude-3-5-sonnet-20241022")
            ),
            "openai": OpenAIVision(
                api_key=self.config.get("openai_api_key"),
                model=self.config.get("openai_model", "gpt-4o")
            )
        }
        
        # Ordem de prioridade (local primeiro)
        self.priority = self.config.get("priority", ["ollama", "gemini", "claude", "openai"])
        
        # ConfiguraÃ§Ã£o de privacidade
        self.require_confirmation_for_cloud = self.config.get("require_confirmation", True)
        
        logger.info(f"[VISION_AI] Inicializado com prioridade: {self.priority}")
    
    def get_available_providers(self) -> List[str]:
        """Retorna lista de provedores disponÃ­veis."""
        available = []
        for name in self.priority:
            if name in self.providers and self.providers[name].is_available():
                available.append(name)
        return available
    
    def analyze(self, image_base64: str, prompt: str,
                provider: str = None, allow_cloud: bool = None) -> Dict:
        """
        Analisa uma imagem usando o melhor provedor disponÃ­vel.
        
        Args:
            image_base64: Imagem em Base64
            prompt: Pergunta ou instruÃ§Ã£o sobre a imagem
            provider: ForÃ§ar uso de um provedor especÃ­fico
            allow_cloud: Permitir uso de provedores cloud (None = perguntar)
        
        Returns:
            DicionÃ¡rio com resultado da anÃ¡lise
        """
        # Se provedor especÃ­fico foi solicitado
        if provider and provider in self.providers:
            if self.providers[provider].is_available():
                return self.providers[provider].analyze(image_base64, prompt)
            else:
                logger.warning(f"[VISION_AI] Provedor {provider} nÃ£o disponÃ­vel")
        
        # Tentar provedores na ordem de prioridade
        for name in self.priority:
            prov = self.providers.get(name)
            if not prov or not prov.is_available():
                continue
            
            # Verificar se Ã© local ou cloud
            is_local = name == "ollama"
            
            # Se Ã© cloud e precisa confirmaÃ§Ã£o
            if not is_local and self.require_confirmation_for_cloud:
                if allow_cloud is None:
                    # Retornar pedido de confirmaÃ§Ã£o
                    return {
                        "success": False,
                        "requires_confirmation": True,
                        "provider": name,
                        "message": f"Deseja enviar a imagem para {name} (cloud)? Dados serÃ£o enviados para servidores externos.",
                        "prompt": prompt
                    }
                elif not allow_cloud:
                    continue  # Pular provedores cloud
            
            # Tentar anÃ¡lise
            result = prov.analyze(image_base64, prompt)
            if result.get("success"):
                return result
            
            logger.warning(f"[VISION_AI] Falha em {name}, tentando prÃ³ximo...")
        
        # Nenhum provedor funcionou
        return {
            "success": False,
            "error": "Nenhum provedor de visÃ£o disponÃ­vel",
            "tried": self.get_available_providers()
        }
    
    def analyze_with_ocr(self, image_base64: str, **kwargs) -> Dict:
        """
        Analisa imagem focando em extraÃ§Ã£o de texto (OCR).
        
        Args:
            image_base64: Imagem em Base64
            **kwargs: Argumentos adicionais para analyze()
        
        Returns:
            DicionÃ¡rio com texto extraÃ­do
        """
        prompt = """Extraia TODO o texto visÃ­vel nesta imagem.
        
InstruÃ§Ãµes:
1. Leia todo o texto, incluindo tÃ­tulos, parÃ¡grafos, labels, botÃµes, etc.
2. Mantenha a estrutura e formataÃ§Ã£o quando possÃ­vel
3. Se houver tabelas, formate como tabela markdown
4. Se houver cÃ³digo, formate como bloco de cÃ³digo
5. Indique elementos visuais importantes entre [colchetes]

Retorne apenas o texto extraÃ­do, sem comentÃ¡rios adicionais."""
        
        return self.analyze(image_base64, prompt, **kwargs)
    
    def analyze_screen(self, image_base64: str, question: str = None, **kwargs) -> Dict:
        """
        Analisa uma captura de tela.
        
        Args:
            image_base64: Imagem em Base64
            question: Pergunta especÃ­fica sobre a tela (opcional)
            **kwargs: Argumentos adicionais para analyze()
        
        Returns:
            DicionÃ¡rio com anÃ¡lise da tela
        """
        if question:
            prompt = f"""Analise esta captura de tela e responda: {question}

Seja especÃ­fico e detalhado na sua resposta."""
        else:
            prompt = """Analise esta captura de tela e descreva:

1. **Aplicativo/Contexto**: Qual programa ou site estÃ¡ aberto?
2. **ConteÃºdo Principal**: O que estÃ¡ sendo mostrado?
3. **Elementos Importantes**: BotÃµes, menus, notificaÃ§Ãµes, etc.
4. **Estado Atual**: O que o usuÃ¡rio parece estar fazendo?
5. **AÃ§Ãµes Sugeridas**: O que pode ser feito a seguir?

Seja conciso mas completo."""
        
        return self.analyze(image_base64, prompt, **kwargs)
    
    def analyze_document(self, image_base64: str, doc_type: str = "general", **kwargs) -> Dict:
        """
        Analisa um documento/imagem de documento.
        
        Args:
            image_base64: Imagem em Base64
            doc_type: Tipo de documento (general, invoice, form, report)
            **kwargs: Argumentos adicionais para analyze()
        
        Returns:
            DicionÃ¡rio com anÃ¡lise do documento
        """
        prompts = {
            "general": """Analise este documento e extraia:
1. Tipo de documento
2. InformaÃ§Ãµes principais
3. Dados estruturados (se houver)
4. Resumo do conteÃºdo""",
            
            "invoice": """Analise esta nota fiscal/fatura e extraia:
1. NÃºmero do documento
2. Data de emissÃ£o
3. Fornecedor/Emissor
4. Cliente/DestinatÃ¡rio
5. Itens (descriÃ§Ã£o, quantidade, valor)
6. Totais (subtotal, impostos, total)
7. Forma de pagamento""",
            
            "form": """Analise este formulÃ¡rio e extraia:
1. Tipo de formulÃ¡rio
2. Campos preenchidos (nome do campo: valor)
3. Campos vazios
4. Assinaturas ou carimbos (se houver)""",
            
            "report": """Analise este relatÃ³rio e extraia:
1. TÃ­tulo/Assunto
2. Data/PerÃ­odo
3. Principais mÃ©tricas/nÃºmeros
4. ConclusÃµes ou destaques
5. GrÃ¡ficos/Tabelas (descreva o conteÃºdo)"""
        }
        
        prompt = prompts.get(doc_type, prompts["general"])
        return self.analyze(image_base64, prompt, **kwargs)


# FunÃ§Ã£o de conveniÃªncia
def analyze_image(image_base64: str, prompt: str, **kwargs) -> Dict:
    """
    FunÃ§Ã£o de conveniÃªncia para anÃ¡lise rÃ¡pida.
    
    Args:
        image_base64: Imagem em Base64
        prompt: Pergunta ou instruÃ§Ã£o
        **kwargs: ConfiguraÃ§Ãµes adicionais
    
    Returns:
        Resultado da anÃ¡lise
    """
    vision = VisionAI(kwargs.get("config", {}))
    return vision.analyze(image_base64, prompt, **kwargs)


# Teste do mÃ³dulo
if __name__ == "__main__":
    print("=== COMET Bridge Vision - Vision AI Test ===\n")
    
    # Criar instÃ¢ncia
    vision = VisionAI()
    
    # Listar provedores disponÃ­veis
    print("Provedores disponÃ­veis:")
    for provider in vision.get_available_providers():
        print(f"  âœ“ {provider}")
    
    print("\n=== Teste concluÃ­do! ===")
