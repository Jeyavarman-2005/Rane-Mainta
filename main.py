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
    def __init__(self, user_role: str = 'master'):
        os.environ["OPENROUTER_API_KEY"] = "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"
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            model="qwen/qwen3-32b:free",
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
        self.collection_names = {
            'master': 'machine_data_master',
            '1150': 'machine_data_1150',
            '1200': 'machine_data_1200',
            '1250': 'machine_data_1250',
            '1300': 'machine_data_1300'
        }
        self.user_role = user_role
        self.vector_store = self._initialize_vector_store()
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 50}
        )
        self.conversation_history = []
        
    def _initialize_vector_store(self):
        """Initialize connection to Qdrant vector store based on user role"""
        client = QdrantClient(
            host="localhost",
            port=6333,
            timeout=30.0
        )
        
        collection_name = self.collection_names.get(self.user_role, 'machine_data_master')
        
        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=self.embeddings
        )
    
    def switch_collection(self, new_role: str):
        """Switch to a different collection based on user role"""
        if new_role in self.collection_names:
            self.user_role = new_role
            self.vector_store = self._initialize_vector_store()
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 50}
            )
            logger.info(f"Switched to collection for {new_role}")
        else:
            logger.warning(f"Invalid role: {new_role}. Keeping current collection.")
    
    def _format_docs(self, docs: List[Dict]) -> str:
        """Format retrieved documents for context with better structure"""
        formatted = []
        for doc in docs:
            formatted.append(
                f"### Machine Breakdown Record\n"
                f"**Machine ID:** {doc.metadata.get('machine_id', 'Unknown')}\n"
                f"**Machine Name:** {doc.metadata.get('machine_name', 'Unknown')}\n"
                f"**SAP Code:** {doc.metadata.get('sap_code', 'Unknown')}\n"
                f"**Plant:** {doc.metadata.get('plant', 'Unknown')}\n"
                f"**Shop:** {doc.metadata.get('shop', 'Unknown')}\n"
                f"**Module:** {doc.metadata.get('module', 'Unknown')}\n"
                f"**Line:** {doc.metadata.get('line', 'Unknown')}\n"
                f"**Problem Type:** {doc.metadata.get('problem_type', 'Unknown')}\n"
                f"**Service Type:** {doc.metadata.get('service_type', 'Unknown')}\n"
                f"**Shift:** {doc.metadata.get('shift', 'Unknown')}\n"
                f"**Duration (Minutes):** {doc.metadata.get('duration_minutes', 0)} minutes\n"
                f"**Duration (Hours):** {doc.metadata.get('duration_hours', 0.0)} hours\n"
                f"**Start Time:** {doc.metadata.get('start_time', 'Unknown')}\n"
                f"**End Time:** {doc.metadata.get('end_time', 'Unknown')}\n"
                f"**Problem:** {doc.metadata.get('problem', 'Unknown')}\n"
                f"**Solution:** {doc.metadata.get('solution', 'No solution provided')}\n"
                f"**Details:** {doc.metadata.get('details', 'No additional details')}\n"
                f"**Closure Reason:** {doc.metadata.get('closure_reason', 'Unknown')}\n"
                f"**Breakdown Type:** {doc.metadata.get('breakdown_type', 'Unknown')}\n"
                f"**SAP Status:** {doc.metadata.get('sap_status', 'Unknown')}\n"
                f"**Sub Group:** {doc.metadata.get('sub_group', 'Unknown')}\n"
                f"**Phenomena:** {doc.metadata.get('phenomena', 'Unknown')}\n"
                f"**LOTO:** {doc.metadata.get('loto', 'Unknown')}\n"
                f"**Vendor:** {doc.metadata.get('vendor', 'Unknown')}\n"
                f"**Material:** {doc.metadata.get('material', 'Unknown')}\n"
                f"**Unique ID:** {doc.metadata.get('unique_id', 'Unknown')}\n"
                f"**Type ID:** {doc.metadata.get('type_id', 'Unknown')}\n"
                f"**Relevance Score:** {doc.metadata.get('relevance_score', 'N/A')}\n"
                f"**Human Readable Text:** {doc.metadata.get('human_readable_text', 'N/A')}\n"
                f"**Full Text:** {doc.metadata.get('full_text', 'N/A')}\n"
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
        - Include relevant statistics, patterns, or trends
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
            f"Analyze the problems in plant {self.user_role}, including frequency and downtime impact",
            "What is the problem with highest downtime? Include specific cases and solutions",
            "Generate a detailed troubleshooting guide for 'Auto cycle not working'",
            "What are the most frequent problems in shift A? Include dates and solutions",
            "Create a summary report of issues with statistics"
        ]
        
        for question in questions:
            print(f"\n\033[1mQuestion:\033[0m {question}")
            print("\033[1mAnswer:\033[0m")
            print(self.query(question))
            print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    # Example usage with user role switching
    print("Initializing with master collection...")
    rag_system = MachineBreakdownRAG(user_role='master')
    rag_system.analyze_data()
    
    print("\nSwitching to plant 1150 collection...")
    rag_system.switch_collection('1150')
    rag_system.analyze_data()
    
    # Interactive mode with better formatting
    print("\n\033[1mInteractive Query Mode (type 'exit' to quit)\033[0m")
    while True:
        user_query = input("\n\033[1mYour question about machine breakdowns:\033[0m ")
        if user_query.lower() == 'exit':
            break
        print("\n\033[1mAnswer:\033[0m")
        print(rag_system.query(user_query))