import pandas as pd
from datetime import datetime, date, time
from config import Config

class DataPreprocessor:
    def __init__(self, data_path):
        self.data_path = data_path
        self.df = self.load_data()
    
    def load_data(self):
        """Load data from Excel file"""
        return pd.read_excel(self.data_path)
    
    def create_document_text(self, row):
        """Create a standardized text representation for each record"""
        doc = f"""
        MACHINE DETAILS:
        Unique ID: {row['Unique_id']}
        Type ID: {row['Type_id']}
        Problem Type: {row['ProblemType']}
        Plant: {row['PlantName']} ({row['ShopName']})
        Module: {row['ModuleName']}
        Line: {row['LineName']}
        Machine: {row['MachineName']}
        Service Type: {row['Servicetype']}
        SAP Code: {row['SapMachnCode']}
        Shift: {row['ShiftName']}
        
        BREAKDOWN DETAILS:
        Start: {row['StartDate']} {row['StartTime']}
        End: {row['EndDate']} {row['EndTime']}
        Duration: {row['Minutes']} minutes ({row['Hours']} hours)
        
        ISSUE DETAILS:
        Problem: {row['Reason']}
        Closure Reason: {row['ClosureReason']}
        Actual Reason: {row['ActualReason']}
        Breakdown Type: {row['Breakdowntype']}
        Solution: {row['details']}
        
        STATUS INFORMATION:
        SAP Status: {row['SapStatus']}
        SubGroup: {row['SubGroup']}
        Phenomena: {row['Phenomena']}
        LOTO: {row['Loto']}
        """
        return doc.strip()
    
    def _sanitize_metadata(self, metadata):
        sanitized = {}
        for k, v in metadata.items():
            if isinstance(v, (pd.Timestamp, datetime, pd.Timedelta)):
                sanitized[k] = str(v)
            elif isinstance(v, (pd._libs.tslibs.nattype.NaTType, type(pd.NaT))):
                sanitized[k] = None
            elif isinstance(v, (date, time)):  # ✅ FIXED
                sanitized[k] = str(v)
            else:
                sanitized[k] = v if isinstance(v, (str, int, float, bool, type(None))) else str(v)
        return sanitized




    def prepare_documents(self):
        """Prepare documents for vector database"""
        documents = [self.create_document_text(row) for _, row in self.df.iterrows()]
        ids = [str(row['Unique_id']) for _, row in self.df.iterrows()]
        raw_metadatas = [row.to_dict() for _, row in self.df.iterrows()]
        metadatas = [self._sanitize_metadata(meta) for meta in raw_metadatas]
        
        return documents, ids, metadatas

if __name__ == "__main__":
    preprocessor = DataPreprocessor(Config.DATA_PATH)
    documents, ids, metadatas = preprocessor.prepare_documents()
    print(f"Prepared {len(documents)} documents")
