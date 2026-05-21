from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.services.retriever_service import RetrieverService
from app.services.memory_service import MemoryService
from app.core.config import GEMINI_API_KEY
class RAGService:
    THRESHOLD = 0.7

    def __init__(self, retriever_service: RetrieverService, memory_service: MemoryService):
        self.retriever = retriever_service
        self.memory = memory_service
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.3
        )
        # RAG prompt 
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that answers questions about a YouTube video.
You will be given transcript context and a user question.

Follow these rules strictly:
1. If the context is relevant to the question — answer using the context fully
2. If the context is NOT relevant to the question — respond with exactly this phrase and nothing else:
   "NO_RELEVANT_CONTEXT"
Do not hallucinate. Do not make up facts."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Context: {context}\nQuestion: {question}")
        ])

# fallback prompt 
        self.general_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful general assistant.
Answer the user's question using your own knowledge.
Be concise and accurate."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

# triggers when llm fallback is triggered 
    def _llm_fallback(self, question: str, chat_history: list):
        messages = self.general_prompt.format_messages(
            chat_history=chat_history,
            question=question
        )
        response = self.llm.invoke(messages)
        self.memory.save(question, response.content) # saving user query alond with ai response without metadata
        return {"answer": response.content, "sources": [], "from_video": False}


    def ask(self, question: str, video_id: str | None = None):
        # first getting history of messages 
        chat_history = self.memory.get_history()
       # retrieve relevant docs  with scores from vectorStore
        docs_with_scores = self.retriever.retrieve_with_scores(query=question, video_id=video_id)
        relevant_docs = [doc for doc, score in docs_with_scores if score < self.THRESHOLD]
      # stage1 filter: when retrieved docs score < threshold, then trigger llm falllback 
        if not relevant_docs:
            return self._llm_fallback(question, chat_history)
      # when relevant docs found(score>threshold), then below code will run
        context = "\n\n".join(doc.page_content for doc in relevant_docs) # build context i.e. relevant chunks for RAGprompt 
        messages = self.prompt.format_messages(
            chat_history=chat_history,
            context=context,
            question=question
        )
        response = self.llm.invoke(messages)
       # stage2 relevance filter: when LLM as judge responds that retrieved chunk is not relevant , then again trigger llm fallback
        if response.content.strip() == "NO_RELEVANT_CONTEXT":
            return self._llm_fallback(question, chat_history)
    # when no stage2 fallback, then save the response of llm wihtout fallback one in memory for context.(for fallback, memory saving is handled inside llm_fallback() function) 
        self.memory.save(question, response.content)
        return {
            "answer": response.content,
            "sources": [doc.metadata for doc in relevant_docs],
            "from_video": True
        }