@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo O Python Launcher nao foi encontrado. Instale o Python para Windows.
    pause
    exit /b 1
)

py -3 -c "import PIL, pystray" >nul 2>&1
if errorlevel 1 (
    echo Instalando as dependencias necessarias para o Painel S1...
    py -3 -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo A instalacao falhou. Confira a conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
)

py -3 -c "import PIL, pystray" >nul 2>&1
if errorlevel 1 (
    echo As dependencias continuam indisponiveis neste Python:
    py -3 -c "import sys; print(sys.executable)"
    pause
    exit /b 1
)

where pyw >nul 2>&1
if errorlevel 1 (
    echo O iniciador pyw do Python nao foi encontrado.
    echo Reinstale o Python para Windows habilitando o Python Launcher.
    pause
    exit /b 1
)

start "" pyw -3 "%~dp0app.py"
