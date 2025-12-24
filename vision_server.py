"""
COMET Bridge Vision - Servidor API REST
========================================
API REST para captura de tela e análise por IA, integrado ao Hub Central.

Autor: Manus AI
Data: 24/12/2024
Versão: 1.0

Endpoints:
- GET  /health              - Status do servidor
- GET  /monitors            - Lista monitores disponíveis
- POST /capture             - Captura tela (sob demanda)
- POST /analyze             - Analisa imagem com IA
- POST /capture-and-analyze - Captura e analisa em uma operação
- POST /ocr                 - Extrai texto de imagem
- GET  /providers           - Lista provedores de IA disponíveis
- GET  /history             - Histórico de capturas/análises
- POST /trigger             - Dispara gatilho no Hub Central
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from flask import Flask, request, jsonify
from flask_cors import CORS

# Importar módulos locais
from screen_capture import ScreenCapture, get_monitors_info
from vision_ai import VisionAI

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VisionServer")

# Criar aplicação Flask
app = Flask(__name__)
CORS(app)

# Configurações
CONFIG_FILE = Path(__file__).parent / "vision_config.json"
CAPTURES_DIR = Path(__file__).parent / "captures"
HISTORY_FILE = Path(__file__).parent / "vision_history.json"

# Criar diretórios
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

# Instâncias globais
screen_capture = None
vision_ai = None
history = []


def load_config() -> Dict:
    """Carrega configurações do arquivo."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "ollama_host": "http://localhost:11434",
        "ollama_model": "llava",
        "priority": ["ollama", "gemini", "claude", "openai"],
        "require_confirmation": True,
        "hub_central_url": "http://localhost:5002",
        "obsidian_api_url": "http://localhost:27124",
        "auto_save_to_obsidian": True,
        "max_history": 100
    }


