from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationBufferWindowMemory

from app.services.retriever_service import retrieve_with_scores
from app.core.config import GEMINI_API_KEY


THRESHOLD = 0.7

# ── Singletons ─────────────────────────────────────────────────────────────────
_llm: ChatGoogleGenerativeAI | None = None
_prompt: ChatPromptTemplate | None = None
_general_prompt: ChatPromptTemplate | None = None


def get_llm() -> ChatGoogleGenerativeAI:
    if _llm is None:
        raise RuntimeError("RAG service not initialized. Call init_rag_service() on startup.")
    return _llm


def init_rag_service() -> None:
    global _llm, _prompt, _general_prompt

    _llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.3
    )

    _prompt = ChatPromptTemplate.from_messages([
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

    _general_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful general assistant.
Answer the user's question using your own knowledge.
Be concise and accurate."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])


def _build_memory() -> ConversationBufferWindowMemory:
    return ConversationBufferWindowMemory(
        k=5,
        memory_key="chat_history",
        return_messages=True
    )


def _llm_fallback(question: str, chat_history: list, memory: ConversationBufferWindowMemory) -> dict:
    messages = _general_prompt.format_messages(
        chat_history=chat_history,
        question=question
    )
    response = get_llm().invoke(messages)
    memory.save_context({"input": question}, {"output": response.content})
    return {"answer": response.content, "sources": [], "from_video": False}


def ask(question: str, video_id: str | None = None) -> dict:
    memory = _build_memory()
    chat_history = memory.load_memory_variables({})["chat_history"]

    docs_with_scores = retrieve_with_scores(query=question, video_id=video_id)
    relevant_docs = [doc for doc, score in docs_with_scores if score < THRESHOLD]

    # Stage 1 — score filter
    if not relevant_docs:
        return _llm_fallback(question, chat_history, memory)

    context = "\n\n".join(doc.page_content for doc in relevant_docs)
    messages = _prompt.format_messages(
        chat_history=chat_history,
        context=context,
        question=question
    )
    response = get_llm().invoke(messages)

    # Stage 2 — LLM-as-a-Judge
    if response.content.strip() == "NO_RELEVANT_CONTEXT":
        return _llm_fallback(question, chat_history, memory)

    memory.save_context({"input": question}, {"output": response.content})
    return {
        "answer": response.content,
        "sources": [doc.metadata for doc in relevant_docs],
        "from_video": True
    }