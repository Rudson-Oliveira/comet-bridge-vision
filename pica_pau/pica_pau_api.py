"""
PicaPau API - Endpoints para integração com vision_server.py
Parte do Agente PicaPau - COMET Bridge Vision

Este módulo fornece os endpoints Flask para o Agente PicaPau,
integrando com o servidor de visão existente.
"""

import asyncio
import logging
import json
from typing import Dict, Optional
from flask import Blueprint, request, jsonify
from functools import wraps

from .nlu_command_parser import NLUCommandParser
from .pica_pau_agent import PicaPauAgent
from .visual_feedback_validator import VisualFeedbackValidator
from .credentials_manager import CredentialsManager

logger = logging.getLogger("PicaPauAPI")

# Blueprint para integração com Flask
pica_pau_bp = Blueprint("pica_pau", __name__, url_prefix="/pica-pau")

# Instâncias globais (inicializadas no register)
_parser: Optional[NLUCommandParser] = None
_agent: Optional[PicaPauAgent] = None
_validator: Optional[VisualFeedbackValidator] = None
_credentials: Optional[CredentialsManager] = None
_vision_analyzer = None


def init_pica_pau(vision_analyzer=None, config: Dict = None):
    """
    Inicializa os componentes do PicaPau.
    
    Args:
        vision_analyzer: Instância do VisionAI para validação visual
        config: Configurações opcionais
    """
    global _parser, _agent, _validator, _credentials, _vision_analyzer
    
    config = config or {}
    
    _parser = NLUCommandParser()
    _agent = PicaPauAgent(
        headless=config.get("headless", False),
        slow_mo=config.get("slow_mo", 100)
    )
    _validator = VisualFeedbackValidator(vision_analyzer)
    _credentials = CredentialsManager()
    _vision_analyzer = vision_analyzer
    
    logger.info("[PICA_PAU_API] Componentes inicializados")


