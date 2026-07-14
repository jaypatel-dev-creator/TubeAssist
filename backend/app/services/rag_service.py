from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from app.services.retriever_service import retrieve_with_scores
from app.core.config import get_settings
from app.core.exceptions import RAGException


THRESHOLD = 0.7

# ── Singletons ─────────────────────────────────────────────────────────────────
_llm: ChatGoogleGenerativeAI | None = None
_prompt: ChatPromptTemplate | None = None
_general_prompt: ChatPromptTemplate | None = None


def get_llm() -> ChatGoogleGenerativeAI:
    if _llm is None:
        raise RuntimeError("RAG service not initialized. Call init_rag_service() on startup.")
    return _llm


def extract_text_content(content) -> str:
    """Normalize Gemini content — handles both string and list of parts."""
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return content or ""


def init_rag_service() -> None:
    global _llm, _prompt, _general_prompt

    _llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=get_settings().gemini_api_key,
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
        ("human", "Context: {context}\nQuestion: {question}")
    ])

    _general_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful general assistant.
Answer the user's question using your own knowledge.
Be concise and accurate."""),
        ("human", "{question}")
    ])


def _llm_fallback(question: str) -> dict:
    try:
        messages = _general_prompt.format_messages(question=question)
        response = get_llm().invoke(messages)
        text = extract_text_content(response.content)
        return {"answer": text, "sources": [], "from_video": False}
    except Exception as e:
        raise RAGException(f"Fallback LLM call failed: {str(e)}")


def ask(question: str, video_id: str | None = None) -> dict:
    try:
        docs_with_scores = retrieve_with_scores(query=question, video_id=video_id)
        relevant_docs = [doc for doc, score in docs_with_scores if score < THRESHOLD]

        # Stage 1 — score filter
        if not relevant_docs:
            return _llm_fallback(question)

        context = "\n\n".join(doc.page_content for doc in relevant_docs)
        messages = _prompt.format_messages(
            context=context,
            question=question
        )
        response = get_llm().invoke(messages)
        text = extract_text_content(response.content)

        # Stage 2 — LLM-as-a-Judge
        if text.strip() == "NO_RELEVANT_CONTEXT":
            return _llm_fallback(question)

        return {
            "answer": text,
            "sources": [doc.metadata for doc in relevant_docs],
            "from_video": True
        }
    except RAGException:
        raise
    except Exception as e:
        raise RAGException(f"Failed to generate answer: {str(e)}")