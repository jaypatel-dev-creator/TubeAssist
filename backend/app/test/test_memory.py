from app.services.rag_service import RAGService

rag = RAGService()

print(rag.ask("What is the main idea?")["answer"])

print("\nFollow up:\n")

print(rag.ask("Why does that happen?")["answer"])

