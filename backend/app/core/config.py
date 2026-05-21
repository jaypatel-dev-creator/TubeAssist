import os
from dotenv import load_dotenv

APP_ENV = os.getenv("APP_ENV", "development")

if APP_ENV == "production":
    load_dotenv(".env.production")
else:
    load_dotenv(".env")

GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")
VECTOR_STORE     = os.getenv("VECTOR_STORE", "chroma")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX", "tubeassist")