import pyodbc

class MachineBreakdownDB:
    def __init__(self):
        self.server = 'JEY_JARVIS'
        self.database = 'MachineBreakdownDB'
        self.driver = '{ODBC Driver 17 for SQL Server}'
        self.conn_str = f'DRIVER={self.driver};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;'
    
    def create_plant_tables(self):
        try:
            # Connect to the database using Windows Authentication
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            
            print("Connected to SQL Server successfully.")
            
            # List of plant names to create tables for
            plant_names = ['1150', '1200', '1250', '1300']
            
            for plant in plant_names:
                table_name = f'MachineBreakdowns_{plant}'
                
                # Check if table exists, drop if it does
                cursor.execute(f"""
                    IF OBJECT_ID('{table_name}', 'U') IS NOT NULL
                    DROP TABLE {table_name};
                """)
                
                # Create new table with the same structure as original
                cursor.execute(f"""
                    SELECT * INTO {table_name} 
                    FROM MachineBreakdowns 
                    WHERE 1 = 0;  -- Creates structure without data
                """)
                
                # Copy data for this specific plant
                cursor.execute(f"""
                    INSERT INTO {table_name}
                    SELECT * FROM MachineBreakdowns 
                    WHERE PlantName = '{plant}';
                """)
                
                # Get row count for verification
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                row_count = cursor.fetchone()[0]
                
                print(f"Created table {table_name} with {row_count} rows.")
            
            # Commit the changes
            conn.commit()
            print("All tables created and populated successfully.")
            
        except Exception as e:
            print(f"Error occurred: {e}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
            print("Connection closed.")

# Execute the function
db = MachineBreakdownDB()
db.create_plant_tables()