import pandas as pd
import os
import glob

def load_latest_data(processed_dir, category, year_keyword="2024"):
    """
    Finds and loads the latest dataset for a given category (households or individuals).
    """
    folder_path = os.path.join(processed_dir, category)
    search_pattern = os.path.join(folder_path, f"*{year_keyword}*.csv")
    
    # glob.glob finds files matching the pattern
    files = glob.glob(search_pattern)
    
    if not files:
        raise FileNotFoundError(f"No {year_keyword} files found in {folder_path}")
    
    # Grab the first matched file
    file_path = files[0]
    print(f"Extracting: {os.path.basename(file_path)}")
    
    # low_memory=False prevents mixed-type inference warnings on large files
    return pd.read_csv(file_path, low_memory=False)