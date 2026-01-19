import lancedb
import pandas as pd
from pathlib import Path

# --- Configuration ---
# Set pandas display options to show all content without truncation
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 80)

# --- Database Connection ---
# This path assumes the script is run from the project root,
# which is the default for Railway's execution environment.
db_path = Path.cwd() / "data" / "lancedb"
table_name = "documents"

print(f"--- Inspecting LanceDB at: {db_path} ---\n")

try:
    db = lancedb.connect(db_path)
    table_names = db.table_names()

    if not table_names:
        print("❌ Error: No tables found in the database on the persistent volume.")
        print("Please ensure the ingestion process has been run in the deployed environment.")
        exit()

    print(f"Tables found: {table_names}\n")

    table = db.open_table(table_name)
    print("✅ Successfully opened table.\n")

    # --- Schema Inspection ---
    print("--- Table Schema ---")
    print(table.schema)
    print("\n")

    # --- Data Inspection ---
    print(f"--- First 5 Records in '{table_name}' ---")
    df = table.to_pandas(limit=5)
    if "embedding" in df.columns:
        df = df.drop(columns=["embedding"])
        
    print(df)
    print("\n")

except Exception as e:
    print(f"❌ An error occurred: {e}")