"""
COMET Bridge Vision - Módulo de Captura de Tela
================================================
Captura de tela sob demanda com suporte a múltiplos monitores.

Autor: Manus AI
Data: 24/12/2024
Versão: 1.0
"""

import os
import sys
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
from io import BytesIO

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScreenCapture")

# Tentar importar bibliotecas de captura
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL não disponível. Instale com: pip install Pillow")

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    logger.warning("mss não disponível. Instale com: pip install mss")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui não disponível. Instale com: pip install pyautogui")


class ScreenCapture:
    """
    Classe para captura de tela com suporte a múltiplos monitores.
    
    Funcionalidades:
    - Captura de tela inteira (todos os monitores)
    - Captura de monitor específico
    - Captura de região específica
    - Captura de janela ativa
    - Exportação em múltiplos formatos (PNG, JPEG, Base64)
    """
    
    def __init__(self, output_dir: str = None):
        """
        Inicializa o módulo de captura.
        
        Args:
            output_dir: Diretório para salvar capturas (padrão: ./captures)
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./captures")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Verificar bibliotecas disponíveis
        self._check_dependencies()
        
        logger.info(f"[SCREEN_CAPTURE] Inicializado. Output: {self.output_dir}")
    
    def _check_dependencies(self):
        """Verifica dependências disponíveis."""
        if not PIL_AVAILABLE:
            raise ImportError("Pillow é necessário. Instale com: pip install Pillow")
        
        if not MSS_AVAILABLE and not PYAUTOGUI_AVAILABLE:
            raise ImportError("mss ou pyautogui é necessário. Instale com: pip install mss pyautogui")
        
        self.capture_method = "mss" if MSS_AVAILABLE else "pyautogui"
        logger.info(f"[SCREEN_CAPTURE] Método de captura: {self.capture_method}")
    
    def get_monitors(self) -> List[Dict]:
        """
        Retorna informações sobre todos os monitores disponíveis.
        
        Returns:
            Lista de dicionários com informações dos monitores
        """
        monitors = []
        
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                for i, monitor in enumerate(sct.monitors):
                    monitors.append({
                        "id": i,
                        "left": monitor["left"],
                        "top": monitor["top"],
                        "width": monitor["width"],
                        "height": monitor["height"],
                        "is_primary": i == 1,  # Monitor 0 é todos, 1 é o primário
                        "is_all": i == 0
                    })
        elif PYAUTOGUI_AVAILABLE:
            # pyautogui só captura a tela principal
            size = pyautogui.size()
            monitors.append({
                "id": 0,
                "left": 0,
                "top": 0,
                "width": size.width,
                "height": size.height,
                "is_primary": True,
                "is_all": True
            })
        
        logger.info(f"[SCREEN_CAPTURE] Monitores detectados: {len(monitors)}")
        return monitors
    
    def capture_full_screen(self) -> Image.Image:
        """
        Captura a tela inteira (todos os monitores).
        
        Returns:
            Imagem PIL da captura
        """
        logger.info("[SCREEN_CAPTURE] Capturando tela inteira...")
        
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                # Monitor 0 = todos os monitores combinados
                screenshot = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        else:
            img = pyautogui.screenshot()
        
        logger.info(f"[SCREEN_CAPTURE] Captura completa: {img.size}")
        return img
    
    def capture_monitor(self, monitor_id: int = 1) -> Image.Image:
        """
        Captura um monitor específico.
        
        Args:
            monitor_id: ID do monitor (1 = primário, 2+ = secundários)
        
        Returns:
            Imagem PIL da captura
        """
        logger.info(f"[SCREEN_CAPTURE] Capturando monitor {monitor_id}...")
        
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                if monitor_id >= len(sct.monitors):
                    logger.warning(f"Monitor {monitor_id} não existe. Usando primário.")
                    monitor_id = 1
                
                screenshot = sct.grab(sct.monitors[monitor_id])
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        else:
            img = pyautogui.screenshot()
        
        logger.info(f"[SCREEN_CAPTURE] Captura monitor {monitor_id}: {img.size}")
        return img
    
    def capture_region(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        Captura uma região específica da tela.
        
        Args:
            left: Posição X inicial
            top: Posição Y inicial
            width: Largura da região
            height: Altura da região
        
        Returns:
            Imagem PIL da captura
        """
        logger.info(f"[SCREEN_CAPTURE] Capturando região: ({left}, {top}, {width}, {height})")
        
        region = {"left": left, "top": top, "width": width, "height": height}
        
        if MSS_AVAILABLE:
            with mss.mss() as sct:
                screenshot = sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        else:
            img = pyautogui.screenshot(region=(left, top, width, height))
        
        logger.info(f"[SCREEN_CAPTURE] Captura região: {img.size}")
        return img
    
    def capture_active_window(self) -> Optional[Image.Image]:
        """
        Captura a janela ativa (requer pyautogui no Windows).
        
        Returns:
            Imagem PIL da captura ou None se não suportado
        """
        logger.info("[SCREEN_CAPTURE] Capturando janela ativa...")
        
        try:
            if PYAUTOGUI_AVAILABLE:
                # Tentar obter a janela ativa
                try:
                    import pygetwindow as gw
                    active = gw.getActiveWindow()
                    if active:
                        region = (active.left, active.top, active.width, active.height)
                        img = pyautogui.screenshot(region=region)
                        logger.info(f"[SCREEN_CAPTURE] Janela ativa capturada: {active.title}")
                        return img
                except ImportError:
                    logger.warning("pygetwindow não disponível para captura de janela ativa")
            
            # Fallback: captura tela inteira
            logger.info("[SCREEN_CAPTURE] Fallback para tela inteira")
            return self.capture_full_screen()
            
        except Exception as e:
            logger.error(f"[SCREEN_CAPTURE] Erro ao capturar janela ativa: {e}")
            return self.capture_full_screen()
    
    def save_capture(self, img: Image.Image, filename: str = None, 
                     format: str = "PNG", quality: int = 95) -> str:
        """
        Salva a captura em arquivo.
        
        Args:
            img: Imagem PIL para salvar
            filename: Nome do arquivo (auto-gerado se não fornecido)
            format: Formato da imagem (PNG, JPEG, WEBP)
            quality: Qualidade para formatos com compressão
        
        Returns:
            Caminho completo do arquivo salvo
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.{format.lower()}"
        
        filepath = self.output_dir / filename
        
        save_kwargs = {}
        if format.upper() in ["JPEG", "JPG", "WEBP"]:
            save_kwargs["quality"] = quality
        
        img.save(filepath, format=format.upper(), **save_kwargs)
        logger.info(f"[SCREEN_CAPTURE] Salvo: {filepath}")
        
        return str(filepath)
    
    def to_base64(self, img: Image.Image, format: str = "PNG") -> str:
        """
        Converte imagem para Base64.
        
        Args:
            img: Imagem PIL
            format: Formato para codificação
        
        Returns:
            String Base64 da imagem
        """
        buffer = BytesIO()
        img.save(buffer, format=format.upper())
        buffer.seek(0)
        
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        logger.info(f"[SCREEN_CAPTURE] Convertido para Base64: {len(base64_str)} chars")
        
        return base64_str
    
    def capture_and_save(self, mode: str = "full", monitor_id: int = 1,
                         region: Dict = None, format: str = "PNG") -> Dict:
        """
        Captura e salva em uma única operação.
        
        Args:
            mode: Modo de captura ("full", "monitor", "region", "window")
            monitor_id: ID do monitor (para mode="monitor")
            region: Dicionário com left, top, width, height (para mode="region")
            format: Formato de saída
        
        Returns:
            Dicionário com informações da captura
        """
        timestamp = datetime.now().isoformat()
        
        # Realizar captura baseado no modo
        if mode == "full":
            img = self.capture_full_screen()
        elif mode == "monitor":
            img = self.capture_monitor(monitor_id)
        elif mode == "region" and region:
            img = self.capture_region(**region)
        elif mode == "window":
            img = self.capture_active_window()
        else:
            img = self.capture_full_screen()
        
        # Salvar arquivo
        filepath = self.save_capture(img, format=format)
        
        # Gerar Base64
        base64_str = self.to_base64(img, format=format)
        
        result = {
            "success": True,
            "timestamp": timestamp,
            "mode": mode,
            "filepath": filepath,
            "size": {
                "width": img.size[0],
                "height": img.size[1]
            },
            "format": format,
            "base64": base64_str,
            "base64_length": len(base64_str)
        }
        
        logger.info(f"[SCREEN_CAPTURE] Captura completa: {result['filepath']}")
        return result


# Funções de conveniência
def capture_screen(mode: str = "full", **kwargs) -> Dict:
    """
    Função de conveniência para captura rápida.
    
    Args:
        mode: Modo de captura
        **kwargs: Argumentos adicionais para capture_and_save
    
    Returns:
        Resultado da captura
    """
    capture = ScreenCapture()
    return capture.capture_and_save(mode=mode, **kwargs)


def get_monitors_info() -> List[Dict]:
    """
    Retorna informações sobre monitores disponíveis.
    
    Returns:
        Lista de monitores
    """
    capture = ScreenCapture()
    return capture.get_monitors()


# Teste do módulo
if __name__ == "__main__":
    print("=== COMET Bridge Vision - Screen Capture Test ===\n")
    
    # Criar instância
    capture = ScreenCapture(output_dir="./test_captures")
    
    # Listar monitores
    print("Monitores disponíveis:")
    monitors = capture.get_monitors()
    for m in monitors:
        print(f"  Monitor {m['id']}: {m['width']}x{m['height']} @ ({m['left']}, {m['top']})")
    
    # Capturar tela inteira
    print("\nCapturando tela inteira...")
    result = capture.capture_and_save(mode="full")
    print(f"  Arquivo: {result['filepath']}")
    print(f"  Tamanho: {result['size']['width']}x{result['size']['height']}")
    print(f"  Base64: {result['base64_length']} caracteres")
    
    print("\n=== Teste concluído! ===")
