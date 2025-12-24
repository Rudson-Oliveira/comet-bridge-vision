"""
Agente PicaPau - Executor de comandos visuais
COMET Bridge Vision Extension

Módulos:
- nlu_command_parser: Parse de linguagem natural para JSON
- pica_pau_agent: Executor Playwright
- visual_feedback_validator: Validação via COMET Vision
- credentials_manager: Gerenciamento seguro de credenciais
"""

from .nlu_command_parser import NLUCommandParser, ParsedCommand, ParsedAction, ActionType
from .pica_pau_agent import PicaPauAgent, ExecutionResult, ActionResult
from .visual_feedback_validator import VisualFeedbackValidator, ValidationResult, ValidationStatus
from .credentials_manager import CredentialsManager

__version__ = "1.0.0"
__all__ = [
    "NLUCommandParser",
    "ParsedCommand", 
    "ParsedAction",
    "ActionType",
    "PicaPauAgent",
    "ExecutionResult",
    "ActionResult",
    "VisualFeedbackValidator",
    "ValidationResult",
    "ValidationStatus",
    "CredentialsManager"
]
