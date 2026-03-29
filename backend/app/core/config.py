import os 
from dotenv import load_dotenv
load_dotenv() ## reads .env file and loads its value in current environment

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
VECTOR_STORE      = os.getenv("VECTOR_STORE", "chroma")  
PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX    = os.getenv("PINECONE_INDEX", "tubeassist")