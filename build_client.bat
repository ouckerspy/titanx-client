@echo off
REM Compila los dos clientes TITAN X (FiveM y Minecraft).
REM Requiere: pip install pyinstaller (una sola vez)
cd /d "%~dp0\.."

echo [1/2] Compilando TitanXClient_FiveM.exe...
pyinstaller --onefile --noconsole --uac-admin --name TitanXClient_FiveM ^
    --add-data "core;core" ^
    --add-data "config.py;." ^
    --add-data "client\eye.gif;." ^
    --paths . ^
    client\titanx_client.py
echo.

echo [2/2] Compilando TitanXClient_Minecraft.exe...
pyinstaller --onefile --noconsole --uac-admin --name TitanXClient_Minecraft ^
    --add-data "core;core" ^
    --add-data "config.py;." ^
    --add-data "client\eye.gif;." ^
    --paths . ^
    client\titanx_minecraft.py
echo.

echo ====================================================
echo  Listo:
echo    dist\TitanXClient_FiveM.exe
echo    dist\TitanXClient_Minecraft.exe
echo.
echo  Si el servidor no corre en esta PC, crea un archivo
echo  "server.txt" junto al .exe con la URL del servidor.
echo  Ej: http://192.168.1.50:7890
echo ====================================================
pause
