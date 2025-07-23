import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.llms import Ollama
from langchain.chat_models import ChatOpenAI
from langchain_community.embeddings import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MachineBreakdownRAG:
    def __init__(self):
        os.environ["OPENROUTER_API_KEY"] = "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"
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat-v3-0324:free",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.2,
            max_tokens=2048,
            model_kwargs={
                "response_format": {
                    "type": "text",  # Can be "text" or "json_object"
                    "structure": {
                        "summary": "string",
                        "details": "array",
                        "actions": "array",
                        "references": "array"
                    }
                }
            }
        )

        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vector_store = self._initialize_vector_store()
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 50}
        )
        self.conversation_history = []
        
    def _initialize_vector_store(self):
        """Initialize connection to Qdrant vector store"""
        client = QdrantClient(
            host="localhost",
            port=6333,
            timeout=30.0
        )
        
        return QdrantVectorStore(
            client=client,
            collection_name="machine_data",
            embedding=self.embeddings
        )
    
    def _format_docs(self, docs: List[Dict]) -> str:
        """Format retrieved documents for context with better structure"""
        formatted = []
        for doc in docs:
            formatted.append(
                f"### Machine Breakdown Record\n"
                f"**Machine Name:** {doc.metadata.get('machine_name', 'Unknown')}\n"
                f"**SAP Code:** {doc.metadata.get('sap_code', 'Unknown')}\n"
                f"**Plant:** {doc.metadata.get('plant', 'Unknown')}\n"
                f"**Shop:** {doc.metadata.get('shop', 'Unknown')}\n"
                f"**Shift:** {doc.metadata.get('shift', 'Unknown')}\n"
                f"**Date:** {doc.metadata.get('start_time', 'Unknown date')}\n"
                f"**Problem:** {doc.metadata.get('problem', 'Unknown')}\n"
                f"**Solution:** {doc.metadata.get('solution', 'No solution provided')}\n"
                f"**Downtime:** {doc.metadata.get('duration_minutes', 0)} minutes\n"
                f"**Details:** {doc.metadata.get('details', 'No additional details')}\n"
                f"**Relevance Score:** {doc.metadata.get('relevance_score', 'N/A')}\n"
            )
        return "\n\n".join(formatted)
    
    def _get_rag_chain(self):
        """Create the RAG chain with enhanced prompt for better formatting"""
        template = """You are an expert technician assistant analyzing machine breakdown data. 
        Provide comprehensive, well-structured answers using Markdown formatting with these sections:

        ### Summary
        - Concise 1-2 sentence overview of the answer
        
        ### Detailed Analysis
        - Bullet points or numbered lists of key findings
        - 
        
        Include relevant statistics, patterns, or trends
        - Reference specific machines, problems, and solutions
        
        ### Recommended Actions (if applicable)
        - Step-by-step instructions for problem resolution
        - Preventive measures to avoid recurrence
        
        ### Supporting Evidence
        - Reference specific records from the context
        - Include machine names, dates, and downtime metrics
        
        Maintain a professional yet approachable tone. If information is incomplete, state what you know and what's uncertain.
        
        **Context:** {context}
        
        **Question:** {question}
        
        **Conversation History:** {history}
        
        **Answer:**"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        return (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
                "history": lambda _: "\n".join(self.conversation_history[-3:])  # Last 3 exchanges
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
    
    def query(self, question: str) -> str:
        """Query the RAG system with a question and maintain conversation history"""
        rag_chain = self._get_rag_chain()
        response = rag_chain.invoke(question)
        
        # Update conversation history
        self.conversation_history.append(f"User: {question}")
        self.conversation_history.append(f"Assistant: {response}")
        
        # Keep history manageable
        if len(self.conversation_history) > 6:  # 3 exchanges
            self.conversation_history = self.conversation_history[-6:]
            
        return response
    
    def analyze_data(self):
        """Run sample analyses to demonstrate system capabilities"""
        questions = [
            "list all the machines with their most common problems",
            "How to rectify sensor failure based on historical solutions? Provide step-by-step instructions.",
            "Analyze the problems in OBJ Assy - 01, including frequency and downtime impact",
            "Compare downtime between plant 1150 and other plants",
            "What is the problem with highest downtime? Include specific cases and solutions",
            "Generate a detailed troubleshooting guide for 'Auto cycle not working'",
            "What are the most frequent problems in shift A? Include dates and solutions",
            "Perform a comparative analysis of problems in AMS vs OTR ASSY - 04",
            "Create a summary report of issues for OBJ Assy 01 with statistics"
        ]
        
        for question in questions:
            print(f"\n\033[1mQuestion:\033[0m {question}")
            print("\033[1mAnswer:\033[0m")
            print(self.query(question))
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    rag_system = MachineBreakdownRAG()
    
    # Run sample analyses
    rag_system.analyze_data()
    
    # Interactive mode with better formatting
    print("\n\033[1mInteractive Query Mode (type 'exit' to quit)\033[0m")
    while True:
        user_query = input("\n\033[1mYour question about machine breakdowns:\033[0m ")
        if user_query.lower() == 'exit':
            break
        print("\n\033[1mAnswer:\033[0m")
        print(rag_system.query(user_query)) 