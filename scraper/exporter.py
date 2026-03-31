import pandas as pd
import json
import os

class DataExporter:
    def __init__(self):
        self.export_dir = 'exports'
        os.makedirs(self.export_dir, exist_ok=True)
    
    def to_csv(self, data, job_id):
        df = pd.DataFrame(data)
        filepath = f"{self.export_dir}/{job_id[:8]}.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath
    
    def to_excel(self, data, job_id):
        df = pd.DataFrame(data)
        filepath = f"{self.export_dir}/{job_id[:8]}.xlsx"
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Businesses', index=False)
            
            # Auto-size columns
            worksheet = writer.sheets['Businesses']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return filepath
    
    def to_json(self, data, job_id):
        filepath = f"{self.export_dir}/{job_id[:8]}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
