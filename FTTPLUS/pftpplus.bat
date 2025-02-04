@echo off
REM Verifica se o Python está instalado utilizando o comando "where"
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python não encontrado. Instalando...
    REM Abre a página do Python para download
    start https://www.python.org/downloads/
    echo ⚠️ Após a instalação, execute o script novamente.
    pause
    exit /b 1
)

REM Verifica se a versão do Python é 3.6 ou superior
python -c "import sys; sys.exit(0 if sys.version_info >= (3,6) else 1)" >nul 2>nul
if errorlevel 1 (
    echo ❌ Python 3.6 ou superior é necessário
    exit /b 1
)

REM Tenta importar o módulo "cryptography" para confirmar se está instalado
python -c "import cryptography" >nul 2>nul
if errorlevel 1 (
    echo 📥 Instalando biblioteca cryptography...
    python -m pip install cryptography
)

REM Executa o cliente passando os argumentos fornecidos para o script
python cliente.py %*