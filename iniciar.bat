@echo off
cd /d "%~dp0"
echo Verificando dependencias...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo.
echo Iniciando o sistema GEC...
echo Acesse http://localhost:5000 no navegador.
echo Para encerrar, feche esta janela ou pressione CTRL+C.
echo.
python app.py
pause
