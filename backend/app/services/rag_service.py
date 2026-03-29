
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import GEMINI_API_KEY
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.retriever_service import RetrieverService
from app.services.memory_service import MemoryService




class RAGService:
  ## constructor injection for services 
    def __init__(
        self,
        retriever_service: RetrieverService,  # object of RetrieverService
        memory_service: MemoryService         # object of MemoryService
    ):
        self.retriever = retriever_service
        self.memory = memory_service

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3
        )

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful assistant that answers questions ONLY using the provided video transcript context.
If the answer is not found in the context, respond with exactly:
'This topic isn't covered in the video. Try asking something specific to the video content.'
Do not use any outside knowledge. Do not hallucinate."""
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                """Context: {context}
                   Question: {question}"""
            )
        ])

    def ask(self, question: str, video_id: str | None = None):
        ## retrieve relevant chunks 
        docs = self.retriever.retrieve(query=question, video_id=video_id)

        if not docs:
            return {
                "answer": "This topic isn't covered in the video. Try asking something specific to the video content.",
                "sources": []
            }
        ## combine relevant chunks 
        context = "\n\n".join(doc.page_content for doc in docs)
        chat_history = self.memory.get_history() ## load chathistory
        messages = self.prompt.format_messages( ## build prompt 
            chat_history=chat_history,
            context=context,
            question=question
        )
        response = self.llm.invoke(messages) ## calling llm 
        self.memory.save(question, response.content) ## storing conversation  in memory 

        return {
            "answer": response.content,
            "sources": [doc.metadata for doc in docs] # video_id, author, title, chunk_index 
        }
    
    #   sources will contain following metadatas
    #
    # "metadata": {
#     "video_id": "...", -> from transcriptservice 
#     "title": "...", -> from metadata service 
#     "author": "...", -> from metadata service 
#     "chunk_index": 0 -> from chunking service 
#   }
# }