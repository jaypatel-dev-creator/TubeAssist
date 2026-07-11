from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# ── Singleton ──────────────────────────────────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


def create_chunks(transcript_data: dict) -> list[Document]:
    base_document = Document(
        page_content=transcript_data["transcript"],
        metadata={
            "video_id": transcript_data["video_id"],
            "title": transcript_data["title"],
            "author": transcript_data["author"],
        }
    )

    documents = _splitter.split_documents([base_document])

    for i, doc in enumerate(documents):
        doc.metadata["chunk_index"] = i

    return documents