from ollama import Client
from config import Config
from typing import List, Dict

class Generator:
    def __init__(self):
        self.client = Client(host=Config.OLLAMA_HOST)
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self):
        """Create the system prompt for the LLM"""
        return """You are a helpful assistant that answers questions about machine breakdowns in a manufacturing plant.
        Use only the provided context to answer questions. If you don't know the answer, say "I don't have that information."
        
        Follow these guidelines:
        1. Be precise and factual
        2. Cite specific details from the context when possible
        3. For duration questions, provide exact numbers
        4. For lists, provide a bullet-point summary
        5. Never make up information not present in the context"""
    
    def generate_response(self, query: str, context_docs: List[Dict]) -> Dict:
        """Generate a response using Llama3"""
        context = "\n\n".join([doc["content"] for doc in context_docs])
        
        response = self.client.generate(
            model=Config.LLM_MODEL,
            prompt=query,
            system=self.system_prompt,
            context=context,
            options={
                'temperature': 0.3,  # Lower temperature for more factual responses
                'top_p': 0.9
            }
        )
        
        return {
            "answer": response["response"],
            "context_docs": context_docs
        }

if __name__ == "__main__":
    from vector_db import VectorDB
    from retrieval import Retriever
    
    # Test the generation system
    db = VectorDB()
    retriever = Retriever(db)
    generator = Generator()
    
    query = "What were the longest breakdowns in P4_SHOP 1?"
    docs = retriever.apply_filters(query, shop_name="P4_SHOP 1")
    
    if docs:
        response = generator.generate_response(query, docs)
        print("Question:", query)
        print("Answer:", response["answer"])
        print("\nSources:")
        for doc in response["context_docs"]:
            print(f"- {doc['metadata']['MachineName']} ({doc['metadata']['Minutes']} minutes)")
    else:
        print("No documents found for the query")