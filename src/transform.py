import pandas as pd

def clean_headers(df):
    """Standardizes column names to lower_snake_case."""
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    return df

def remove_duplicates_and_empty(df):
    """Removes exact duplicate rows and completely empty columns."""
    df = df.drop_duplicates()
    df = df.dropna(axis=1, how='all')
    return df

def harmonize_and_merge(hh_df, ind_df):
    """
    Cleans, maps variables, and merges household and individual datasets.
    """
    # 1. Clean both dataframes
    hh_df = remove_duplicates_and_empty(clean_headers(hh_df))
    ind_df = remove_duplicates_and_empty(clean_headers(ind_df))

    # 2. Schema Standardization (Mapping)
    # NOTE: You will need to update the strings on the left with the exact 
    # column names outputted during your EDA phase.
    col_mapping = {
        'regn': 'region',
        'prov': 'province',
        'age_col_name': 'age',
        'highest_educ_col': 'educational_attainment',
        'literacy_col': 'functional_literacy'
    }
    ind_df = ind_df.rename(columns=col_mapping)

    # 3. Join the tables
    # Find common geographical and serial number columns to link a person to their house
    possible_keys = ['region', 'province', 'mun', 'bgy', 'hsn', 'w_id']
    join_keys = [col for col in possible_keys if col in hh_df.columns and col in ind_df.columns]
    
    if not join_keys:
        print("Warning: Common ID keys not found. Ensure column mapping aligns.")
        return ind_df # Failsafe: return unmerged individuals if keys mismatch

    print(f"Merging datasets on keys: {join_keys}")
    merged_df = pd.merge(ind_df, hh_df, on=join_keys, how='left')
    
    # 4. Feature Engineering Placeholders for downstream modeling
    merged_df['digital_access_score'] = 0 # Replace with logic summing internet/device flags
    merged_df['literacy_tier'] = 'Unknown' # Replace with logic grouping literacy scores
    
    return merged_df