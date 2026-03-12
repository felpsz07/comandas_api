# Felipe Bueno de Oliveira
from dotenv import load_dotenv, find_dotenv
import os

# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Careega o aqrquivo .env
load_dotenv(dotenv_file)


# Configurações da API
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
RELOAD = os.getenv("RELOAD")

# Configurações do Banco de Dados
DB_SGDB = os.getenv("DB_SGDB")
DB_NAME = os.getenv("DB_NAME")

# Caso seja diferente de slite
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# Ajusta STR_DATABASE CONFORME GERENCIADOR ESCOLHIDOu

if DB_SGDB == "sqlite":
    STR_DATABASE = f"{DB_SGDB}:///{DB_NAME}.db"
elif DB_SGDB == "mysql":
    import pymysql
    STR_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
elif DB_SGDB == "mssql":
    import pymssql
    STR_DATABASE =f"mssql+pymssql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8"
else:     # SQLite
    STR_DATABASE = f"sqlite:///./comandas_db.db"