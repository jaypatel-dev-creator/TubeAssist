from langchain_classic.memory import ConversationBufferWindowMemory

class MemoryService:

    def __init__(self):
        self.memory = ConversationBufferWindowMemory(
            k=5,  # store last 5 conversation turns
            memory_key="chat_history",## this specifies variable_name in Mesageplaceholder in ChatPrompttemplate
            return_messages=True ##  memory service will return messages in form of list of message objects (human,system,ai) instead of raw strings. 
        )


    
    def get_history(self):
        return self.memory.load_memory_variables({})["chat_history"] ## to load chathistory in form of list of message object (human, ai)

    def save(self, question: str, answer: str): ## to save current turn's  human and ai message 
        self.memory.save_context(
            {"input": question}, ## save as HumanMessage
            {"output": answer} ## save as AIMessage
        )