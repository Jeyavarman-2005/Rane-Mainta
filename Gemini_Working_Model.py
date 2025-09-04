# Standard library
import os
import logging
import base64
from typing import List, Dict, Optional

# FastAPI & Security
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware

# Data validation
from pydantic import BaseModel

# LangChain Core
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage

# LangChain Integrations
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore

# Qdrant
from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MachineBreakdownRAG:
    def __init__(self, user_role: str = 'master'):
        os.environ["GOOGLE_API_KEY"] = "AIzaSyATU6hs6njlxBhGwJT60JYf1LafFttY-kQ"  
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",  
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2,
            max_output_tokens=2048,
        )
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",  
            model_kwargs={"device": "cuda"},  
            encode_kwargs={"normalize_embeddings": True}
        )

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
    
    def verify_connection(self):
        """Verify connection to Qdrant"""
        try:
            self.vector_store.client.get_collections()
            return True, "Connected to Qdrant and vector store is ready"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        
    def _format_docs(self, docs: List[Dict]) -> str:
        """Format retrieved documents for context with better structure"""
        formatted = []
        for doc in docs:
            formatted.append(
                f"### Machine Breakdown Record\n"
                f"**Machine Name:** {doc.metadata.get('machine_name', 'Unknown')}\n"
                f"**SAP Code:** {doc.metadata.get('sap_code', 'Unknown')}\n"
                f"**Plant Code:** {doc.metadata.get('plant_code', 'Unknown')}\n"
                f"**Plant:** {doc.metadata.get('plant_name', 'Unknown')}\n"
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
                f"**Details:** {doc.metadata.get('details', 'No additional details')}\n"    
            )
        return "\n".join(formatted)
    
    def _get_rag_chain(self):
        """Create the RAG chain with a structured, instructional prompt for Gemini"""
        template = """**Role:** You are an expert technical assistant for industrial machine maintenance and breakdown analysis.

    **Objective:** Analyze the provided context and conversation history to answer the user's question comprehensively, clearly, and accurately.

    **Instruction: Structure your response strictly using the following Markdown sections. Use clear, concise, and professional language suitable for a technician.**

    ### 🎯 Executive Summary
    Provide a concise, high-level overview of your findings in 1-2 sentences. This should answer the user's primary question directly.

    ### 🔍 Detailed Analysis
    Present your key findings here. For each distinct point or finding, create a new bullet point.
    - **Focus on clarity:** Use clear and simple language. Avoid jargon unless it is standard industry terminology.
    - **Incorporate data:** Where possible, include specific statistics, metrics (e.g., downtime, frequency), patterns, or trends you identify.
    - **Be specific:** Explicitly reference machine names, problem types, solutions, and timeframes from the context.

    ### 🛠️ Recommended Actions (If Applicable)
    If the question involves problem-solving or prevention, provide actionable recommendations,start each step on a new line.
    1.  **Immediate Resolution:** List clear, step-by-step instructions to resolve the current issue.
    2.  **Preventive Measures:** Suggest specific, actionable steps to prevent the problem from recurring.

    ### 📊 Supporting Evidence
    **Synthesize common evidence patterns found across all retrieved contexts.**
    - **Group evidence by subtopics** (e.g., common failure patterns, recurring solutions, frequent time patterns)
    - **Each subtopic should be on a new line** with clear separation
    - **Focus on aggregated insights** rather than individual records
    - **Highlight frequency and patterns** observed across multiple instances
    - **Do not reference specific records** by machine name, SAP code, or date/time

    **Example structure:**
    - **Common Failure Patterns:** [Describe patterns with frequency data]
    - **Recurring Solutions:** [Group similar solutions with effectiveness notes]
    - **Time/Shift Trends:** [Note temporal patterns if any]
    - **Machine Type Vulnerabilities:** [Patterns by machine category]

    **Tone & Handling Uncertainty:**
    - Maintain a professional, confident, and helpful tone.
    - If the context does not contain enough information to answer the question fully, state the limitations clearly. Specify what you know based on the data and what remains uncertain. **Do not hallucinate or invent information.**

    ---
    **CONTEXT (Machine Breakdown Records):**
    {context}

    ---
    **USER'S QUESTION:**
    {question}

    ---
    **CONVERSATION HISTORY:**
    {history}

    ---
    **ASSISTANT'S RESPONSE:**
    """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        return (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
                "history": lambda _: "\n".join(self.conversation_history[-3:]) if self.conversation_history else "No history"
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
    
    def query(self, question: str) -> str:
        """Query the RAG system with a question and maintain conversation history"""
        try:
            rag_chain = self._get_rag_chain()
            response = rag_chain.invoke(question)
            
            # Update conversation history
            self.conversation_history.append(f"User: {question}")
            self.conversation_history.append(f"Assistant: {response}")
            
            # Keep history manageable
            if len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]
                
            return response
            
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            return f"I encountered an error while processing your request. Please try again. Error: {str(e)}"
    
    def process_image_with_text(self, image_data: str, text_query: Optional[str] = None) -> str:
        """
        Process an image with optional text query using Gemini's multimodal capabilities
        Focuses only on machine and mechanical related images with structured response
        """
        try:
            # Create a comprehensive prompt for image analysis with structured output
            image_prompt = """**Role:** You are an expert technical assistant for industrial machine maintenance and breakdown analysis.

        **Objective:** Analyze the provided industrial/machine image and provide comprehensive technical insights.

        **Instruction:** Structure your response strictly using the following Markdown sections. Use clear, concise, and professional language suitable for a technician.

        ### 🖼️ Data Identified in Image
        Provide detailed identification of visible components and systems:
        - **Machine Type:** [Identify the specific machine type]
        - **Key Components:** [List all identifiable mechanical, electrical, thermal components]
        - **System Classification:** [Mechanical/Electrical/Thermal/Automation/Software/Safety]

        ### ⚠️ Visible Issues & Potential Failures
        List all observable problems and potential failure modes:
        - **Mechanical Issues:** Wear patterns, corrosion, misalignment, vibration indicators
        - **Electrical Defects:** Burn marks, loose connections, insulation problems
        - **Thermal Anomalies:** Overheating signs, cooling system issues
        - **Safety Hazards:** Missing guards, exposed components, spillage risks
        - **Automation Problems:** Sensor misalignment, control system visible issues

        ### 🛠️ Recommended Actions
        Provide actionable recommendations in clear steps, start each section on a new line.:

        **Immediate Resolution:** (start each step on a new line)
        1. [First immediate action step]
        2. [Second immediate action step]
        3. [Third immediate action step]

        **Preventive Measures:** (start each step on a new line)
        1. [First preventive action]
        2. [Second preventive action]
        3. [Third preventive action]


        ### 🔧 Maintenance & Solution Plan
        Detailed maintenance and solution approach:

        **Short-term Solutions:**
        - [Solution 1 with specific steps]
        - [Solution 2 with specific steps]

        **Long-term Preventive Measures:**
        - [Preventive measure 1]
        - [Preventive measure 2]

        ### 📋 Safety & Compliance Considerations
        **Safety Protocols:**
        - [Required safety equipment and procedures]
        - [Emergency shutdown procedures if needed]
        - [Compliance standards applicable (OSHA, ISO, IEC)]

        **Risk Assessment:**
        - [Immediate risks identified]
        - [Potential long-term risks]

        ### ⚡ Technical Specifications & Requirements
        **Tools & Equipment Needed:**
        - [Required tools for maintenance]
        - [Specialized equipment if any]

        **Technical Parameters:**
        - [Recommended maintenance intervals]
        - [Performance benchmarks]

        **Focus Areas for Analysis:**
        - Mechanical Systems: Bearings, shafts, gears, couplings, belts, pumps, compressors, wear patterns
        - Electrical Systems: Motors, wiring, panels, PLCs, relays, drives, sensors, burn marks
        - Thermal Systems: Heat signatures, cooling systems, thermal expansion, energy efficiency
        - Process Automation: PLC/SCADA issues, sensor errors, process bottlenecks
        - Software & Control: Error indicators, firmware issues, network problems
        - Safety & Compliance: Missing guards, exposed wiring, compliance violations

        **Response Requirements:**
        - Use clear bullet points and numbered lists
        - Start each major point on a new line
        - Be specific and technical in recommendations
        - Include safety considerations in every section
        - If not a machine/mechanical component, politely decline analysis
        - Do not hallucinate information - only report what is visible
        """

            if text_query:
                image_prompt = f"USER QUERY: {text_query}\n\n{image_prompt}"

            # Create a multimodal message
            message = HumanMessage(
                content=[
                    {"type": "text", "text": image_prompt},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
            )

            # Use the LLM directly for image processing
            response = self.llm.invoke([message])

            # Update conversation history
            history_entry = f"User: [Image analysis request] {text_query if text_query else ''}"
            self.conversation_history.append(history_entry)
            self.conversation_history.append(f"Assistant: {response.content}")

            # Keep history manageable
            if len(self.conversation_history) > 6:
                self.conversation_history = self.conversation_history[-6:]

            return response.content

        except Exception as e:
            logger.error(f"Error in image processing: {str(e)}")
            return f"I encountered an error while processing the image. Please try again. Error: {str(e)}"

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["WWW-Authenticate"]
)

# Data models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    status: str = "success"

class ImageQueryResponse(BaseModel):
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

@app.post("/api/chat-with-image")
async def process_image_query(
    image: UploadFile = File(...),
    text_query: Optional[str] = Form(None),
    user: Dict = Depends(verify_user)
) -> ImageQueryResponse:
    """Process image query with optional text"""
    try:
        
        image_data = await image.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{image.content_type};base64,{base64_image}"
        
        # Process the image
        answer = rag_system.process_image_with_text(data_url, text_query)
        return ImageQueryResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error processing image query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)