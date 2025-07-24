import logging
import os
from datetime import datetime
from typing import List, Dict
import httpx
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from qdrant_client import QdrantClient
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_qdrant import QdrantVectorStore


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MachineBreakdownRAG:
    def __init__(self, user_role: str = 'master'):
        
        self.llm = ChatOllama(
            model="qwq:32b",
            temperature=0.2,
            num_ctx=2048,  
            num_gpu=1,     
            num_thread=8, 
            top_k=20,      
            top_p=0.9,
            repeat_penalty=1.1,
            model_kwargs={
                "low_vram": True,  
                "n_batch": 512,    
            }
        )
        
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.collection_names = {
            'Master': 'machine_data_master',
            '1150': 'machine_data_1150',
            '1200': 'machine_data_1200',
            '1250': 'machine_data_1250',
            '1300': 'machine_data_1300'
        }
        self.user_role = user_role
        self.vector_store = self._initialize_vector_store()
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}  
        )
        self.conversation_history = []
        
    def _initialize_vector_store(self):
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
        if new_role in self.collection_names:
            self.user_role = new_role
            self.vector_store = self._initialize_vector_store()
            self.retriever = self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            logger.info(f"Switched to collection for {new_role}")
        else:
            logger.warning(f"Invalid role: {new_role}. Keeping current collection.")
    
    def verify_connection(self):
        try:
            self.vector_store.client.get_collections()
            return True, "Connected to Qdrant and vector store is ready"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        
    def _format_docs(self, docs: List[Dict]) -> str:
        formatted = []
        for doc in docs:
            formatted.append(
                f"### Machine Breakdown Record\n"
                f"**Machine Name:** {doc.metadata.get('machine_name', 'Unknown')}\n"
                f"**SAP Code:** {doc.metadata.get('sap_code', 'Unknown')}\n"
                f"**Plant:** {doc.metadata.get('plant', 'Unknown')}\n"
                f"**Shop:** {doc.metadata.get('shop', 'Unknown')}\n"
                f"**Module:** {doc.metadata.get('module', 'Unknown')}\n"
                f"**Line:** {doc.metadata.get('line', 'Unknown')}\n"
                f"**Problem Type:** {doc.metadata.get('problem_type', 'Unknown')}\n"
                f"**Shift:** {doc.metadata.get('shift', 'Unknown')}\n"
                f"**Duration (Minutes):** {doc.metadata.get('duration_minutes', 0)} minutes\n"
                f"**Start Time:** {doc.metadata.get('start_time', 'Unknown')}\n"
                f"**End Time:** {doc.metadata.get('end_time', 'Unknown')}\n"
                f"**Problem:** {doc.metadata.get('problem', 'Unknown')}\n"
                f"**Solution:** {doc.metadata.get('solution', 'No solution provided')}\n"
            )
        return "\n\n".join(formatted)
    
    def _get_rag_chain(self):
        template = """You are an expert technician assistant analyzing machine breakdown data. 
        Respond ONLY in this exact format with these sections (include the section headers):

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
        
        Current time: {time}
        
        Context: {context}
        
        Question: {question}
        
        Conversation History: {history}
        
        Provide ONLY the formatted response, no additional commentary:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        return (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
                "history": lambda _: "\n".join(self.conversation_history[-3:]),
                "time": lambda _: datetime.now().strftime("%I:%M %p")
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
    
    def query(self, question: str) -> str:
        rag_chain = self._get_rag_chain()
        try:
            response = rag_chain.invoke(question)
            self.conversation_history.append(f"User: {question}")
            self.conversation_history.append(f"Assistant: {response}")
            
            if len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]
                
            return response
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            return f"Error processing your request. Please try again. Technical details: {str(e)}"

# Initialize RAG system
rag_system = MachineBreakdownRAG()

# User database (in production, use proper authentication)
USER_DATABASE = {
    "master": {"password": "masterpass", "plant": "Master"},
    "plant1150": {"password": "plant1150pass", "plant": "1150"},
    "plant1200": {"password": "plant1200pass", "plant": "1200"},
    "plant1250": {"password": "plant1250pass", "plant": "1250"},
    "plant1300": {"password": "plant1300pass", "plant": "1300"}
}

security = HTTPBasic()

app = FastAPI(
    title="Machine Breakdown RAG API",
    description="API for interacting with the Machine Breakdown RAG system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["WWW-Authenticate"]  # Important for auth
)

# Data models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    status: str = "success"

class ExampleResponse(BaseModel):
    examples: list[str]

class HealthResponse(BaseModel):
    status: str
    message: str

class LoginResponse(BaseModel):
    status: str
    plant: str
    message: str

# Example questions
EXAMPLE_QUESTIONS = [
    "What are the most common problems reported for the machines?",
    "Which machine has the highest downtime?",
    "What are the solutions for sensor failures?",
    "What problems occur most frequently in shift A?"
]

def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials"""
    user = USER_DATABASE.get(credentials.username)
    if user is None or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

@app.get("/api/health")
async def health_check() -> HealthResponse:
    status, message = rag_system.verify_connection()
    return HealthResponse(status="ok" if status else "error", message=message)

@app.get("/api/examples")
async def get_example_questions() -> ExampleResponse:
    """Get example questions"""
    return ExampleResponse(examples=EXAMPLE_QUESTIONS)

@app.post("/api/login")
async def login(user: Dict = Depends(verify_user)) -> LoginResponse:
    """Login endpoint"""
    try:
        rag_system.switch_collection(user["plant"])
        return LoginResponse(
            status="success",
            plant=user["plant"],
            message=f"Logged in to plant {user['plant']} collection"
        )
    except Exception as e:
        logger.error(f"Error switching collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def process_query(
    query: QueryRequest,
    user: Dict = Depends(verify_user)
) -> QueryResponse:
    """Process chat query"""
    try:
        rag_system.switch_collection(user["plant"])
        answer = rag_system.query(query.question)
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)