import os
from src.extract import load_latest_data
from src.transform import harmonize_and_merge
from src.load import save_to_parquet

def run_pipeline():
    print("=== Starting FLEMMS ETL Pipeline ===")
    
    # Define relative paths
    processed_dir = os.path.join("data", "processed")
    final_output = os.path.join("data", "final", "flemms_analytical_base_table.parquet")
    
    try:
        # 1. Extract
        print("\n--- Phase 1: Extraction ---")
        hh_df = load_latest_data(processed_dir, "households", "2024")
        ind_df = load_latest_data(processed_dir, "individuals", "2024")
        
        # 2. Transform
        print("\n--- Phase 2: Transformation ---")
        final_df = harmonize_and_merge(hh_df, ind_df)
        
        print(f"Transformed Dataset Shape: {final_df.shape}")
        
        # 3. Load
        print("\n--- Phase 3: Load ---")
        save_to_parquet(final_df, final_output)
        
        print("\n=== Pipeline Finished Successfully ===")
        
    except Exception as e:
        print(f"\nPipeline Failed: {e}")

if __name__ == "__main__":
    run_pipeline()