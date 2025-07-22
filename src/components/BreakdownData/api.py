from fastapi import FastAPI, HTTPException
import pyodbc
from typing import List, Optional , Union
from datetime import datetime, time
from pydantic import BaseModel , validator
from typing import Optional, Union
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatabaseConfig:
    def __init__(self):
        self.server = 'JEY_JARVIS'
        self.drivers = [
            '{ODBC Driver 17 for SQL Server}',
            '{SQL Server Native Client 11.0}',
            '{SQL Server}'  # Fallback to older drivers if needed
        ]
    
    def get_connection(self, database_name):
        for driver in self.drivers:
            try:
                conn_str = f'DRIVER={driver};SERVER={self.server};DATABASE={database_name};Trusted_Connection=yes;'
                return pyodbc.connect(conn_str)
            except pyodbc.Error:
                continue
        raise Exception("Could not connect with any available driver")

db_config = DatabaseConfig()

def get_db_connection(plant: str):
    database_mapping = {
        'master': 'MachineBreakdownDB',
        '1150': 'MachineBreakdown_1150',
        '1200': 'MachineBreakdown_1200',
        '1250': 'MachineBreakdown_1250',
        '1300': 'MachineBreakdown_1300'
    }
    database_name = database_mapping.get(plant, 'MachineBreakdownDB')
    return db_config.get_connection(database_name)

class BreakdownRecord(BaseModel):
    Unique_ID_No: Union[str, int, float]
    Type_id: Optional[Union[str, int, float]] = None
    ProblemType: Optional[str] = None
    PlantName: Optional[Union[str, int]] = None
    ShopName: Optional[str] = None
    ModuleName: Optional[str] = None
    LineName: Optional[str] = None
    MachineName: Optional[str] = None
    Servicetype: Optional[str] = None
    SapMachnCode: Optional[Union[str, int, float]] = None
    ShiftName: Optional[str] = None
    StartDate: Optional[Union[str, datetime]] = None
    StartTime: Optional[Union[str, time]] = None
    EndDate: Optional[Union[str, datetime]] = None
    EndTime: Optional[Union[str, time]] = None
    Minutes: Optional[int] = 0  # Default to 0 instead of None
    Hours: Optional[int] = 0    # Default to 0 instead of None
    ClosureReason: Optional[str] = None
    ActualReason: Optional[str] = None
    Breakdowntype: Optional[str] = None
    SapStatus: Optional[str] = None
    SubGroup: Optional[str] = None
    Phenomena: Optional[str] = None
    Loto: Optional[str] = None
    Vendor: Optional[str] = None
    Material: Optional[str] = None
    Reason: Optional[str] = None
    details: Optional[str] = None

    @validator('Minutes', 'Hours', pre=True)
    def empty_str_to_zero(cls, v):
        if v == '' or v is None:
            return 0
        return int(v)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            time: lambda v: v.isoformat() if v else None
        }

@app.get("/api/breakdown-data/", response_model=List[BreakdownRecord])
@app.get("/api/breakdown-data/{plant}", response_model=List[BreakdownRecord])
async def get_breakdown_data(plant: str = None):
    try:
        conn = get_db_connection(plant)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            Unique_ID_No, Type_id, ProblemType, PlantName, ShopName, 
            ModuleName, LineName, MachineName, Servicetype, SapMachnCode,
            ShiftName, StartDate, StartTime, EndDate, EndTime, Minutes, 
            Hours, ClosureReason, ActualReason, Breakdowntype, SapStatus,
            SubGroup, Phenomena, Loto, Vendor, Material, Reason, details
        FROM MachineBreakdowns
        ORDER BY StartDate DESC
        """
        
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            row_dict = {}
            for col, val in zip(columns, row):
                # Handle NULL values first
                if val is None:
                    row_dict[col] = "" if col not in ['Minutes', 'Hours'] else 0
                    continue
                
                # Special handling for numeric fields
                if col in ['Minutes', 'Hours']:
                    row_dict[col] = int(val) if val is not None else 0
                # Convert datetime to ISO format string
                elif isinstance(val, datetime):
                    row_dict[col] = val.isoformat()
                # Convert time to string
                elif isinstance(val, time):
                    row_dict[col] = val.strftime('%H:%M:%S')
                # Convert numeric IDs to strings
                elif col in ['Unique_ID_No', 'Type_id', 'PlantName', 'SapMachnCode']:
                    row_dict[col] = str(int(val)) if val is not None else ""
                # Convert all other values to string
                else:
                    row_dict[col] = str(val) if val is not None else ""
            
            results.append(row_dict)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)