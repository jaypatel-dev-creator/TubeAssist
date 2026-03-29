from langchain_classic.memory import ConversationBufferWindowMemory

class MemoryService:

    def __init__(self):
## since this memory is not persistent like redis, postgre, so no DI needed 
        self.memory = ConversationBufferWindowMemory(
            k=5,  # store last 5 conversation turns
            memory_key="chat_history",## this specifies the key name  langchain uses to inject history to prompt template. 
            return_messages=True ##  memory service will return messages in form of list of message objects instead of raw strings. 
        )


    
    def get_history(self):
        return self.memory.load_memory_variables({})["chat_history"] ## to load past convo => in form of messages of langchain object (HumanMessage, AIMessage ..........)

    def save(self, question: str, answer: str): ## to save current turn's  question (user query) and answer (from LLM)
        self.memory.save_context(
            {"input": question}, ## save as HumanMessage
            {"output": answer} ## save as AIMessage
        )