"""
PicaPau Agent - Executor de comandos visuais usando Playwright
Parte do Agente PicaPau - COMET Bridge Vision

Este módulo executa as ações parseadas pelo NLU Command Parser,
controlando o navegador via Playwright com feedback visual.
"""

import asyncio
import logging
import json
import os
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("[PICA_PAU] Playwright não instalado. Execute: pip install playwright && playwright install chromium")

from .nlu_command_parser import ParsedCommand, ParsedAction, ActionType

logger = logging.getLogger("PicaPauAgent")


@dataclass
class ActionResult:
    """Resultado de uma ação executada"""
    action_type: str
    success: bool
    message: str
    screenshot: Optional[str] = None
    duration_ms: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ExecutionResult:
    """Resultado completo da execução de um comando"""
    command: str
    success: bool
    actions_executed: int
    actions_failed: int
    actions_log: List[ActionResult]
    final_screenshot: Optional[str] = None
    total_duration_ms: int = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "command": self.command,
            "success": self.success,
            "actions_executed": self.actions_executed,
            "actions_failed": self.actions_failed,
            "actions_log": [a.to_dict() for a in self.actions_log],
            "final_screenshot": self.final_screenshot,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error
        }


class PicaPauAgent:
    """
    Agente executor de comandos visuais usando Playwright.
    
    Características:
    - Perfil de navegador persistente (mantém sessões)
    - Suporte a múltiplas abas
    - Screenshots para validação visual
    - Logs de auditoria detalhados
    - Tratamento robusto de erros
    """
    
    def __init__(self, 
                 profile_dir: str = None,
                 headless: bool = False,
                 slow_mo: int = 100,
                 timeout: int = 30000):
        """
        Inicializa o agente PicaPau.
        
        Args:
            profile_dir: Diretório para perfil persistente do navegador
            headless: Se True, executa sem interface gráfica
            slow_mo: Delay entre ações (ms) para visualização
            timeout: Timeout padrão para operações (ms)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright não está instalado. Execute: pip install playwright && playwright install chromium")
        
        self.profile_dir = profile_dir or os.path.join(
            os.path.dirname(__file__), 
            "browser_profiles", 
            "default"
        )
        self.headless = headless
        self.slow_mo = slow_mo
        self.timeout = timeout
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Criar diretório de perfil se não existir
        Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
        
        # Diretório para screenshots
        self.screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        Path(self.screenshots_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[PICA_PAU] Inicializado | Profile: {self.profile_dir} | Headless: {headless}")
    
    async def start(self) -> None:
        """Inicia o navegador e contexto"""
        if self._browser is not None:
            return
        
        logger.info("[PICA_PAU] Iniciando navegador...")
        
        self._playwright = await async_playwright().start()
        
        # Usar contexto persistente para manter sessões
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ]
        )
        
        # Usar página existente ou criar nova
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()
        
        # Configurar timeout padrão
        self._page.set_default_timeout(self.timeout)
        
        logger.info("[PICA_PAU] Navegador iniciado com sucesso")
    
    async def stop(self) -> None:
        """Para o navegador"""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        
        logger.info("[PICA_PAU] Navegador parado")
    
    async def execute_command(self, 
                              parsed_command: ParsedCommand,
                              credentials: Dict[str, str] = None,
                              take_screenshots: bool = True) -> ExecutionResult:
        """
        Executa um comando parseado.
        
        Args:
            parsed_command: Comando parseado pelo NLU
            credentials: Dicionário com credenciais (senhas, etc.)
            take_screenshots: Se deve capturar screenshots durante execução
            
        Returns:
            ExecutionResult com detalhes da execução
        """
        start_time = datetime.now()
        actions_log = []
        actions_failed = 0
        
        logger.info(f"[PICA_PAU] Executando comando: {parsed_command.original_command}")
        logger.info(f"[PICA_PAU] Ações a executar: {len(parsed_command.actions)}")
        
        try:
            # Garantir que o navegador está iniciado
            await self.start()
            
            # Executar cada ação
            for i, action in enumerate(parsed_command.actions):
                logger.info(f"[PICA_PAU] Ação {i+1}/{len(parsed_command.actions)}: {action.action_type.value}")
                
                action_start = datetime.now()
                
                try:
                    result = await self._execute_action(action, credentials)
                    
                    # Capturar screenshot se solicitado
                    if take_screenshots and result.success:
                        screenshot = await self._take_screenshot(f"action_{i+1}")
                        result.screenshot = screenshot
                    
                    result.duration_ms = int((datetime.now() - action_start).total_seconds() * 1000)
                    actions_log.append(result)
                    
                    if not result.success:
                        actions_failed += 1
                        # Se ação não é opcional, parar execução
                        if not action.options or not action.options.get("optional"):
                            logger.warning(f"[PICA_PAU] Ação falhou e não é opcional. Parando execução.")
                            break
                
                except Exception as e:
                    logger.error(f"[PICA_PAU] Erro na ação {i+1}: {str(e)}")
                    actions_failed += 1
                    actions_log.append(ActionResult(
                        action_type=action.action_type.value,
                        success=False,
                        message=f"Erro: {str(e)}",
                        error=str(e),
                        duration_ms=int((datetime.now() - action_start).total_seconds() * 1000)
                    ))
                    
                    if not action.options or not action.options.get("optional"):
                        break
            
            # Screenshot final
            final_screenshot = await self._take_screenshot("final") if take_screenshots else None
            
            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
            
            success = actions_failed == 0
            
            return ExecutionResult(
                command=parsed_command.original_command,
                success=success,
                actions_executed=len(actions_log),
                actions_failed=actions_failed,
                actions_log=actions_log,
                final_screenshot=final_screenshot,
                total_duration_ms=total_duration
            )
        
        except Exception as e:
            logger.error(f"[PICA_PAU] Erro geral na execução: {str(e)}")
            return ExecutionResult(
                command=parsed_command.original_command,
                success=False,
                actions_executed=len(actions_log),
                actions_failed=actions_failed + 1,
                actions_log=actions_log,
                error=str(e),
                total_duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def _execute_action(self, action: ParsedAction, credentials: Dict = None) -> ActionResult:
        """Executa uma ação individual"""
        action_type = action.action_type
        
        if action_type == ActionType.NAVIGATE:
            return await self._action_navigate(action)
        elif action_type == ActionType.CLICK:
            return await self._action_click(action)
        elif action_type == ActionType.TYPE:
            return await self._action_type(action, credentials)
        elif action_type == ActionType.WAIT:
            return await self._action_wait(action)
        elif action_type == ActionType.SCREENSHOT:
            return await self._action_screenshot(action)
        elif action_type == ActionType.SCROLL:
            return await self._action_scroll(action)
        elif action_type == ActionType.SELECT:
            return await self._action_select(action)
        elif action_type == ActionType.PRESS_KEY:
            return await self._action_press_key(action)
        elif action_type == ActionType.LOGIN:
            # Login é tratado como sequência de ações pelo parser
            return ActionResult(
                action_type=action_type.value,
                success=True,
                message="Login action delegated to sub-actions"
            )
        else:
            return ActionResult(
                action_type=action_type.value,
                success=False,
                message=f"Tipo de ação não suportado: {action_type.value}"
            )
    
    async def _action_navigate(self, action: ParsedAction) -> ActionResult:
        """Executa navegação para URL"""
        url = action.target
        
        if not url:
            return ActionResult(
                action_type="navigate",
                success=False,
                message="URL não especificada"
            )
        
        # Garantir protocolo
        if not url.startswith("http"):
            url = "https://" + url
        
        try:
            # Navegar
            response = await self._page.goto(url, wait_until="domcontentloaded")
            
            # Aguardar carregamento adicional se especificado
            if action.options and action.options.get("wait_for_load"):
                await self._page.wait_for_load_state("networkidle", timeout=10000)
            
            return ActionResult(
                action_type="navigate",
                success=True,
                message=f"Navegou para {url}"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="navigate",
                success=False,
                message=f"Falha ao navegar para {url}",
                error=str(e)
            )
    
    async def _action_click(self, action: ParsedAction) -> ActionResult:
        """Executa clique em elemento"""
        selector = action.selector
        
        if not selector:
            return ActionResult(
                action_type="click",
                success=False,
                message="Seletor não especificado"
            )
        
        try:
            # Tentar múltiplos seletores separados por vírgula
            selectors = [s.strip() for s in selector.split(",")]
            
            clicked = False
            for sel in selectors:
                try:
                    element = await self._page.wait_for_selector(sel, timeout=5000, state="visible")
                    if element:
                        await element.click()
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                return ActionResult(
                    action_type="click",
                    success=False,
                    message=f"Elemento não encontrado: {action.target}"
                )
            
            # Aguardar após clique se especificado
            if action.options and action.options.get("wait_after"):
                await asyncio.sleep(action.options["wait_after"] / 1000)
            
            return ActionResult(
                action_type="click",
                success=True,
                message=f"Clicou em {action.target}"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="click",
                success=False,
                message=f"Falha ao clicar em {action.target}",
                error=str(e)
            )
    
    async def _action_type(self, action: ParsedAction, credentials: Dict = None) -> ActionResult:
        """Executa digitação em campo"""
        selector = action.selector
        value = action.value
        
        # Substituir placeholder de credencial
        if value == "{{PASSWORD}}" and credentials and "password" in credentials:
            value = credentials["password"]
        
        if not selector or not value:
            return ActionResult(
                action_type="type",
                success=False,
                message="Seletor ou valor não especificado"
            )
        
        try:
            # Tentar múltiplos seletores
            selectors = [s.strip() for s in selector.split(",")]
            
            typed = False
            for sel in selectors:
                try:
                    element = await self._page.wait_for_selector(sel, timeout=5000, state="visible")
                    if element:
                        # Limpar campo se especificado
                        if action.options and action.options.get("clear_first"):
                            await element.fill("")
                        
                        # Digitar valor
                        await element.fill(value)
                        typed = True
                        break
                except:
                    continue
            
            if not typed:
                return ActionResult(
                    action_type="type",
                    success=False,
                    message=f"Campo não encontrado: {action.target}"
                )
            
            # Mascarar senha no log
            display_value = "****" if "password" in (action.target or "").lower() else value
            
            return ActionResult(
                action_type="type",
                success=True,
                message=f"Digitou em {action.target}: {display_value}"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="type",
                success=False,
                message=f"Falha ao digitar em {action.target}",
                error=str(e)
            )
    
    async def _action_wait(self, action: ParsedAction) -> ActionResult:
        """Executa espera"""
        try:
            wait_time = int(action.value or 1000)
            await asyncio.sleep(wait_time / 1000)
            
            return ActionResult(
                action_type="wait",
                success=True,
                message=f"Aguardou {wait_time}ms"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="wait",
                success=False,
                message="Falha ao aguardar",
                error=str(e)
            )
    
    async def _action_screenshot(self, action: ParsedAction) -> ActionResult:
        """Captura screenshot"""
        try:
            screenshot = await self._take_screenshot(action.target or "screenshot")
            
            return ActionResult(
                action_type="screenshot",
                success=True,
                message="Screenshot capturado",
                screenshot=screenshot
            )
        
        except Exception as e:
            return ActionResult(
                action_type="screenshot",
                success=False,
                message="Falha ao capturar screenshot",
                error=str(e)
            )
    
    async def _action_scroll(self, action: ParsedAction) -> ActionResult:
        """Executa scroll na página"""
        try:
            direction = action.options.get("direction", "down") if action.options else "down"
            amount = int(action.value or 500)
            
            if direction == "down":
                await self._page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self._page.evaluate(f"window.scrollBy(0, -{amount})")
            
            return ActionResult(
                action_type="scroll",
                success=True,
                message=f"Scroll {direction} {amount}px"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="scroll",
                success=False,
                message="Falha ao fazer scroll",
                error=str(e)
            )
    
    async def _action_select(self, action: ParsedAction) -> ActionResult:
        """Seleciona opção em dropdown"""
        try:
            selector = action.selector
            value = action.value
            
            await self._page.select_option(selector, value)
            
            return ActionResult(
                action_type="select",
                success=True,
                message=f"Selecionou: {value}"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="select",
                success=False,
                message="Falha ao selecionar opção",
                error=str(e)
            )
    
    async def _action_press_key(self, action: ParsedAction) -> ActionResult:
        """Pressiona tecla"""
        try:
            key = action.value or "Enter"
            await self._page.keyboard.press(key)
            
            return ActionResult(
                action_type="press_key",
                success=True,
                message=f"Pressionou tecla: {key}"
            )
        
        except Exception as e:
            return ActionResult(
                action_type="press_key",
                success=False,
                message="Falha ao pressionar tecla",
                error=str(e)
            )
    
    async def _take_screenshot(self, name: str) -> str:
        """Captura screenshot e retorna como base64"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            # Capturar screenshot
            await self._page.screenshot(path=filepath, full_page=False)
            
            # Converter para base64
            with open(filepath, "rb") as f:
                screenshot_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            return screenshot_b64
        
        except Exception as e:
            logger.error(f"[PICA_PAU] Erro ao capturar screenshot: {str(e)}")
            return None
    
    async def get_page_content(self) -> str:
        """Retorna o conteúdo HTML da página atual"""
        if self._page:
            return await self._page.content()
        return ""
    
    async def get_current_url(self) -> str:
        """Retorna a URL atual"""
        if self._page:
            return self._page.url
        return ""


# Função auxiliar para execução síncrona
def run_command_sync(command: str, credentials: Dict = None) -> Dict:
    """
    Executa um comando de forma síncrona (wrapper para uso em Flask).
    
    Args:
        command: Comando em linguagem natural
        credentials: Dicionário com credenciais
        
    Returns:
        Dicionário com resultado da execução
    """
    from .nlu_command_parser import NLUCommandParser
    
    async def _run():
        parser = NLUCommandParser()
        parsed = parser.parse(command)
        
        agent = PicaPauAgent(headless=False)
        try:
            result = await agent.execute_command(parsed, credentials)
            return result.to_dict()
        finally:
            await agent.stop()
    
    return asyncio.run(_run())


# Teste standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        from nlu_command_parser import NLUCommandParser
        
        parser = NLUCommandParser()
        agent = PicaPauAgent(headless=False)
        
        try:
            # Teste simples de navegação
            command = "PicaPau navegue para google.com"
            parsed = parser.parse(command)
            result = await agent.execute_command(parsed)
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        
        finally:
            await agent.stop()
    
    asyncio.run(test())
