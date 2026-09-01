from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from app.services.retriever_service import retrieve_with_scores
from app.core.config import get_settings
from app.core.exceptions import RAGException


THRESHOLD = 0.7
HISTORY_WINDOW = 6  # max messages (3 user + 3 ai turns) sent to LLM

# ── Module-level singletons (stateless — safe to share across requests) ────────
_llm: ChatGoogleGenerativeAI | None = None
_prompt: ChatPromptTemplate | None = None
_general_prompt: ChatPromptTemplate | None = None

# ── Per-session store (NOT a singleton — each value is isolated per session_id) ─
_session_store: dict[str, list[dict]] = {}


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


def _get_history(session_id: str | None) -> list[dict]:
    """Return the windowed history for a session. Empty list if no session."""
    if not session_id:
        return []
    history = _session_store.get(session_id, [])
    # Keep only the last HISTORY_WINDOW messages
    return history[-HISTORY_WINDOW:]


def _append_to_history(session_id: str | None, question: str, answer: str) -> None:
    """Append the latest Q&A turn to the session's history list."""
    if not session_id:
        return
    if session_id not in _session_store:
        _session_store[session_id] = []
    _session_store[session_id].append({"role": "user", "content": question})
    _session_store[session_id].append({"role": "assistant", "content": answer})


def _build_history_text(history: list[dict]) -> str:
    """Format history list into a readable block for the prompt."""
    if not history:
        return ""
    lines = []
    for msg in history:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{prefix}: {msg['content']}")
    return "\n".join(lines)


def init_rag_service() -> None:
    global _llm, _prompt, _general_prompt

    _llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        google_api_key=get_settings().gemini_api_key,
        temperature=0.3
    )

    _prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that answers questions about a YouTube video.
You will be given transcript context, prior conversation history, and a user question.

Follow these rules strictly:
1. Use the conversation history to understand follow-up questions and maintain context.
2. If the context is relevant to the question — answer using the context fully.
3. If the context is NOT relevant to the question — respond with exactly this phrase and nothing else:
   "NO_RELEVANT_CONTEXT"
Do not hallucinate. Do not make up facts."""),
        ("human", "Context:\n{context}\n\nConversation History:\n{history}\n\nQuestion: {question}")
    ])

    _general_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful general assistant.
Answer the user's question using your own knowledge.
Use the conversation history to understand follow-up questions.
Be concise and accurate."""),
        ("human", "Conversation History:\n{history}\n\nQuestion: {question}")
    ])


def _llm_fallback(question: str, history: list[dict]) -> dict:
    try:
        history_text = _build_history_text(history)
        messages = _general_prompt.format_messages(
            history=history_text,
            question=question
        )
        response = get_llm().invoke(messages)
        text = extract_text_content(response.content)
        return {"answer": text, "sources": [], "from_video": False}
    except Exception as e:
        raise RAGException(f"Fallback LLM call failed: {str(e)}")


def ask(question: str, video_id: str | None = None, session_id: str | None = None) -> dict:
    try:
        history = _get_history(session_id)
        history_text = _build_history_text(history)

        docs_with_scores = retrieve_with_scores(query=question, video_id=video_id)
        relevant_docs = [doc for doc, score in docs_with_scores if score < THRESHOLD]

        # Stage 1 — score filter
        if not relevant_docs:
            result = _llm_fallback(question, history)
            _append_to_history(session_id, question, result["answer"])
            return result

        context = "\n\n".join(doc.page_content for doc in relevant_docs)
        messages = _prompt.format_messages(
            context=context,
            history=history_text,
            question=question
        )
        response = get_llm().invoke(messages)
        text = extract_text_content(response.content)

        # Stage 2 — LLM-as-a-Judge
        if text.strip() == "NO_RELEVANT_CONTEXT":
            result = _llm_fallback(question, history)
            _append_to_history(session_id, question, result["answer"])
            return result

        result = {
            "answer": text,
            "sources": [doc.metadata for doc in relevant_docs],
            "from_video": True
        }
        _append_to_history(session_id, question, text)
        return result

    except RAGException:
        raise
    except Exception as e:
        raise RAGException(f"Failed to generate answer: {str(e)}")