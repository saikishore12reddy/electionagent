import pandas as pd
import os
import json
import re

class ECIPreprocessor:
    def __init__(self, data_dir="data", output_dir="processed"):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.lookup_file = os.path.join(output_dir, "pc_lookup.json")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def build_lookup_table(self):
        """
        Build a master lookup table from Report 4 (List of Successful Candidates).
        Maps (State, PC_No) to PC_Name.
        """
        report_path = os.path.join(self.data_dir, "Report_4.xlsx")
        if not os.path.exists(report_path):
            print("Report 4 not found. Cannot build lookup table.")
            return None
            
        print("Building PC lookup table from Report 4...")
        try:
            # ECI legacy .xls reports often contain minor structural issues.
            # Explicitly opening via xlrd bypasses pandas version issues with engine_kwargs.
            import xlrd
            book = xlrd.open_workbook(report_path, ignore_workbook_corruption=True)
            df_preview = pd.read_excel(book, nrows=20)
            df_data = pd.read_excel(book)
            
            header_idx = 0
            for i, row in df_preview.iterrows():
                row_str = " ".join(str(v).upper() for v in row.values)
                # Look for header row explicitly using Const No or Constituency
                if "CONST NO" in row_str or "CONSTITUENCY" in row_str or "STATE" in row_str:
                    header_idx = i
                    break
            
            df = df_data.iloc[header_idx + 1:] # Skip header
            df.columns = df_data.iloc[header_idx].values # Assign proper headers
            
            # Identify columns mathematically to avoid whitespace issues
            state_col = None
            pc_no_col = None
            pc_name_col = None
            
            for col in df.columns:
                c_upper = str(col).upper()
                if "STATE" in c_upper: state_col = col
                elif "CONST NO" in c_upper or "PC NO" in c_upper: pc_no_col = col
                elif "CONSTITUENCY" in c_upper and "TYPE" not in c_upper: pc_name_col = col
            
            lookup = {}
            for _, row in df.iterrows():
                try:
                    state = str(row[state_col]).strip() if state_col else str(row.iloc[0]).strip()
                    pc_no = str(row[pc_no_col]).strip() if pc_no_col else str(row.iloc[1]).strip()
                    pc_name = str(row[pc_name_col]).strip() if pc_name_col else str(row.iloc[2]).strip()
                    
                    # Clean PC No (sometimes it has decimals like 1.0)
                    pc_no = re.sub(r'\.0$', '', pc_no)
                    
                    if state and pc_no and pc_name and pc_no.isdigit():
                        key = f"{state}_{pc_no}"
                        lookup[key] = {
                            "state": state,
                            "pc_no": pc_no,
                            "pc_name": pc_name
                        }
                        lookup[pc_name.lower()] = key
                except:
                    continue
            
            if lookup:
                with open(self.lookup_file, 'w') as f:
                    json.dump(lookup, f, indent=4)
                return lookup
            return None
        except Exception as e:
            print(f"Error building lookup table: {e}")
            return None

    def standardize_report(self, report_num):
        """
        Load a report, clean it, and return a DataFrame.
        """
        report_path = os.path.join(self.data_dir, f"Report_{report_num}.xlsx")
        if not os.path.exists(report_path):
            return None
            
        try:
            # Handle legacy XLS vs XLSX
            try:
                df_raw = pd.read_excel(report_path, nrows=30, engine='openpyxl')
            except Exception:
                import xlrd
                book = xlrd.open_workbook(report_path, ignore_workbook_corruption=True)
                df_raw = pd.read_excel(book, nrows=30)
            
            # Find the header row efficiently
            header_idx = -1
            header_rows = []
            for i, row in df_raw.iterrows():
                row_vals = [str(v).upper() for v in row.values if pd.notna(v)]
                row_str = " ".join(row_vals)
                if any(kw in row_str for kw in ['STATE', 'PC', 'CONSTITUENCY', 'PARTY', 'CANDIDATE', 'VOTERS', 'WON', 'TOTAL', 'ELECTORS']):
                    header_idx = i
                    # Sometimes headers are split across 2-3 rows. Let's capture them.
                    # If the next row also has keywords and fewer numbers, it's likely a sub-header
                    break
            
            if header_idx == -1:
                header_idx = 0

            # Re-read with merged headers if possible
            # We'll read 3 rows starting from header_idx to check for multi-row headers
            try:
                head_sample = pd.read_excel(report_path, skiprows=header_idx, nrows=3, header=None, engine='openpyxl')
            except Exception:
                book = xlrd.open_workbook(report_path, ignore_workbook_corruption=True)
                head_sample = pd.read_excel(book, skiprows=header_idx, nrows=3, header=None)
            
            # Merge the rows where the next row has high text-to-number ratio AND contains header keywords
            HEADER_KEYWORDS = {'STATE', 'PC', 'CONSTITUENCY', 'PARTY', 'CANDIDATE', 'VOTERS', 'WON', 'TOTAL', 'ELECTORS', 'MARGIN', 'GENDER', 'CATEGORY', 'NO.', 'NAME', 'SYMBOL', 'TYPE', 'VOTE', 'SECURED', 'RUNNER'}
            
            num_header_rows = 1
            for j in range(1, 3):
                row = head_sample.iloc[j]
                row_vals = [str(v).upper() for v in row.values if pd.notna(v)]
                
                # Check if this row contains any header keywords
                has_keywords = any(any(kw in val for kw in HEADER_KEYWORDS) for val in row_vals)
                
                text_count = sum(1 for v in row if isinstance(v, str) and len(v) > 1)
                num_count = sum(1 for v in row if isinstance(v, (int, float)) and pd.notna(v))
                
                # If it has keywords and isn't dominated by numbers, it's likely a header
                if has_keywords and text_count > (num_count + 1):
                    num_header_rows += 1
                else:
                    break
            
            # Final headers: combine the first few rows, ignoring "Unnamed" and "nan"
            final_cols = []
            for col_idx in range(len(head_sample.columns)):
                col_parts = []
                for row_idx in range(num_header_rows):
                    val = str(head_sample.iloc[row_idx, col_idx]).strip()
                    if val != "nan" and "Unnamed:" not in val and val not in col_parts:
                        col_parts.append(val)
                
                col_name = "_".join(col_parts).strip("_")
                if not col_name:
                    col_name = f"column_{col_idx}"
                final_cols.append(col_name)

            # Read data
            try:
                df = pd.read_excel(report_path, skiprows=header_idx + num_header_rows, header=None, engine='openpyxl')
            except Exception:
                book = xlrd.open_workbook(report_path, ignore_workbook_corruption=True)
                df = pd.read_excel(book, skiprows=header_idx + num_header_rows, header=None)
            
            df.columns = final_cols
            
            # Basic cleanup of headers: remove \n, strip whitespace, handle numbers
            df.columns = [str(h).replace('\n', ' ').strip() for h in df.columns]
            
            # Specific logic for messy reports
            if str(report_num) == "4": # Successful Candidates
                # Report 4 has winner and runner up on same line usually
                # We need to ensure columns like 'Margin' are numeric
                for col in df.columns:
                    if 'MARGIN' in col.upper():
                        df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if str(report_num) == "33": # Detailed Results
                # Ensure Votes are numeric
                for col in df.columns:
                    if any(kw in col.upper() for kw in ['VOTES', 'TOTAL']):
                        df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop rows where all elements are NaN
            df = df.dropna(how='all')
            
            # Save as CSV for backup/vector indexing
            processed_path = os.path.join(self.output_dir, f"Report_{report_num}.csv")
            df.to_csv(processed_path, index=False)
            
            return df
        except Exception as e:
            print(f"Error processing report {report_num}: {e}")
            return None

    def get_table_markdown(self, report_num):
        """
        Convert processed CSV to markdown for the LLM.
        """
        processed_path = os.path.join(self.output_dir, f"Report_{report_num}.csv")
        if os.path.exists(processed_path):
            df = pd.read_csv(processed_path)
            return df.head(100).to_markdown(index=False)
        return ""

if __name__ == "__main__":
    prep = ECIPreprocessor()
    # df = prep.standardize_report("4")
    # print(df.head() if df is not None else "Failed")
