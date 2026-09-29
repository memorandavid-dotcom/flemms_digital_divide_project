import os

def save_to_parquet(df, output_path):
    """
    Saves the dataframe to Apache Parquet format.
    Requires 'pyarrow' installed in your requirements.txt.
    """
    # Ensure the final directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Saving Analytical Base Table to {output_path}...")
    df.to_parquet(output_path, index=False, engine='pyarrow')
    print("Save complete!")