import os

class Settings:
    PROJECT_NAME = "ml-publisher-enterprise"

    # 🔐 CHAVE ÚNICA DO SISTEMA (OBRIGATÓRIO SER A MESMA EM TODO LUGAR)
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

settings = Settings()