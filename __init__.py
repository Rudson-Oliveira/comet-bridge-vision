"""
COMET Bridge Vision
===================
Sistema de visão computacional para captura e análise de tela com IA.

Módulos:
- screen_capture: Captura de tela (múltiplos monitores)
- vision_ai: Integração com IAs (Ollama, Claude, GPT-4, Gemini)
- vision_server: API REST
- obsidian_integration: Comandos e integração com Obsidian

Autor: Manus AI
Data: 24/12/2024
Versão: 1.0
"""

__version__ = "1.0.0"
__author__ = "Manus AI"

from .screen_capture import ScreenCapture, get_monitors_info
from .vision_ai import VisionAI
from .obsidian_integration import ObsidianVisionCommands, process_vision_command
