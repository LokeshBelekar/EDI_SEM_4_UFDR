# File: core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Centralized configuration management using Pydantic BaseSettings.
    Automatically loads variables from the .env file and provides defaults.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General App Settings ---
    PROJECT_NAME: str = "UFDR AI Forensic Analyzer"
    VERSION: str = "5.0.0"
    DEBUG: bool = False
    DATASET_PATH: str = "touse"

    # --- PostgreSQL Configuration ---
    POSTGRES_USER: str = Field(..., alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., alias="POSTGRES_PASSWORD")
    POSTGRES_HOST: str = Field("localhost", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field("forensics", alias="POSTGRES_DB")

    # --- Neo4j Configuration ---
    NEO4J_URI: str = Field("bolt://127.0.0.1:7687", alias="NEO4J_URI")
    NEO4J_USERNAME: str = Field("neo4j", alias="NEO4J_USERNAME")
    NEO4J_PASSWORD: str = Field(..., alias="NEO4J_PASSWORD")

    # --- Groq AI Configuration ---
    GROQ_API_KEY: str = Field(..., alias="GROQ_API_KEY")
    GROQ_MODEL: str = Field("llama-3.3-70b-versatile", alias="GROQ_MODEL")

# Instantiate settings singleton
settings = Settings()