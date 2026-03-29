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

        # ── RAG prompt — used when relevant chunks are found ──────────────────
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful assistant that answers questions about a YouTube video.
Use the provided transcript context to answer the user's question.
If the answer can be inferred or derived from the context, answer it fully.
If the context is insufficient, answer using your general knowledge but keep the answer related to the video topic.
Do not hallucinate or make up facts."""
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                """Context: {context}
                   Question: {question}"""
            )
        ])

        # ── General prompt — used when no relevant chunks found ───────────────
        # Fires when all retrieved chunks score above the relevance threshold
        # OR when ChromaDB returns zero docs entirely.
        self.general_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful general assistant.
Answer the user's question using your own knowledge.
Be concise and accurate."""
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                "{question}"
            )
        ])

    def ask(self, question: str, video_id: str | None = None):

        # retrieve chunks with relevance scores
        docs_with_scores = self.retriever.retrieve_with_scores(
            query=question, video_id=video_id
        )

        # ChromaDB cosine distance — lower = more relevant
        # 0.0 = identical, 0.7+ = likely irrelevant to the question
        THRESHOLD = 0.7
        relevant_docs = [doc for doc, score in docs_with_scores if score < THRESHOLD]

        # ── LLM fallback — no relevant chunks found ───────────────────────────
        # Fires when:
        # 1. ChromaDB returns zero docs (video not indexed)
        # 2. All retrieved chunks score above threshold (unrelated question)
        if not relevant_docs:
            chat_history = self.memory.get_history()
            messages = self.general_prompt.format_messages(
                chat_history=chat_history,
                question=question
            )
            response = self.llm.invoke(messages)
            self.memory.save(question, response.content)
            return {
                "answer": response.content,
                "sources": [],
                "from_video": False  # ← frontend shows "General knowledge" badge
            }

        # ── RAG flow — relevant chunks found ─────────────────────────────────
        context = "\n\n".join(doc.page_content for doc in relevant_docs)  ## combine relevant chunks
        chat_history = self.memory.get_history()                           ## load chat history
        messages = self.prompt.format_messages(                            ## build prompt
            chat_history=chat_history,
            context=context,
            question=question
        )
        response = self.llm.invoke(messages)           ## calling llm
        self.memory.save(question, response.content)   ## storing conversation in memory

        return {
            "answer": response.content,
            "sources": [doc.metadata for doc in relevant_docs],  # video_id, author, title, chunk_index
            "from_video": True  # ← answer grounded in video transcript
        }

        #   sources will contain following metadatas
        #
        # "metadata": {
        #     "video_id": "...", -> from transcriptservice
        #     "title": "...",    -> from metadata service
        #     "author": "...",   -> from metadata service
        #     "chunk_index": 0   -> from chunking service
        #   }
        # }