def async_route(f):
    """Decorator para rotas assíncronas no Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(f(*args, **kwargs))
    return wrapper


@pica_pau_bp.route("/execute-command", methods=["POST"])
@async_route
async def execute_command():
    """
    Executa um comando em linguagem natural.
    
    Request Body:
    {
        "command": "PicaPau entre no Hotmail com rud.pa@hotmail.com senha Rudson2323##",
        "use_vision_feedback": true,
        "headless": false,
        "save_credentials": true
    }
    
    Response:
    {
        "success": true,
        "command": "...",
        "parsed": {...},
        "execution": {...},
        "validation": {...},
        "screenshot": "base64...",
        "actions_log": [...]
    }
    """
    global _parser, _agent, _validator, _credentials
    
    try:
        data = request.get_json()
        
        if not data or "command" not in data:
            return jsonify({
                "success": False,
                "error": "Campo 'command' é obrigatório"
            }), 400
        
        command = data["command"]
        use_vision_feedback = data.get("use_vision_feedback", True)
        save_credentials = data.get("save_credentials", False)
        
        logger.info(f"[PICA_PAU_API] Comando recebido: {command}")
        
        # 1. Parse do comando
        parsed = _parser.parse(command)
        
        if not parsed.is_valid:
            return jsonify({
                "success": False,
                "error": "Comando não reconhecido",
                "parsed": parsed.to_dict()
            }), 400
        
        # 2. Obter credenciais se necessário
        credentials = {}
        if parsed.entities.get("has_password"):
            credentials = _credentials.get_credentials_for_command(
                entities=parsed.entities,
                credential_keys=["password"]
            )
            
            # Salvar credenciais se solicitado
            if save_credentials and parsed.entities.get("password"):
                service = parsed.entities.get("site_name", "unknown")
                _credentials.store_credential(
                    service=service,
                    username=parsed.entities.get("email", ""),
                    password=parsed.entities.get("password", ""),
                    metadata={"url": parsed.entities.get("site_url", "")}
                )
        
        # 3. Executar comando
        result = await _agent.execute_command(
            parsed_command=parsed,
            credentials=credentials,
            take_screenshots=True
        )
        
        # 4. Validar resultado com visão (se habilitado)
        validation = None
        if use_vision_feedback and result.final_screenshot and _vision_analyzer:
            # Determinar tipo de ação principal para validação
            main_action = parsed.actions[0].action_type.value if parsed.actions else "general"
            
            validation_result = await _validator.validate_action(
                action_type=main_action,
                screenshot_b64=result.final_screenshot,
                expected_result=parsed.entities,
                context={"command": command}
            )
            validation = validation_result.to_dict()
        
        # 5. Montar resposta
        response = {
            "success": result.success,
            "command": command,
            "parsed": parsed.to_dict(),
            "execution": {
                "actions_executed": result.actions_executed,
                "actions_failed": result.actions_failed,
                "total_duration_ms": result.total_duration_ms
            },
            "validation": validation,
            "screenshot": result.final_screenshot,
            "actions_log": [a.to_dict() for a in result.actions_log]
        }
        
        if result.error:
            response["error"] = result.error
        
        logger.info(f"[PICA_PAU_API] Comando executado | Sucesso: {result.success}")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"[PICA_PAU_API] Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/parse-command", methods=["POST"])
def parse_command():
    """
    Apenas faz o parse de um comando sem executar.
    Útil para preview e validação.
    """
    try:
        data = request.get_json()
        
        if not data or "command" not in data:
            return jsonify({
                "success": False,
                "error": "Campo 'command' é obrigatório"
            }), 400
        
        parsed = _parser.parse(data["command"])
        
        return jsonify({
            "success": True,
            "parsed": parsed.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/credentials", methods=["GET"])
def list_credentials():
    """Lista serviços com credenciais armazenadas (sem expor senhas)"""
    try:
        services = _credentials.list_services()
        
        return jsonify({
            "success": True,
            "services": services,
            "count": len(services)
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/credentials", methods=["POST"])
def store_credential():
    """Armazena uma nova credencial"""
    try:
        data = request.get_json()
        
        required = ["service", "username", "password"]
        for field in required:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Campo '{field}' é obrigatório"
                }), 400
        
        success = _credentials.store_credential(
            service=data["service"],
            username=data["username"],
            password=data["password"],
            metadata=data.get("metadata", {})
        )
        
        return jsonify({
            "success": success,
            "message": "Credencial armazenada" if success else "Falha ao armazenar"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/credentials/<service>", methods=["DELETE"])
def delete_credential(service: str):
    """Remove uma credencial"""
    try:
        success = _credentials.delete_credential(service)
        
        return jsonify({
            "success": success,
            "message": "Credencial removida" if success else "Credencial não encontrada"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/browser/start", methods=["POST"])
@async_route
async def start_browser():
    """Inicia o navegador do PicaPau"""
    try:
        await _agent.start()
        
        return jsonify({
            "success": True,
            "message": "Navegador iniciado"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/browser/stop", methods=["POST"])
@async_route
async def stop_browser():
    """Para o navegador do PicaPau"""
    try:
        await _agent.stop()
        
        return jsonify({
            "success": True,
            "message": "Navegador parado"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/browser/screenshot", methods=["GET"])
@async_route
async def get_screenshot():
    """Captura screenshot do navegador atual"""
    try:
        if not _agent._page:
            return jsonify({
                "success": False,
                "error": "Navegador não iniciado"
            }), 400
        
        screenshot = await _agent._take_screenshot("manual")
        
        return jsonify({
            "success": True,
            "screenshot": screenshot
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/audit-log", methods=["GET"])
def get_audit_log():
    """Exporta log de auditoria para compliance LGPD"""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        entries = _credentials.export_audit_log(start_date, end_date)
        
        return jsonify({
            "success": True,
            "entries": entries,
            "count": len(entries)
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@pica_pau_bp.route("/health", methods=["GET"])
def health_check():
    """Verifica saúde do serviço PicaPau"""
    return jsonify({
        "status": "ok",
        "service": "PicaPau Agent",
        "version": "1.0.0",
        "components": {
            "parser": _parser is not None,
            "agent": _agent is not None,
            "validator": _validator is not None,
            "credentials": _credentials is not None,
            "vision": _vision_analyzer is not None
        }
    })


def register_pica_pau(app, vision_analyzer=None, config: Dict = None):
    """
    Registra o blueprint do PicaPau no app Flask.
    
    Args:
        app: Instância do Flask app
        vision_analyzer: Instância do VisionAI
        config: Configurações opcionais
    """
    init_pica_pau(vision_analyzer, config)
    app.register_blueprint(pica_pau_bp)
    
    logger.info("[PICA_PAU_API] Blueprint registrado")
