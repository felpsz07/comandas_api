# Felipe Bueno de Oliveira
from dotenv import load_dotenv, find_dotenv
import os

# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Careega o aqrquivo .env
load_dotenv(dotenv_file)


# Configurações da API
HOST = os.getenv("HOST", "0.0.0.0")
PORT = os.getenv("PORT", "8000")
RELOAD = os.getenv("RELOAD", True)