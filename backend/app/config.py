import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "local-development-jwt-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///mtaafix.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "true").lower() == "true"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
