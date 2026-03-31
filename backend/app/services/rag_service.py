from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.retriever_service import RetrieverService
from app.services.memory_service import MemoryService
from app.core.config import GEMINI_API_KEY


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

        # RAG prompt => when relevant document are found 
        # Stage 2 filter — if context is irrelevant, LLM returns "NO_RELEVANT_CONTEXT" which wil return llm fallback 
      
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are a helpful assistant that answers questions about a YouTube video.
You will be given transcript context and a user question.

Follow these rules strictly:
1. If the context is relevant to the question — answer using the context fully
2. If the context is NOT relevant to the question — respond with exactly this phrase and nothing else:
   "NO_RELEVANT_CONTEXT"
Do not hallucinate. Do not make up facts."""
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                """Context: {context}
                   Question: {question}"""
            )
        ])

        # ── General prompt  @ LLM fallback 
        # Fires when:
        # Stage 1 — all chunks score above threshold (score filter) => stage 1 filter 
        # Stage 2 — LLM flags context as irrelevant (NO_RELEVANT_CONTEXT) => stage 2 filter 
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

    def _llm_fallback(self, question: str, chat_history: list):
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

    def ask(self, question: str, video_id: str | None = None):

        # retrieve chunks with relevance scores
        docs_with_scores = self.retriever.retrieve_with_scores(
            query=question, video_id=video_id
        )

        # ── Stage 1: Score-based filter ───────────────────────────────────────
        #both chroma and pinecone => threshold 0.7 
        THRESHOLD = 0.7
        relevant_docs = [doc for doc, score in docs_with_scores if score < THRESHOLD]

        chat_history = self.memory.get_history()

        # Stage 1 llm  fallback — no chunks passed score filter
        if not relevant_docs:
            return self._llm_fallback(question, chat_history)

    # when relevant context found, then RAG prompt will be fired. 
        context = "\n\n".join(doc.page_content for doc in relevant_docs)  ## combine relevant chunks
        messages = self.prompt.format_messages(                            ## build prompt
            chat_history=chat_history,
            context=context,
            question=question
        )
        response = self.llm.invoke(messages)           ## calling llm


        # ── Stage 2: LLM-based relevance check ───────────────────────────────
        # Even if chunks pass score filter, LLM verifies context is actually relevant, when LLM flagged context as irrelevant, then again llm fallback 
    
        if response.content.strip() == "NO_RELEVANT_CONTEXT":
            return self._llm_fallback(question, chat_history)

       
        self.memory.save(question, response.content)   ## storing conversation in memory (both rag and llm fallback answer is stored. )

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