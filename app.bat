@echo off
REM Start Ollama server in a new Command Prompt window
start "Ollama Server" cmd /k "ollama serve"

REM Wait a second to make sure Ollama starts first (optional)
timeout /t 2 /nobreak >nul

REM Start Streamlit in a new Command Prompt window with virtual env
start "Streamlit App" cmd /k "call .\env\Scripts\activate && streamlit run chat.py"
