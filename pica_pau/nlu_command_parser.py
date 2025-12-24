"""
NLU Command Parser - Parse de linguagem natural para comandos estruturados
Parte do Agente PicaPau - COMET Bridge Vision

Este módulo interpreta comandos em linguagem natural e os converte em
ações estruturadas que o executor Playwright pode processar.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("NLUParser")


class ActionType(Enum):
    """Tipos de ações suportadas pelo PicaPau"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    FILL_FORM = "fill_form"
    LOGIN = "login"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SELECT = "select"
    HOVER = "hover"
    PRESS_KEY = "press_key"
    DOWNLOAD = "download"
    UPLOAD = "upload"


@dataclass
class ParsedAction:
    """Representa uma ação parseada do comando"""
    action_type: ActionType
    target: Optional[str] = None
    value: Optional[str] = None
    selector: Optional[str] = None
    options: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "value": self.value,
            "selector": self.selector,
            "options": self.options or {}
        }


@dataclass
class ParsedCommand:
    """Resultado do parsing de um comando completo"""
    original_command: str
    intent: str
    actions: List[ParsedAction]
    entities: Dict[str, Any]
    confidence: float
    requires_credentials: bool = False
    credential_keys: List[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Verifica se o comando foi parseado com sucesso"""
        return self.intent != "unknown" and self.confidence > 0.5 and len(self.actions) > 0
    
    def to_dict(self) -> Dict:
        return {
            "original_command": self.original_command,
            "intent": self.intent,
            "actions": [a.to_dict() for a in self.actions],
            "entities": self.entities,
            "confidence": self.confidence,
            "requires_credentials": self.requires_credentials,
            "credential_keys": self.credential_keys or []
        }


class NLUCommandParser:
    """
    Parser de comandos em linguagem natural para o Agente PicaPau.
    
    Suporta comandos como:
    - "PicaPau entre no Hotmail com email@example.com senha 123456"
    - "PicaPau clique no botão Enviar"
    - "PicaPau navegue para google.com e pesquise por Python"
    - "PicaPau preencha o formulário com nome João e email joao@email.com"
    """
    
    # Padrões de sites conhecidos
    KNOWN_SITES = {
        "hotmail": "https://outlook.live.com/mail/0/inbox",
        "outlook": "https://outlook.live.com/mail/0/inbox",
        "gmail": "https://mail.google.com",
        "google": "https://www.google.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "linkedin": "https://www.linkedin.com",
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "whatsapp": "https://web.whatsapp.com",
        "telegram": "https://web.telegram.org",
    }
    
    # Padrões regex para extração de entidades
    PATTERNS = {
        "email": r'[\w\.-]+@[\w\.-]+\.\w+',
        "url": r'https?://[^\s]+|www\.[^\s]+|\w+\.(com|org|net|br|io|dev)[^\s]*',
        "password": r'senha\s+(\S+)',
        "username": r'usuario\s+(\S+)|user\s+(\S+)',
        "button": r'bot[aã]o\s+["\']?([^"\']+)["\']?',
        "link": r'link\s+["\']?([^"\']+)["\']?',
        "field": r'campo\s+["\']?([^"\']+)["\']?',
        "text": r'texto?\s+["\']?([^"\']+)["\']?',
    }
    
    # Verbos de ação e seus mapeamentos
    ACTION_VERBS = {
        # Navegação
        "entre": ActionType.LOGIN,
        "entrar": ActionType.LOGIN,
        "login": ActionType.LOGIN,
        "logar": ActionType.LOGIN,
        "acesse": ActionType.NAVIGATE,
        "acessar": ActionType.NAVIGATE,
        "navegue": ActionType.NAVIGATE,
        "navegar": ActionType.NAVIGATE,
        "abra": ActionType.NAVIGATE,
        "abrir": ActionType.NAVIGATE,
        "va": ActionType.NAVIGATE,
        "ir": ActionType.NAVIGATE,
        
        # Interação
        "clique": ActionType.CLICK,
        "clicar": ActionType.CLICK,
        "click": ActionType.CLICK,
        "pressione": ActionType.CLICK,
        "pressionar": ActionType.CLICK,
        "aperte": ActionType.CLICK,
        "apertar": ActionType.CLICK,
        
        # Digitação
        "digite": ActionType.TYPE,
        "digitar": ActionType.TYPE,
        "escreva": ActionType.TYPE,
        "escrever": ActionType.TYPE,
        "preencha": ActionType.FILL_FORM,
        "preencher": ActionType.FILL_FORM,
        "insira": ActionType.TYPE,
        "inserir": ActionType.TYPE,
        
        # Scroll
        "role": ActionType.SCROLL,
        "rolar": ActionType.SCROLL,
        "scroll": ActionType.SCROLL,
        "desça": ActionType.SCROLL,
        "descer": ActionType.SCROLL,
        "suba": ActionType.SCROLL,
        "subir": ActionType.SCROLL,
        
        # Outros
        "espere": ActionType.WAIT,
        "esperar": ActionType.WAIT,
        "aguarde": ActionType.WAIT,
        "aguardar": ActionType.WAIT,
        "selecione": ActionType.SELECT,
        "selecionar": ActionType.SELECT,
        "escolha": ActionType.SELECT,
        "escolher": ActionType.SELECT,
        "capture": ActionType.SCREENSHOT,
        "capturar": ActionType.SCREENSHOT,
        "screenshot": ActionType.SCREENSHOT,
        "baixe": ActionType.DOWNLOAD,
        "baixar": ActionType.DOWNLOAD,
        "download": ActionType.DOWNLOAD,
        "envie": ActionType.UPLOAD,
        "enviar": ActionType.UPLOAD,
        "upload": ActionType.UPLOAD,
    }
    
    def __init__(self):
        logger.info("[NLU_PARSER] Inicializado")
    
    def parse(self, command: str) -> ParsedCommand:
        """
        Faz o parse de um comando em linguagem natural.
        
        Args:
            command: Comando em linguagem natural (ex: "PicaPau entre no Gmail")
            
        Returns:
            ParsedCommand com as ações estruturadas
        """
        logger.info(f"[NLU_PARSER] Parseando comando: {command}")
        
        # Normalizar comando
        normalized = self._normalize_command(command)
        
        # Extrair entidades
        entities = self._extract_entities(command)
        
        # Identificar intent principal
        intent, confidence = self._identify_intent(normalized)
        
        # Gerar ações baseadas no intent e entidades
        actions = self._generate_actions(intent, entities, normalized)
        
        # Verificar se precisa de credenciais
        requires_creds, cred_keys = self._check_credentials_needed(entities, intent)
        
        result = ParsedCommand(
            original_command=command,
            intent=intent,
            actions=actions,
            entities=entities,
            confidence=confidence,
            requires_credentials=requires_creds,
            credential_keys=cred_keys
        )
        
        logger.info(f"[NLU_PARSER] Resultado: {result.to_dict()}")
        return result
    
    def _normalize_command(self, command: str) -> str:
        """Normaliza o comando removendo prefixo PicaPau e caracteres especiais"""
        # Remover prefixo "PicaPau" ou variações
        normalized = re.sub(r'^pica\s*pau\s*', '', command, flags=re.IGNORECASE)
        # Converter para minúsculas
        normalized = normalized.lower().strip()
        # Remover pontuação extra
        normalized = re.sub(r'[,;!?]+', ' ', normalized)
        return normalized
    
    def _extract_entities(self, command: str) -> Dict[str, Any]:
        """Extrai entidades do comando (emails, URLs, senhas, etc.)"""
        entities = {}
        
        # Extrair email
        emails = re.findall(self.PATTERNS["email"], command)
        if emails:
            entities["email"] = emails[0]
            entities["all_emails"] = emails
        
        # Extrair URL
        urls = re.findall(self.PATTERNS["url"], command, re.IGNORECASE)
        if urls:
            entities["url"] = urls[0] if isinstance(urls[0], str) else urls[0][0]
        
        # Extrair senha (com cuidado para não logar)
        password_match = re.search(self.PATTERNS["password"], command, re.IGNORECASE)
        if password_match:
            entities["password"] = password_match.group(1)
            entities["has_password"] = True
        
        # Extrair nome de usuário
        username_match = re.search(self.PATTERNS["username"], command, re.IGNORECASE)
        if username_match:
            entities["username"] = username_match.group(1) or username_match.group(2)
        
        # Extrair site conhecido
        for site_name, site_url in self.KNOWN_SITES.items():
            if site_name in command.lower():
                entities["site_name"] = site_name
                entities["site_url"] = site_url
                break
        
        # Extrair opções especiais
        if "salvar senha" in command.lower() or "lembrar" in command.lower():
            entities["save_credentials"] = True
        
        if "nova aba" in command.lower() or "new tab" in command.lower():
            entities["new_tab"] = True
            
        if "incognito" in command.lower() or "privado" in command.lower():
            entities["incognito"] = True
        
        return entities
    
    def _identify_intent(self, normalized: str) -> tuple:
        """Identifica a intenção principal do comando"""
        words = normalized.split()
        
        # Procurar verbo de ação
        for word in words:
            if word in self.ACTION_VERBS:
                action_type = self.ACTION_VERBS[word]
                return action_type.value, 0.9
        
        # Fallback: tentar identificar pelo contexto
        if any(site in normalized for site in self.KNOWN_SITES.keys()):
            return ActionType.NAVIGATE.value, 0.7
        
        if "senha" in normalized or "login" in normalized:
            return ActionType.LOGIN.value, 0.8
        
        return "unknown", 0.3
    
    def _generate_actions(self, intent: str, entities: Dict, normalized: str) -> List[ParsedAction]:
        """Gera lista de ações baseadas no intent e entidades"""
        actions = []
        
        if intent == ActionType.LOGIN.value:
            actions = self._generate_login_actions(entities)
        elif intent == ActionType.NAVIGATE.value:
            actions = self._generate_navigate_actions(entities)
        elif intent == ActionType.CLICK.value:
            actions = self._generate_click_actions(entities, normalized)
        elif intent == ActionType.TYPE.value:
            actions = self._generate_type_actions(entities, normalized)
        elif intent == ActionType.FILL_FORM.value:
            actions = self._generate_fill_form_actions(entities, normalized)
        else:
            # Ação genérica
            actions.append(ParsedAction(
                action_type=ActionType.NAVIGATE,
                target=entities.get("url") or entities.get("site_url"),
                options={"wait_for_load": True}
            ))
        
        return actions
    
    def _generate_login_actions(self, entities: Dict) -> List[ParsedAction]:
        """Gera ações para fluxo de login"""
        actions = []
        
        # 1. Navegar para o site
        url = entities.get("site_url") or entities.get("url")
        if url:
            actions.append(ParsedAction(
                action_type=ActionType.NAVIGATE,
                target=url,
                options={"wait_for_load": True}
            ))
        
        # 2. Aguardar carregamento
        actions.append(ParsedAction(
            action_type=ActionType.WAIT,
            value="2000",
            options={"type": "timeout"}
        ))
        
        # 3. Preencher email/usuário
        email = entities.get("email") or entities.get("username")
        if email:
            actions.append(ParsedAction(
                action_type=ActionType.TYPE,
                target="email_field",
                value=email,
                selector='input[type="email"], input[name="email"], input[name="username"], input[name="loginfmt"], #identifierId',
                options={"clear_first": True}
            ))
            
            # Clicar em próximo (comum em logins modernos)
            actions.append(ParsedAction(
                action_type=ActionType.CLICK,
                target="next_button",
                selector='button[type="submit"], input[type="submit"], #idSIButton9, .VfPpkd-LgbsSe',
                options={"wait_after": 2000}
            ))
        
        # 4. Preencher senha
        if entities.get("has_password"):
            actions.append(ParsedAction(
                action_type=ActionType.WAIT,
                value="2000",
                options={"type": "timeout"}
            ))
            
            actions.append(ParsedAction(
                action_type=ActionType.TYPE,
                target="password_field",
                value="{{PASSWORD}}",  # Placeholder para segurança
                selector='input[type="password"], input[name="passwd"], input[name="password"]',
                options={"clear_first": True, "credential_key": "password"}
            ))
            
            # Clicar em entrar
            actions.append(ParsedAction(
                action_type=ActionType.CLICK,
                target="login_button",
                selector='button[type="submit"], input[type="submit"], #idSIButton9',
                options={"wait_after": 3000}
            ))
        
        # 5. Salvar credenciais se solicitado
        if entities.get("save_credentials"):
            actions.append(ParsedAction(
                action_type=ActionType.CLICK,
                target="save_credentials_button",
                selector='button:has-text("Sim"), button:has-text("Yes"), button:has-text("Manter"), #idSIButton9',
                options={"optional": True, "wait_after": 1000}
            ))
        
        # 6. Screenshot final para validação
        actions.append(ParsedAction(
            action_type=ActionType.SCREENSHOT,
            target="login_result",
            options={"for_validation": True}
        ))
        
        return actions
    
    def _generate_navigate_actions(self, entities: Dict) -> List[ParsedAction]:
        """Gera ações para navegação"""
        actions = []
        
        url = entities.get("url") or entities.get("site_url")
        if url:
            # Adicionar protocolo se necessário
            if not url.startswith("http"):
                url = "https://" + url
            
            actions.append(ParsedAction(
                action_type=ActionType.NAVIGATE,
                target=url,
                options={
                    "wait_for_load": True,
                    "new_tab": entities.get("new_tab", False)
                }
            ))
        
        return actions
    
    def _generate_click_actions(self, entities: Dict, normalized: str) -> List[ParsedAction]:
        """Gera ações de clique"""
        actions = []
        
        # Extrair alvo do clique
        button_match = re.search(r'(?:no|em|o)\s+(?:bot[aã]o\s+)?["\']?([^"\']+)["\']?', normalized)
        target = button_match.group(1) if button_match else "unknown"
        
        actions.append(ParsedAction(
            action_type=ActionType.CLICK,
            target=target,
            selector=f'button:has-text("{target}"), a:has-text("{target}"), [aria-label*="{target}"]',
            options={"wait_after": 1000}
        ))
        
        return actions
    
    def _generate_type_actions(self, entities: Dict, normalized: str) -> List[ParsedAction]:
        """Gera ações de digitação"""
        actions = []
        
        # Extrair texto a ser digitado
        text_match = re.search(r'(?:digite|escreva|insira)\s+["\']?([^"\']+)["\']?', normalized)
        text = text_match.group(1) if text_match else ""
        
        actions.append(ParsedAction(
            action_type=ActionType.TYPE,
            value=text,
            selector='input:focus, textarea:focus, [contenteditable="true"]:focus',
            options={"clear_first": False}
        ))
        
        return actions
    
    def _generate_fill_form_actions(self, entities: Dict, normalized: str) -> List[ParsedAction]:
        """Gera ações para preenchimento de formulário"""
        actions = []
        
        # Extrair campos do formulário
        field_pattern = r'(\w+)\s+["\']?([^"\']+)["\']?'
        fields = re.findall(field_pattern, normalized)
        
        for field_name, field_value in fields:
            if field_name.lower() in ["com", "e", "o", "a", "no", "na"]:
                continue
                
            actions.append(ParsedAction(
                action_type=ActionType.TYPE,
                target=field_name,
                value=field_value,
                selector=f'input[name*="{field_name}"], input[placeholder*="{field_name}"], label:has-text("{field_name}") + input',
                options={"clear_first": True}
            ))
        
        return actions
    
    def _check_credentials_needed(self, entities: Dict, intent: str) -> tuple:
        """Verifica se o comando precisa de credenciais armazenadas"""
        requires = False
        keys = []
        
        if intent == ActionType.LOGIN.value:
            requires = True
            if entities.get("has_password"):
                keys.append("password")
            if entities.get("email"):
                keys.append("email")
        
        return requires, keys


# Teste standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = NLUCommandParser()
    
    # Testes
    test_commands = [
        "PicaPau entre no Hotmail com rud.pa@hotmail.com senha Rudson2323##, salvar senha",
        "PicaPau navegue para google.com",
        "PicaPau clique no botão Enviar",
        "PicaPau preencha o formulário com nome João e email joao@email.com",
    ]
    
    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"Comando: {cmd}")
        result = parser.parse(cmd)
        print(f"Resultado: {json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}")
