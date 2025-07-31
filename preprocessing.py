import pandas as pd
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings 
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
import logging
from typing import List, Any, Optional, Dict, Tuple
from datetime import datetime
import pyodbc
from sqlalchemy import create_engine
import urllib.parse
import os
import time
import uuid
from tqdm import tqdm
import csv
import psutil
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, base_path: str = None):
        # SQL Server connection parameters
        self.server = 'JEY_JARVIS'
        self.database = 'MachineBreakdownDB'
        self.driver = '{ODBC Driver 17 for SQL Server}'
        self.collection_names = {
            'master': 'machine_data_master',
            '1150': 'machine_data_1150',
            '1200': 'machine_data_1200',
            '1250': 'machine_data_1250',
            '1300': 'machine_data_1300'
        }
        self.progress_file = 'vectorization_progress.csv'
        self.max_retries = 5  # Increased retries
        self.retry_delay = 10  # Increased delay
        self.batch_size = 50  # Reduced batch size
        self.max_memory_usage = 0.85  # 85% memory threshold
        
    def _initialize_progress_log(self):
        """Initialize or load progress tracking file with headers"""
        if not os.path.exists(self.progress_file):
            with open(self.progress_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Unique_ID_No', 'Collection', 'Processed', 'Timestamp'])

    def _log_processed_id(self, unique_id: str, collection: str):
        """Log successfully processed IDs with collection info"""
        with open(self.progress_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([unique_id, collection, True, datetime.now().isoformat()])

    def _get_processed_ids(self) -> Dict[str, set]:
        """Get dictionary of processed IDs for each collection"""
        processed = defaultdict(set)
        
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['Processed'].lower() == 'true':
                            unique_id = row['Unique_ID_No']
                            collection = row['Collection']
                            processed[collection].add(unique_id)
            except Exception as e:
                logger.warning(f"Error reading progress file: {e}")
        return processed
        
    def _get_sql_connection(self):
        """Establish connection to SQL Server using Windows Authentication"""
        try:
            conn_str = (
                f'DRIVER={self.driver};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                'Trusted_Connection=yes;'
            )
            conn = pyodbc.connect(conn_str)
            return conn
        except Exception as e:
            logger.error(f"Error connecting to SQL Server: {e}")
            raise

    def _get_sqlalchemy_engine(self):
        """Create SQLAlchemy engine for pandas using Windows Authentication"""
        try:
            params = urllib.parse.quote_plus(
                f'DRIVER={self.driver};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                'Trusted_Connection=yes;'
            )
            engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
            return engine
        except Exception as e:
            logger.error(f"Error creating SQLAlchemy engine: {e}")
            raise

    def _clean_text(self, text: Any) -> str:
        """Clean and standardize text values"""
        if pd.isna(text) or str(text).strip().upper() in ['NULL', 'NAN', 'NONE', '']:
            return ""
        return str(text).strip()

    def _format_datetime(self, date_str: Any, time_str: Any) -> Dict[str, Optional[str]]:
        """Parse and format datetime into separate date and time components"""
        try:
            if pd.isna(date_str) or str(date_str).strip() == '':
                return {'date': None, 'time': None, 'datetime': None}
            
            if isinstance(date_str, (pd.Timestamp, datetime)):
                datetime_obj = date_str
            elif isinstance(date_str, str) and ' ' in date_str:
                datetime_obj = pd.to_datetime(date_str, errors='coerce')
            else:
                date_part = pd.to_datetime(date_str, errors='coerce')
                if pd.isna(date_part):
                    return {'date': None, 'time': None, 'datetime': None}
                
                if not pd.isna(time_str) and str(time_str).strip() != '':
                    if isinstance(time_str, str):
                        time_part = pd.to_datetime(time_str, errors='coerce').time()
                        datetime_obj = datetime.combine(date_part.date(), time_part)
                    else:
                        datetime_obj = date_part
                else:
                    datetime_obj = date_part
            
            if pd.isna(datetime_obj):
                return {'date': None, 'time': None, 'datetime': None}
            
            return {
                'date': datetime_obj.strftime('%d-%m-%Y'),
                'time': datetime_obj.strftime('%H:%M:%S'),
                'datetime': datetime_obj.strftime('%d-%m-%Y %H:%M:%S')
            }
        except Exception as e:
            logger.warning(f"Could not parse datetime: {e}")
            return {'date': None, 'time': None, 'datetime': None}

    def _generate_human_readable_text(self, row: Dict) -> str:
        """Generate the human-readable descriptive text"""
        start_dt = self._format_datetime(row['StartTime'], row['StartTime'])
        end_dt = self._format_datetime(row['EndDate'], row['EndTime'])
        
        text_parts = [
            f"The machine with Unique ID {row.get('Unique_ID_No', 'UNKNOWN')} had been analyzed.",
            f"The problem type is '{row.get('ProblemType', 'UNKNOWN')}', and it was repaired in Plant {row.get('PlantName', 'UNKNOWN')}, ",
            f"Shop {row.get('ShopName', 'UNKNOWN')}, Module {row.get('ModuleName', 'UNKNOWN')}, on the {row.get('LineName', 'UNKNOWN')} line.",
            f"The machine name is {row.get('MachineName', 'UNKNOWN')}, and the service type is {row.get('Servicetype', 'UNKNOWN')}.",
            f"The SAP machine code is {row.get('SapMachnCode', 'UNKNOWN')}."
        ]

        if start_dt['datetime'] and end_dt['datetime']:
            text_parts.append(
                f"The repair started on {start_dt['datetime']} and ended on {end_dt['datetime']}, "
                f"resulting in a downtime of {row.get('Minutes', 0)} minutes ({row.get('Hours', 0)} hours)."
            )
        elif start_dt['datetime']:
            text_parts.append(
                f"The repair started on {start_dt['datetime']} with a downtime of {row.get('Minutes', 0)} minutes."
            )
        
        text_parts.extend([
            f"The closure reason was {row.get('ClosureReason', 'UNKNOWN')}, and the solution was '{row.get('ActualReason', 'NO SOLUTION PROVIDED')}'.",
            f"The breakdown type is {row.get('Breakdowntype', 'UNKNOWN')}, and the SAP status is {row.get('SapStatus', 'UNKNOWN')}.",
            f"The subgroup is {row.get('SubGroup', 'UNKNOWN')}, and the phenomena was {row.get('Phenomena', 'UNKNOWN')}."
        ])

        loto = row.get('Loto', '')
        if loto:
            text_parts.append(f"The LOTO (Lock Out Tag Out) status was {loto}.")
        else:
            text_parts.append("No LOTO status was recorded.")

        vendor = row.get('Vendor', '')
        material = row.get('Material', '')
        if vendor or material:
            text_parts.append(f"{'Vendor: ' + vendor if vendor else ''}{' and ' if vendor and material else ''}"
                            f"{'Material: ' + material if material else ''} was involved.")
        else:
            text_parts.append("No vendor or material was involved.")

        text_parts.append(f"The problem was '{row.get('Reason', 'NO PROBLEM PROVIDED')}'.")
        details = row.get('details', '')
        if details:
            text_parts.append(f"Additional details: {details}")
        
        return " ".join(text_parts).replace(" .", ".").replace(" ,", ",")

    def _check_system_resources(self):
        """Check if system has enough resources to continue processing"""
        mem = psutil.virtual_memory()
        if mem.percent > self.max_memory_usage * 100:
            logger.warning(f"High memory usage detected: {mem.percent}%")
            return False
        return True

    def _wait_for_resources(self):
        """Wait until system resources are available"""
        while not self._check_system_resources():
            logger.info(f"Waiting for resources... (current memory: {psutil.virtual_memory().percent}%)")
            time.sleep(30)

    def _retry_operation(self, operation, *args, **kwargs):
        """Retry operation with exponential backoff and resource checks"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._wait_for_resources()
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (attempt + 1)
                logger.warning(f"Attempt {attempt + 1} failed. Retrying in {wait_time} seconds... Error: {str(e)}")
                time.sleep(wait_time)
        raise last_error

    def load_data(self) -> pd.DataFrame:
        logger.info("🔄 Loading data from SQL Server...")
        try:
            engine = self._get_sqlalchemy_engine()
            query = "SELECT * FROM machine_reports"
            df = pd.read_sql(query, engine)
            
            text_columns = ['MachineName', 'ProblemType', 'Reason', 'ActualReason', 'details',
                          'ShopName', 'ModuleName', 'LineName', 'Servicetype', 'ClosureReason',
                          'Breakdowntype', 'SubGroup', 'Phenomena', 'Loto', 'Vendor', 'Material']
            
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self._clean_text)

            df = df.fillna({
                'SapMachnCode': 'UNKNOWN',
                'MachineName': 'UNKNOWN_MACHINE',
                'details': '',
                'ActualReason': 'NO SOLUTION PROVIDED',
                'Reason': 'NO PROBLEM PROVIDED',
                'Minutes': 0,
                'Hours': 0,
                'ProblemType': 'UNKNOWN',
                'ClosureReason': 'UNKNOWN',
                'Vendor': '',
                'Material': '',
                'Loto': '',
                'StartTime': '',
                'EndTime': ''
            })

            df['Minutes'] = pd.to_numeric(df['Minutes'], errors='coerce').fillna(0).astype(int)
            df['Hours'] = pd.to_numeric(df['Hours'], errors='coerce').fillna(0).astype(float)

            return df

        except Exception as e:
            logger.error(f"Error loading data from SQL Server: {e}")
            raise

    def create_documents(self, df: pd.DataFrame) -> Dict[str, List[Document]]:
        """Create documents grouped by plant with precise tracking"""
        logger.info("📝 Creating documents...")
        
        df['PlantName'] = df['PlantName'].astype(str).str.replace('.0', '', regex=False)
        unique_plants = df['PlantName'].unique()
        logger.info(f"Unique plant values in data: {unique_plants}")
        
        documents = defaultdict(list)
        processed_ids = self._get_processed_ids()
        new_documents_count = 0

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing rows"):
            try:
                unique_id = str(row.get('Unique_ID_No', ''))
                if not unique_id:
                    continue
                
                plant = str(row['PlantName']).strip()
                machine_name = row.get('MachineName', 'UNKNOWN_MACHINE')
                sap_code = row.get('SapMachnCode', 'UNKNOWN')
                machine_id = f"{machine_name}_{sap_code}"
                
                needs_master = unique_id not in processed_ids['master']
                needs_plant = (plant in ['1150', '1200', '1250', '1300'] and 
                            unique_id not in processed_ids[plant])
                
                if not needs_master and not needs_plant:
                    continue
                    
                human_readable_text = self._generate_human_readable_text(row)

                structured_text_parts = [
                    "MACHINE DETAILS:",
                    f"Name: {machine_name}",
                    f"SAP Code: {sap_code}",
                    f"Plant: {row.get('PlantName', 'UNKNOWN')}",
                    f"Shop: {row['ShopName']}",
                    f"Module: {row['ModuleName']}",
                    f"Line: {row['LineName']}",
                    f"Sub Group: {row['SubGroup']}",
                    "",
                    "BREAKDOWN DETAILS:",
                    f"Problem Type: {row['ProblemType']}",
                    f"Service Type: {row['Servicetype']}",
                    f"Start Time: {self._format_datetime(row['StartTime'], row['StartTime'])['datetime'] or 'UNKNOWN'}",
                    f"End Time: {self._format_datetime(row['EndDate'], row['EndTime'])['datetime'] or 'UNKNOWN'}",
                    f"Duration: {row['Minutes']} minutes ({row['Hours']} hours)",
                    "",
                    "ISSUE DETAILS:",
                    f"Problem: {row['Reason']}",
                    f"Solution: {row['ActualReason']}",
                    f"Phenomena: {row['Phenomena']}",
                    f"Details: {row['details']}",
                    "",
                    "STATUS INFORMATION:",
                    f"Closure Reason: {row['ClosureReason']}",
                    f"Breakdown Type: {row['Breakdowntype']}",
                    f"SAP Status: {row.get('SapStatus', 'UNKNOWN')}",
                    f"LOTO: {row['Loto']}",
                    "",
                    "ADDITIONAL INFO:",
                    f"Vendor: {row['Vendor']}",
                    f"Material: {row['Material']}"
                ]

                structured_text = "\n".join(
                    part for part in structured_text_parts 
                    if not (part.endswith(": ") or 
                        (part.endswith(":") and len(part.split(':')) == 1 or
                        part.endswith(": UNKNOWN") or
                        part.endswith(": NO DETAILS PROVIDED") or
                        part.endswith(": NO SOLUTION PROVIDED"))
                ))

                metadata = {
                    "machine_id": machine_id,
                    "machine_name": machine_name,
                    "sap_code": sap_code,
                    "plant": str(row.get('PlantName', 'UNKNOWN')),
                    "shop": row['ShopName'],
                    "module": row['ModuleName'],
                    "line": row['LineName'],
                    "problem_type": row['ProblemType'],
                    "service_type": row['Servicetype'],
                    "shift": row['ShiftName'],
                    "duration_minutes": int(row['Minutes']),
                    "duration_hours": float(row['Hours']),
                    "start_time": self._format_datetime(row['StartDate'], row['StartTime'])['datetime'],
                    "end_time": self._format_datetime(row['EndDate'], row['EndTime'])['datetime'],
                    "problem": row['Reason'],
                    "solution": row['ActualReason'],
                    "details": row['details'],
                    "closure_reason": row['ClosureReason'],
                    "breakdown_type": row['Breakdowntype'],
                    "sap_status": row.get('SapStatus', 'UNKNOWN'),
                    "sub_group": row['SubGroup'],
                    "phenomena": row['Phenomena'],
                    "loto": row['Loto'],
                    "vendor": row['Vendor'],
                    "material": row['Material'],
                    "unique_id": unique_id,
                    "human_readable_text": human_readable_text,
                    "full_text": structured_text
                }

                metadata = {
                    k: v for k, v in metadata.items()
                    if v not in ['', 'UNKNOWN', 'NO DETAILS PROVIDED',
                            'NO SOLUTION PROVIDED', 'NO PROBLEM PROVIDED',
                            'NAN', 'NULL', 'NONE'] and v is not None
                }

                doc = Document(
                    page_content=human_readable_text,
                    metadata=metadata
                )

                if needs_master:
                    documents['master'].append(doc)
                    new_documents_count += 1
                
                if needs_plant:
                    documents[plant].append(doc)
                    new_documents_count += 1

            except Exception as e:
                logger.error(f"Error processing row {row.get('Unique_ID_No', 'UNKNOWN')}: {e}")
                continue

        plant_counts = {k: len(v) for k, v in documents.items()}
        logger.info(f"New documents to process by plant: {plant_counts}")
        logger.info(f"Total new documents to process: {new_documents_count}")

        return documents
    
    def _initialize_qdrant_collection(self, client: QdrantClient, collection_name: str, vector_size: int):
        """Initialize Qdrant collection with optimized settings"""
        try:
            # First check if collection exists
            try:
                client.get_collection(collection_name)
                client.delete_collection(collection_name)
            except Exception:
                pass  # Collection doesn't exist

            vector_config = models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
                on_disk=True
            )

            # Create new collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_config,
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,
                    memmap_threshold=10000,
                    max_segment_size=50000,
                    default_segment_number=2
                ),
                shard_number=2
            )
            
            logger.info(f"Created collection {collection_name} with optimized settings")
        except Exception as e:
            logger.error(f"Error initializing collection {collection_name}: {e}")
            raise

    def create_vector_stores(self, documents: Dict[str, List[Document]]):
        """Create vector stores with optimized batch processing"""
        logger.info("🧠 Creating vector stores...")

        # Initialize embeddings and client
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        client = QdrantClient(
            host="localhost",
            port=6333,
            prefer_grpc=True,
            timeout=120
        )

        # First get embedding dimension
        sample_embedding = embeddings.embed_query("test")
        vector_size = len(sample_embedding)

        for collection_name, docs in documents.items():
            if not docs:
                continue
                
            try:
                full_collection_name = self.collection_names[collection_name]
                self._initialize_qdrant_collection(client, full_collection_name, vector_size)
                
                # Process documents in optimized batches
                for i in tqdm(range(0, len(docs), self.batch_size), 
                            desc=f"Processing {full_collection_name}"):
                    batch = docs[i:i + self.batch_size]
                    
                    try:
                        # Generate embeddings for the batch
                        texts = [doc.page_content for doc in batch]
                        embeddings_list = self._retry_operation(
                            embeddings.embed_documents,
                            texts
                        )
                        
                        # Create points with unique IDs
                        points = [
                            models.PointStruct(
                                id=str(uuid.uuid4()),  # Generate proper UUIDs
                                vector=embeddings_list[j],
                                payload=doc.metadata
                            )
                            for j, doc in enumerate(batch)
                        ]
                        
                        # Upload with retry
                        self._retry_operation(
                            client.upsert,
                            collection_name=full_collection_name,
                            points=points,
                            wait=True
                        )
                        
                        # Log successful processing
                        for doc in batch:
                            unique_id = doc.metadata.get('unique_id')
                            if unique_id:
                                self._log_processed_id(unique_id, collection_name)
                        
                        # Small delay between batches
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Failed to process batch starting at {i} for {full_collection_name}: {e}")
                        continue
                
                logger.info(f"✅ Successfully updated {full_collection_name}")

            except Exception as e:
                logger.error(f"❌ Failed to update collection {collection_name}: {str(e)}", exc_info=True)
                continue

    def run(self):
        try:
            self._initialize_progress_log()
            df = self.load_data()
            documents = self.create_documents(df)
            self.create_vector_stores(documents)
            logger.info("🚀 Vectorization process completed successfully")
        except Exception as e:
            logger.error(f"💥 Error in processing: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    logger.info("🚀 Starting preprocessing pipeline")
    processor = DataProcessor()
    processor.run()