def save_config(config: Dict):
    """Salva configurações no arquivo."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_history() -> List[Dict]:
    """Carrega histórico de operações."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: List[Dict]):
    """Salva histórico de operações."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-100:], f, indent=2, ensure_ascii=False)  # Manter últimos 100


def add_to_history(entry: Dict):
    """Adiciona entrada ao histórico."""
    global history
    entry["id"] = len(history) + 1
    entry["timestamp"] = datetime.now().isoformat()
    history.append(entry)
    save_history(history)


def init_services():
    """Inicializa serviços."""
    global screen_capture, vision_ai, history
    
    config = load_config()
    history = load_history()
    
    # Inicializar captura de tela
    screen_capture = ScreenCapture(output_dir=str(CAPTURES_DIR))
    
    # Inicializar Vision AI
    vision_ai = VisionAI(config)
    
    logger.info("[INIT] Serviços inicializados")
    logger.info(f"[INIT] Provedores disponíveis: {vision_ai.get_available_providers()}")


# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """Status do servidor."""
    config = load_config()
    return jsonify({
        "status": "ok",
        "service": "COMET Bridge Vision",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "providers": vision_ai.get_available_providers() if vision_ai else [],
        "captures_count": len(list(CAPTURES_DIR.glob("*"))),
        "history_count": len(history)
    })


@app.route("/monitors", methods=["GET"])
def list_monitors():
    """Lista monitores disponíveis."""
    try:
        monitors = screen_capture.get_monitors() if screen_capture else []
        return jsonify({
            "success": True,
            "monitors": monitors,
            "count": len(monitors)
        })
    except Exception as e:
        logger.error(f"[MONITORS] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/capture", methods=["POST"])
def capture():
    """
    Captura tela sob demanda.
    
    Body JSON:
    {
        "mode": "full" | "monitor" | "region" | "window",
        "monitor_id": 1,  // para mode="monitor"
        "region": {"left": 0, "top": 0, "width": 800, "height": 600},  // para mode="region"
        "format": "PNG" | "JPEG",
        "include_base64": true
    }
    """
    try:
        data = request.get_json() or {}
        
        mode = data.get("mode", "full")
        monitor_id = data.get("monitor_id", 1)
        region = data.get("region")
        format = data.get("format", "PNG")
        include_base64 = data.get("include_base64", True)
        
        # Realizar captura
        result = screen_capture.capture_and_save(
            mode=mode,
            monitor_id=monitor_id,
            region=region,
            format=format
        )
        
        # Remover base64 se não solicitado
        if not include_base64:
            result.pop("base64", None)
            result.pop("base64_length", None)
        
        # Adicionar ao histórico
        add_to_history({
            "type": "capture",
            "mode": mode,
            "filepath": result.get("filepath"),
            "size": result.get("size")
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[CAPTURE] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analisa imagem com IA.
    
    Body JSON:
    {
        "image_base64": "...",  // ou
        "image_path": "/path/to/image.png",
        "prompt": "Descreva esta imagem",
        "provider": "ollama" | "claude" | "openai" | "gemini",  // opcional
        "allow_cloud": true | false  // opcional
    }
    """
    try:
        data = request.get_json() or {}
        
        # Obter imagem
        image_base64 = data.get("image_base64")
        image_path = data.get("image_path")
        
        if not image_base64 and image_path:
            # Carregar imagem do arquivo
            from PIL import Image
            import base64
            from io import BytesIO
            
            img = Image.open(image_path)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        if not image_base64:
            return jsonify({"success": False, "error": "Imagem não fornecida"}), 400
        
        prompt = data.get("prompt", "Descreva esta imagem em detalhes.")
        provider = data.get("provider")
        allow_cloud = data.get("allow_cloud")
        
        # Analisar
        result = vision_ai.analyze(
            image_base64=image_base64,
            prompt=prompt,
            provider=provider,
            allow_cloud=allow_cloud
        )
        
        # Adicionar ao histórico
        add_to_history({
            "type": "analyze",
            "prompt": prompt[:100],
            "provider": result.get("provider"),
            "success": result.get("success")
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[ANALYZE] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/capture-and-analyze", methods=["POST"])
def capture_and_analyze():
    """
    Captura tela e analisa em uma operação.
    
    Body JSON:
    {
        "mode": "full" | "monitor" | "region" | "window",
        "prompt": "O que está acontecendo nesta tela?",
        "provider": "ollama",  // opcional
        "allow_cloud": false,  // opcional
        "save_to_obsidian": true  // opcional
    }
    """
    try:
        data = request.get_json() or {}
        config = load_config()
        
        mode = data.get("mode", "full")
        prompt = data.get("prompt", "Analise esta captura de tela e descreva o que você vê.")
        provider = data.get("provider")
        allow_cloud = data.get("allow_cloud")
        save_to_obsidian = data.get("save_to_obsidian", config.get("auto_save_to_obsidian", True))
        
        # 1. Capturar tela
        capture_result = screen_capture.capture_and_save(mode=mode)
        
        if not capture_result.get("success"):
            return jsonify(capture_result), 500
        
        # 2. Analisar com IA
        analysis_result = vision_ai.analyze(
            image_base64=capture_result["base64"],
            prompt=prompt,
            provider=provider,
            allow_cloud=allow_cloud
        )
        
        # 3. Combinar resultados
        result = {
            "success": analysis_result.get("success", False),
            "capture": {
                "filepath": capture_result.get("filepath"),
                "size": capture_result.get("size"),
                "timestamp": capture_result.get("timestamp")
            },
            "analysis": {
                "provider": analysis_result.get("provider"),
                "model": analysis_result.get("model"),
                "response": analysis_result.get("analysis"),
                "local": analysis_result.get("local"),
                "cost": analysis_result.get("cost", 0)
            },
            "prompt": prompt
        }
        
        # 4. Salvar no Obsidian (se configurado)
        if save_to_obsidian and analysis_result.get("success"):
            obsidian_result = save_analysis_to_obsidian(
                capture_path=capture_result.get("filepath"),
                analysis=analysis_result.get("analysis"),
                prompt=prompt,
                provider=analysis_result.get("provider")
            )
            result["obsidian"] = obsidian_result
        
        # 5. Adicionar ao histórico
        add_to_history({
            "type": "capture_and_analyze",
            "mode": mode,
            "prompt": prompt[:100],
            "provider": analysis_result.get("provider"),
            "success": analysis_result.get("success"),
            "filepath": capture_result.get("filepath")
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[CAPTURE_AND_ANALYZE] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/ocr", methods=["POST"])
def ocr():
    """
    Extrai texto de imagem (OCR).
    
    Body JSON:
    {
        "image_base64": "...",  // ou
        "image_path": "/path/to/image.png",
        "provider": "ollama"  // opcional
    }
    """
    try:
        data = request.get_json() or {}
        
        # Obter imagem
        image_base64 = data.get("image_base64")
        image_path = data.get("image_path")
        
        if not image_base64 and image_path:
            from PIL import Image
            import base64
            from io import BytesIO
            
            img = Image.open(image_path)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        if not image_base64:
            return jsonify({"success": False, "error": "Imagem não fornecida"}), 400
        
        # Extrair texto
        result = vision_ai.analyze_with_ocr(
            image_base64=image_base64,
            provider=data.get("provider"),
            allow_cloud=data.get("allow_cloud")
        )
        
        # Adicionar ao histórico
        add_to_history({
            "type": "ocr",
            "provider": result.get("provider"),
            "success": result.get("success")
        })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[OCR] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/providers", methods=["GET"])
def list_providers():
    """Lista provedores de IA disponíveis."""
    try:
        available = vision_ai.get_available_providers() if vision_ai else []
        all_providers = ["ollama", "gemini", "claude", "openai"]
        
        providers = []
        for name in all_providers:
            providers.append({
                "name": name,
                "available": name in available,
                "local": name == "ollama",
                "description": {
                    "ollama": "IA local com LLaVA (gratuito, privado)",
                    "gemini": "Google Gemini (cloud, gratuito limitado)",
                    "claude": "Anthropic Claude (cloud, pago)",
                    "openai": "OpenAI GPT-4 Vision (cloud, pago)"
                }.get(name, "")
            })
        
        return jsonify({
            "success": True,
            "providers": providers,
            "available": available,
            "priority": load_config().get("priority", [])
        })
        
    except Exception as e:
        logger.error(f"[PROVIDERS] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/history", methods=["GET"])
def get_history():
    """Retorna histórico de operações."""
    try:
        limit = request.args.get("limit", 50, type=int)
        type_filter = request.args.get("type")
        
        filtered = history
        if type_filter:
            filtered = [h for h in history if h.get("type") == type_filter]
        
        return jsonify({
            "success": True,
            "history": filtered[-limit:],
            "total": len(filtered)
        })
        
    except Exception as e:
        logger.error(f"[HISTORY] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/config", methods=["GET", "POST"])
def manage_config():
    """Gerencia configurações."""
    try:
        if request.method == "GET":
            config = load_config()
            # Ocultar API keys
            safe_config = {k: v for k, v in config.items() if "key" not in k.lower()}
            return jsonify({"success": True, "config": safe_config})
        
        elif request.method == "POST":
            data = request.get_json() or {}
            config = load_config()
            config.update(data)
            save_config(config)
            
            # Reinicializar serviços
            init_services()
            
            return jsonify({"success": True, "message": "Configurações atualizadas"})
            
    except Exception as e:
        logger.error(f"[CONFIG] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/trigger", methods=["POST"])
def trigger_hub():
    """
    Dispara gatilho no Hub Central.
    
    Body JSON:
    {
        "trigger_id": "trg_xxx",
        "data": {...}
    }
    """
    try:
        data = request.get_json() or {}
        config = load_config()
        hub_url = config.get("hub_central_url", "http://localhost:5002")
        
        trigger_id = data.get("trigger_id")
        trigger_data = data.get("data", {})
        
        if not trigger_id:
            return jsonify({"success": False, "error": "trigger_id não fornecido"}), 400
        
        # Chamar Hub Central
        import requests as req
        response = req.post(
            f"{hub_url}/triggers/{trigger_id}/fire",
            json=trigger_data,
            timeout=30
        )
        
        return jsonify({
            "success": response.status_code == 200,
            "hub_response": response.json() if response.status_code == 200 else None,
            "status_code": response.status_code
        })
        
    except Exception as e:
        logger.error(f"[TRIGGER] Erro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def save_analysis_to_obsidian(capture_path: str, analysis: str, 
                               prompt: str, provider: str) -> Dict:
    """Salva análise no Obsidian como nota."""
    try:
        config = load_config()
        obsidian_url = config.get("obsidian_api_url", "http://localhost:27124")
        
        # Criar conteúdo da nota
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = Path(capture_path).name if capture_path else "capture"
        
        content = f"""# Análise de Captura - {timestamp}

## Informações
- **Data/Hora**: {timestamp}
- **Provedor**: {provider}
- **Arquivo**: {filename}

## Prompt
{prompt}

## Análise
{analysis}

---
*Gerado automaticamente pelo COMET Bridge Vision*
"""
        
        # Enviar para Obsidian
        import requests as req
        
        note_path = f"COMET Vision/Analise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        response = req.put(
            f"{obsidian_url}/vault/{note_path}",
            headers={
                "Content-Type": "text/markdown",
                "Authorization": f"Bearer {os.getenv('OBSIDIAN_API_KEY', '')}"
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
        logger.error(f"[OBSIDIAN] Erro ao salvar nota: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def main():
    """Função principal."""
    # Inicializar serviços
    init_services()
    
    # Configurações do servidor
    host = os.getenv("VISION_HOST", "0.0.0.0")
    port = int(os.getenv("VISION_PORT", "5003"))
    
    logger.info("=" * 60)
    logger.info("   COMET BRIDGE VISION SERVER v1.0")
    logger.info("=" * 60)
    logger.info(f"[SERVER] Iniciando em http://{host}:{port}")
    logger.info(f"[SERVER] Provedores: {vision_ai.get_available_providers()}")
    logger.info("=" * 60)
    
    # Iniciar servidor
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
