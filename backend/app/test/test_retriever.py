from app.dependencies import get_retriever_service

r = get_retriever_service()

docs = r.retrieve(
    query="Why should we keep goals private?",
    k=2
)

for d in docs:
    print("\n---")
    print(d.page_content)
    print(d.metadata)