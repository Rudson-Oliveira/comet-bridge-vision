"""
Visual Feedback Validator - Validação de ações via COMET Vision
Parte do Agente PicaPau - COMET Bridge Vision

Este módulo usa o COMET Vision (LLaVA) para validar se as ações
executadas pelo PicaPau foram bem-sucedidas através de análise visual.
"""

import logging
import base64
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("VisualValidator")


class ValidationStatus(Enum):
    """Status de validação"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Resultado de uma validação visual"""
    status: ValidationStatus
    confidence: float
    message: str
    details: Dict[str, Any]
    suggestions: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "confidence": self.confidence,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions
        }


class VisualFeedbackValidator:
    """
    Validador de feedback visual usando COMET Vision.
    
    Usa LLaVA ou outro modelo de visão para analisar screenshots
    e determinar se as ações foram executadas com sucesso.
    """
    
    # Prompts de validação para diferentes cenários
    VALIDATION_PROMPTS = {
        "login_success": """Analise esta tela e responda em JSON:
{
    "logged_in": true/false,
    "indicators": ["lista de indicadores que mostram login bem-sucedido"],
    "errors_visible": ["lista de mensagens de erro visíveis"],
    "current_page": "descrição da página atual",
    "confidence": 0.0-1.0
}

Indicadores de login bem-sucedido incluem:
- Caixa de entrada de email visível
- Nome do usuário aparecendo
- Menu de perfil/conta
- Ausência de formulário de login

Indicadores de falha:
- Mensagem de erro visível
- Formulário de login ainda presente
- Captcha ou verificação adicional""",

        "navigation_success": """Analise esta tela e responda em JSON:
{
    "page_loaded": true/false,
    "current_url_matches": true/false,
    "page_title": "título da página",
    "main_content_visible": true/false,
    "loading_indicators": true/false,
    "error_page": true/false,
    "confidence": 0.0-1.0
}""",

        "form_filled": """Analise esta tela e responda em JSON:
{
    "form_visible": true/false,
    "fields_filled": ["lista de campos que parecem preenchidos"],
    "fields_empty": ["lista de campos vazios"],
    "validation_errors": ["erros de validação visíveis"],
    "submit_button_enabled": true/false,
    "confidence": 0.0-1.0
}""",

        "click_result": """Analise esta tela e responda em JSON:
{
    "action_completed": true/false,
    "visible_changes": ["mudanças visíveis após o clique"],
    "new_elements": ["novos elementos que apareceram"],
    "removed_elements": ["elementos que desapareceram"],
    "modal_opened": true/false,
    "page_changed": true/false,
    "confidence": 0.0-1.0
}""",

        "general_state": """Descreva o estado atual desta tela em JSON:
{
    "page_type": "tipo de página (login, dashboard, formulário, etc)",
    "main_elements": ["elementos principais visíveis"],
    "user_logged_in": true/false/unknown,
    "errors_visible": ["erros ou alertas visíveis"],
    "loading_state": "loaded/loading/error",
    "interactive_elements": ["botões e links principais"],
    "confidence": 0.0-1.0
}"""
    }
    
    # Padrões de sucesso para diferentes ações
    SUCCESS_PATTERNS = {
        "login": {
            "positive": ["inbox", "caixa de entrada", "bem-vindo", "welcome", "dashboard", "perfil", "profile", "conta", "account"],
            "negative": ["erro", "error", "incorreta", "invalid", "falha", "failed", "tente novamente", "try again", "captcha"]
        },
        "navigate": {
            "positive": ["carregado", "loaded", "página", "page"],
            "negative": ["404", "não encontrado", "not found", "erro", "error", "timeout"]
        },
        "form": {
            "positive": ["preenchido", "filled", "válido", "valid"],
            "negative": ["obrigatório", "required", "inválido", "invalid", "erro", "error"]
        }
    }
    
    def __init__(self, vision_analyzer=None):
        """
        Inicializa o validador.
        
        Args:
            vision_analyzer: Instância do VisionAI para análise de imagens
        """
        self.vision_analyzer = vision_analyzer
        logger.info("[VISUAL_VALIDATOR] Inicializado")
    
    def set_vision_analyzer(self, analyzer):
        """Define o analisador de visão"""
        self.vision_analyzer = analyzer
    
    async def validate_action(self, 
                              action_type: str,
                              screenshot_b64: str,
                              expected_result: Dict = None,
                              context: Dict = None) -> ValidationResult:
        """
        Valida se uma ação foi executada com sucesso.
        
        Args:
            action_type: Tipo da ação (login, navigate, click, etc.)
            screenshot_b64: Screenshot em base64 para análise
            expected_result: Resultado esperado da ação
            context: Contexto adicional (URL esperada, etc.)
            
        Returns:
            ValidationResult com status e detalhes
        """
        logger.info(f"[VISUAL_VALIDATOR] Validando ação: {action_type}")
        
        if not self.vision_analyzer:
            logger.warning("[VISUAL_VALIDATOR] Analisador de visão não configurado")
            return ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=0.0,
                message="Analisador de visão não disponível",
                details={},
                suggestions=["Configure o COMET Vision para validação visual"]
            )
        
        try:
            # Selecionar prompt apropriado
            prompt = self._get_validation_prompt(action_type, expected_result, context)
            
            # Analisar screenshot com LLaVA
            analysis = await self._analyze_screenshot(screenshot_b64, prompt)
            
            # Interpretar resultado
            result = self._interpret_analysis(action_type, analysis, expected_result, context)
            
            return result
        
        except Exception as e:
            logger.error(f"[VISUAL_VALIDATOR] Erro na validação: {str(e)}")
            return ValidationResult(
                status=ValidationStatus.ERROR,
                confidence=0.0,
                message=f"Erro na validação: {str(e)}",
                details={"error": str(e)},
                suggestions=["Verifique a conexão com o COMET Vision"]
            )
    
    def validate_action_sync(self,
                             action_type: str,
                             screenshot_b64: str,
                             expected_result: Dict = None,
                             context: Dict = None) -> ValidationResult:
        """
        Versão síncrona da validação (para uso em Flask).
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.validate_action(action_type, screenshot_b64, expected_result, context)
        )
    
    def _get_validation_prompt(self, 
                               action_type: str, 
                               expected_result: Dict = None,
                               context: Dict = None) -> str:
        """Gera o prompt de validação apropriado"""
        
        # Mapear tipo de ação para prompt
        prompt_key = "general_state"
        
        if action_type in ["login", "LOGIN"]:
            prompt_key = "login_success"
        elif action_type in ["navigate", "NAVIGATE"]:
            prompt_key = "navigation_success"
        elif action_type in ["fill_form", "FILL_FORM", "type", "TYPE"]:
            prompt_key = "form_filled"
        elif action_type in ["click", "CLICK"]:
            prompt_key = "click_result"
        
        base_prompt = self.VALIDATION_PROMPTS.get(prompt_key, self.VALIDATION_PROMPTS["general_state"])
        
        # Adicionar contexto específico se disponível
        if context:
            context_info = "\n\nContexto adicional:\n"
            if context.get("expected_url"):
                context_info += f"- URL esperada: {context['expected_url']}\n"
            if context.get("expected_elements"):
                context_info += f"- Elementos esperados: {', '.join(context['expected_elements'])}\n"
            if context.get("previous_action"):
                context_info += f"- Ação anterior: {context['previous_action']}\n"
            
            base_prompt += context_info
        
        return base_prompt
    
    async def _analyze_screenshot(self, screenshot_b64: str, prompt: str) -> Dict:
        """Analisa screenshot usando COMET Vision"""
        
        if not self.vision_analyzer:
            return {"error": "Vision analyzer not available"}
        
        try:
            # Chamar o analisador de visão
            result = self.vision_analyzer.analyze(screenshot_b64, prompt)
            
            if result.get("success"):
                analysis_text = result.get("analysis", "")
                
                # Tentar extrair JSON da resposta
                json_match = re.search(r'\{[^{}]*\}', analysis_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
                
                # Se não conseguir extrair JSON, retornar texto
                return {"raw_analysis": analysis_text, "parsed": False}
            else:
                return {"error": result.get("error", "Unknown error")}
        
        except Exception as e:
            logger.error(f"[VISUAL_VALIDATOR] Erro na análise: {str(e)}")
            return {"error": str(e)}
    
    def _interpret_analysis(self,
                           action_type: str,
                           analysis: Dict,
                           expected_result: Dict = None,
                           context: Dict = None) -> ValidationResult:
        """Interpreta o resultado da análise visual"""
        
        # Se houve erro na análise
        if "error" in analysis:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                confidence=0.0,
                message=f"Erro na análise: {analysis['error']}",
                details=analysis,
                suggestions=["Tente novamente", "Verifique a conexão com o modelo de visão"]
            )
        
        # Se a análise não foi parseada como JSON
        if analysis.get("parsed") == False:
            return self._interpret_raw_analysis(action_type, analysis.get("raw_analysis", ""))
        
        # Interpretar baseado no tipo de ação
        if action_type in ["login", "LOGIN"]:
            return self._interpret_login_result(analysis)
        elif action_type in ["navigate", "NAVIGATE"]:
            return self._interpret_navigation_result(analysis, context)
        elif action_type in ["fill_form", "FILL_FORM", "type", "TYPE"]:
            return self._interpret_form_result(analysis)
        elif action_type in ["click", "CLICK"]:
            return self._interpret_click_result(analysis)
        else:
            return self._interpret_general_result(analysis)
    
    def _interpret_login_result(self, analysis: Dict) -> ValidationResult:
        """Interpreta resultado de validação de login"""
        
        logged_in = analysis.get("logged_in", False)
        confidence = analysis.get("confidence", 0.5)
        errors = analysis.get("errors_visible", [])
        indicators = analysis.get("indicators", [])
        
        if logged_in and not errors:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                confidence=confidence,
                message="Login realizado com sucesso",
                details={
                    "logged_in": True,
                    "indicators": indicators,
                    "current_page": analysis.get("current_page", "")
                },
                suggestions=[]
            )
        elif errors:
            return ValidationResult(
                status=ValidationStatus.FAILED,
                confidence=confidence,
                message="Login falhou - erros detectados",
                details={
                    "logged_in": False,
                    "errors": errors
                },
                suggestions=[
                    "Verifique as credenciais",
                    "Pode ser necessário resolver captcha",
                    "Tente novamente em alguns minutos"
                ]
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=confidence,
                message="Não foi possível confirmar o login",
                details=analysis,
                suggestions=["Verifique manualmente o estado do login"]
            )
    
    def _interpret_navigation_result(self, analysis: Dict, context: Dict = None) -> ValidationResult:
        """Interpreta resultado de validação de navegação"""
        
        page_loaded = analysis.get("page_loaded", False)
        error_page = analysis.get("error_page", False)
        confidence = analysis.get("confidence", 0.5)
        
        if page_loaded and not error_page:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                confidence=confidence,
                message="Página carregada com sucesso",
                details={
                    "page_title": analysis.get("page_title", ""),
                    "content_visible": analysis.get("main_content_visible", False)
                },
                suggestions=[]
            )
        elif error_page:
            return ValidationResult(
                status=ValidationStatus.FAILED,
                confidence=confidence,
                message="Página de erro detectada",
                details=analysis,
                suggestions=[
                    "Verifique a URL",
                    "O site pode estar indisponível",
                    "Tente novamente"
                ]
            )
        else:
            return ValidationResult(
                status=ValidationStatus.PARTIAL,
                confidence=confidence,
                message="Página pode não ter carregado completamente",
                details=analysis,
                suggestions=["Aguarde mais tempo para carregamento"]
            )
    
    def _interpret_form_result(self, analysis: Dict) -> ValidationResult:
        """Interpreta resultado de validação de formulário"""
        
        fields_filled = analysis.get("fields_filled", [])
        fields_empty = analysis.get("fields_empty", [])
        validation_errors = analysis.get("validation_errors", [])
        confidence = analysis.get("confidence", 0.5)
        
        if fields_filled and not validation_errors:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                confidence=confidence,
                message="Formulário preenchido com sucesso",
                details={
                    "fields_filled": fields_filled,
                    "submit_ready": analysis.get("submit_button_enabled", False)
                },
                suggestions=[]
            )
        elif validation_errors:
            return ValidationResult(
                status=ValidationStatus.PARTIAL,
                confidence=confidence,
                message="Formulário com erros de validação",
                details={
                    "errors": validation_errors,
                    "fields_empty": fields_empty
                },
                suggestions=["Corrija os campos com erro", "Preencha os campos obrigatórios"]
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=confidence,
                message="Não foi possível confirmar preenchimento",
                details=analysis,
                suggestions=["Verifique manualmente o formulário"]
            )
    
    def _interpret_click_result(self, analysis: Dict) -> ValidationResult:
        """Interpreta resultado de validação de clique"""
        
        action_completed = analysis.get("action_completed", False)
        visible_changes = analysis.get("visible_changes", [])
        confidence = analysis.get("confidence", 0.5)
        
        if action_completed or visible_changes:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                confidence=confidence,
                message="Clique executado com sucesso",
                details={
                    "changes": visible_changes,
                    "modal_opened": analysis.get("modal_opened", False),
                    "page_changed": analysis.get("page_changed", False)
                },
                suggestions=[]
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=confidence,
                message="Não foi possível confirmar o resultado do clique",
                details=analysis,
                suggestions=["O elemento pode não ter respondido", "Tente clicar novamente"]
            )
    
    def _interpret_general_result(self, analysis: Dict) -> ValidationResult:
        """Interpreta resultado geral"""
        
        confidence = analysis.get("confidence", 0.5)
        loading_state = analysis.get("loading_state", "unknown")
        errors = analysis.get("errors_visible", [])
        
        if loading_state == "loaded" and not errors:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                confidence=confidence,
                message="Estado da página validado",
                details=analysis,
                suggestions=[]
            )
        elif errors:
            return ValidationResult(
                status=ValidationStatus.PARTIAL,
                confidence=confidence,
                message="Erros detectados na página",
                details={"errors": errors},
                suggestions=["Verifique os erros indicados"]
            )
        else:
            return ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=confidence,
                message="Estado incerto",
                details=analysis,
                suggestions=["Verifique manualmente"]
            )
    
    def _interpret_raw_analysis(self, action_type: str, raw_text: str) -> ValidationResult:
        """Interpreta análise quando não foi possível extrair JSON"""
        
        raw_lower = raw_text.lower()
        patterns = self.SUCCESS_PATTERNS.get(action_type, self.SUCCESS_PATTERNS.get("navigate"))
        
        # Contar indicadores positivos e negativos
        positive_count = sum(1 for p in patterns["positive"] if p in raw_lower)
        negative_count = sum(1 for n in patterns["negative"] if n in raw_lower)
        
        if positive_count > negative_count:
            status = ValidationStatus.SUCCESS
            confidence = min(0.7, 0.5 + (positive_count * 0.1))
            message = "Análise indica sucesso"
        elif negative_count > positive_count:
            status = ValidationStatus.FAILED
            confidence = min(0.7, 0.5 + (negative_count * 0.1))
            message = "Análise indica falha"
        else:
            status = ValidationStatus.UNCERTAIN
            confidence = 0.4
            message = "Análise inconclusiva"
        
        return ValidationResult(
            status=status,
            confidence=confidence,
            message=message,
            details={"raw_analysis": raw_text[:500]},
            suggestions=["Considere verificação manual para maior precisão"]
        )


# Teste standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    validator = VisualFeedbackValidator()
    
    # Teste com análise simulada
    mock_analysis = {
        "logged_in": True,
        "indicators": ["Caixa de entrada visível", "Nome do usuário no canto"],
        "errors_visible": [],
        "current_page": "Inbox - Outlook",
        "confidence": 0.85
    }
    
    result = validator._interpret_login_result(mock_analysis)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
