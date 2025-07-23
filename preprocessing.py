import pandas as pd
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings 
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging
from typing import List, Any, Optional, Dict
from datetime import datetime
import pyodbc
from sqlalchemy import create_engine
import urllib.parse

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
            
            # Handle cases where date_str might already be a datetime object
            if isinstance(date_str, (pd.Timestamp, datetime)):
                datetime_obj = date_str
            # Handle cases where date_str might already contain time
            elif isinstance(date_str, str) and ' ' in date_str:
                datetime_obj = pd.to_datetime(date_str, errors='coerce')
            else:
                # Convert date and time separately
                date_part = pd.to_datetime(date_str, errors='coerce')
                if pd.isna(date_part):
                    return {'date': None, 'time': None, 'datetime': None}
                
                # If time_str is provided, combine with date
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
            f"The machine with Unique ID {row.get('Unique_ID_No', 'UNKNOWN')} has a Type ID of {row.get('Type_id', 'UNKNOWN')}.",
            f"The problem type is '{row.get('ProblemType', 'UNKNOWN')}', and it was repaired in Plant {row.get('PlantName', 'UNKNOWN')}, ",
            f"Shop {row.get('ShopName', 'UNKNOWN')}, Module {row.get('ModuleName', 'UNKNOWN')}, on the {row.get('LineName', 'UNKNOWN')} line.",
            f"The machine name is {row.get('MachineName', 'UNKNOWN')}, and the service type is {row.get('Servicetype', 'UNKNOWN')}.",
            f"The SAP machine code is {row.get('SapMachnCode', 'UNKNOWN')}."
        ]

        # Add time information if available
        if start_dt['datetime'] and end_dt['datetime']:
            text_parts.append(
                f"The repair started on {start_dt['datetime']} and ended on {end_dt['datetime']}, "
                f"resulting in a downtime of {row.get('Minutes', 0)} minutes ({row.get('Hours', 0)} hours)."
            )
        elif start_dt['datetime']:
            text_parts.append(
                f"The repair started on {start_dt['datetime']} with a downtime of {row.get('Minutes', 0)} minutes."
            )
        
        # Add problem and solution information
        text_parts.extend([
            f"The closure reason was {row.get('ClosureReason', 'UNKNOWN')}, and the solution was '{row.get('ActualReason', 'NO SOLUTION PROVIDED')}'.",
            f"The breakdown type is {row.get('Breakdowntype', 'UNKNOWN')}, and the SAP status is {row.get('SapStatus', 'UNKNOWN')}.",
            f"The subgroup is {row.get('SubGroup', 'UNKNOWN')}, and the phenomena was {row.get('Phenomena', 'UNKNOWN')}."
        ])

        # Add LOTO information
        loto = row.get('Loto', '')
        if loto:
            text_parts.append(f"The LOTO (Lock Out Tag Out) status was {loto}.")
        else:
            text_parts.append("No LOTO status was recorded.")

        # Add vendor/material information
        vendor = row.get('Vendor', '')
        material = row.get('Material', '')
        if vendor or material:
            text_parts.append(f"{'Vendor: ' + vendor if vendor else ''}{' and ' if vendor and material else ''}"
                            f"{'Material: ' + material if material else ''} was involved.")
        else:
            text_parts.append("No vendor or material was involved.")

        # Add problem reason and details
        text_parts.append(f"The problem was '{row.get('Reason', 'NO PROBLEM PROVIDED')}'.")
        details = row.get('details', '')
        if details:
            text_parts.append(f"Additional details: {details}")
        
        # Join all parts and clean up empty lines
        return " ".join(text_parts).replace(" .", ".").replace(" ,", ",")

    def load_data(self) -> pd.DataFrame:
        logger.info("🔄 Loading data from SQL Server...")
        try:
            # Using SQLAlchemy engine for pandas
            engine = self._get_sqlalchemy_engine()
            
            # Query to get all data from the table
            query = "SELECT * FROM MachineBreakdowns_1000"
            
            # Read data into DataFrame
            df = pd.read_sql(query, engine)
            
            # Clean text columns
            text_columns = ['MachineName', 'ProblemType', 'Reason', 'ActualReason', 'details',
                          'ShopName', 'ModuleName', 'LineName', 'Servicetype', 'ClosureReason',
                          'Breakdowntype', 'SubGroup', 'Phenomena', 'Loto', 'Vendor', 'Material']
            
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self._clean_text)

            # Fill missing values with appropriate defaults
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

            # Convert numeric fields
            df['Minutes'] = pd.to_numeric(df['Minutes'], errors='coerce').fillna(0).astype(int)
            df['Hours'] = pd.to_numeric(df['Hours'], errors='coerce').fillna(0).astype(float)

            return df

        except Exception as e:
            logger.error(f"Error loading data from SQL Server: {e}")
            raise

    def create_documents(self, df: pd.DataFrame) -> Dict[str, List[Document]]:
        """Create documents grouped by plant"""
        logger.info("📝 Creating documents...")
        
        df['PlantName'] = df['PlantName'].astype(str).str.replace('.0', '', regex=False)
        unique_plants = df['PlantName'].unique()
        logger.info(f"Unique plant values in data: {unique_plants}")
        
        documents = {
            'master': [],
            '1150': [],
            '1200': [],
            '1250': [],
            '1300': []
        }

        for _, row in df.iterrows():
            try:
                plant = str(row['PlantName']).strip()
                logger.debug(f"Processing plant: {plant} (type: {type(plant)})")
                
                machine_id = f"{row['MachineName']}_{row['SapMachnCode']}"
                human_readable_text = self._generate_human_readable_text(row)

                # Generate structured metadata text
                structured_text_parts = [
                    "MACHINE DETAILS:",
                    f"Name: {row['MachineName']}",
                    f"SAP Code: {row['SapMachnCode']}",
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

                # Filter out empty lines and sections
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
                    "machine_name": row['MachineName'],
                    "sap_code": str(row['SapMachnCode']),
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
                    "unique_id": str(row.get('Unique_id', '')),
                    "type_id": str(row.get('Type_id', '')),
                    "human_readable_text": human_readable_text,
                    "full_text": structured_text
                }

                # Clean metadata by removing empty or default values
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

                # Add to master collection
                documents['master'].append(doc)
                
                # Add to specific plant collection if plant is known
                if plant in ['1150', '1200', '1250', '1300']:
                    documents[plant].append(doc)
                    logger.debug(f"Added to plant {plant} collection")

            except Exception as e:
                logger.error(f"Error processing row {row.get('Unique_ID_No', 'UNKNOWN')}: {e}")
                continue

        # Log document counts for each collection
        plant_counts = {k: len(v) for k, v in documents.items()}
        logger.info(f"Document counts by plant: {plant_counts}")

        return documents

    def create_vector_stores(self, documents: Dict[str, List[Document]]):
        """Create vector stores for all collections"""
        logger.info("🧠 Creating vector stores...")

        # Initialize embeddings and client
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        client = QdrantClient(host="localhost", port=6333)
        
        # Vector configuration
        vector_config = models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        )

        # Create/update collections
        for collection_name, docs in documents.items():
            try:
                full_collection_name = self.collection_names[collection_name]
                
                # Check if collection exists
                existing_collections = client.get_collections()
                collection_exists = any(
                    col.name == full_collection_name 
                    for col in existing_collections.collections
                )
                
                if not collection_exists:
                    logger.info(f"Creating new collection: {full_collection_name}")
                    client.create_collection(
                        collection_name=full_collection_name,
                        vectors_config=vector_config
                    )
                
                logger.info(f"Updating collection: {full_collection_name} with {len(docs)} documents")
                
                # Create vector store and add documents
                vector_store = QdrantVectorStore(
                    client=client,
                    collection_name=full_collection_name,
                    embedding=embeddings
                )
                
                # Add documents (will update existing ones with same IDs)
                vector_store.add_documents(docs)
                
                logger.info(f"✅ Successfully updated {full_collection_name}")

            except Exception as e:
                logger.error(f"❌ Failed to update collection {collection_name}: {str(e)}", exc_info=True)
                continue

    def run(self):
        try:
            df = self.load_data()
            documents = self.create_documents(df)
            self.create_vector_stores(documents)
        except Exception as e:
            logger.error(f"💥 Error in processing: {str(e)}", exc_info=True)
            raise

# --- ENTRY POINT ---
if __name__ == "__main__":
    logger.info("🚀 Starting preprocessing pipeline")
    processor = DataProcessor()
    processor.run()