@echo off
echo ============================================================
echo   INSTALANDO AGENTE PICAPAU - COMET BRIDGE VISION
echo ============================================================
echo.

echo [1/3] Instalando dependencias Python...
pip install playwright cryptography

echo.
echo [2/3] Instalando navegador Chromium para Playwright...
playwright install chromium

echo.
echo [3/3] Criando diretorios necessarios...
if not exist "browser_profiles" mkdir browser_profiles
if not exist "screenshots" mkdir screenshots

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo Para usar o PicaPau, reinicie o COMET Bridge Vision.
echo.
pause
