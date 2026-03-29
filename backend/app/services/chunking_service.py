from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents  import Document


class ChunkingService:

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
           
        )

    def create_chunks(self, transcript_data: dict) -> list[Document]:

        base_document = Document(
            page_content=transcript_data["transcript"], # transcript data is returning   video_id, title, author , transcript , from that we are only selecting transcript as page content and metadatas in metadata 
            #this metadata will be stored in chroma 
            metadata={
                "video_id": transcript_data["video_id"],
                "title": transcript_data["title"],
                "author": transcript_data["author"],
            }
        )
        documents = self.text_splitter.split_documents([base_document])

    ## adding chunk index metadata in splitted chunks 
        for i, doc in enumerate(documents):
            doc.metadata["chunk_index"] = i
        return documents 
    
    ## finally each chunk looks like 
#     {
#   "page_content": "some text...",
#   "metadata": {
#     "video_id": "...", -> from transcriptservice 
#     "title": "...", -> from metadata service 
#     "author": "...", -> from metadata service 
#     "chunk_index": 0 -> from chunking service 
#   }
# }

