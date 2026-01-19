import lancedb
import pandas as pd
import pyarrow as pa
import random
import os
import tempfile
import json

# --- Configuration ---
# Set pandas display options to show all content without truncation
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 80)

# --- In-Memory Database Setup ---
# Create a temporary directory for our in-memory DB
temp_dir = tempfile.mkdtemp()
uri = temp_dir
db = lancedb.connect(uri)
table_name = "documents"

print(f"--- Creating a temporary, in-memory LanceDB table for demonstration ---")
print(f"--- Table Name: {table_name} ---\n")

# --- Sample Data ---
# This data simulates what the Ingestion and Memory agents would create
sample_data = [
    {
        "chunk_id": "doc1-chunk001",
        "content": "The ROMA Orchestrator is the heart of the system. It manages the entire workflow and delegates tasks to other agents.",
        "embedding": [random.random() for _ in range(384)],
        "source_id": "ARCHITECTURE.md",
        "source_url": "file://ARCHITECTURE.md",
        "metadata": json.dumps({"type": "markdown", "author": "AI"}),
    },
    {
        "chunk_id": "doc2-chunk005",
        "content": "LanceDB is a serverless vector database that runs directly inside the application process, storing data as files.",
        "embedding": [random.random() for _ in range(384)],
        "source_id": "01_DESIGN_DOC.md",
        "source_url": "file://docs/01_DESIGN_DOC.md",
        "metadata": json.dumps({"type": "markdown", "author": "System Architect"}),
    },
]

# --- Schema Definition ---
# This schema matches the one in src/app/memory/lancedb_store.py
embedding_dim = 384
schema = pa.schema(
    [
        pa.field("chunk_id", pa.string()),
        pa.field("content", pa.string()),
        pa.field(
            "embedding",
            pa.list_(pa.float32(), list_size=embedding_dim),
        ),
        pa.field("source_id", pa.string()),
        pa.field("source_url", pa.string()),
        pa.field("metadata", pa.string()),  # JSON-encoded
    ]
)

# --- Table Creation and Inspection ---
try:
    # Create a new table with the sample data
    table = db.create_table(table_name, schema=schema, mode="overwrite")
    table.add(sample_data)
    print("✅ Successfully created and populated in-memory table.\n")

    # --- Schema Inspection ---
    print("--- Table Schema ---")
    print(table.schema)
    print("\n")

    # --- Data Inspection ---
    print(f"--- Sample Records in '{table_name}' ---")
    # Convert to a pandas DataFrame to print nicely
    # We drop the 'embedding' vector column as it's too long to be useful here
    df = table.to_pandas()
    if "embedding" in df.columns:
        df = df.drop(columns=["embedding"])
        
    print(df)
    print("\n")

except Exception as e:
    print(f"❌ An error occurred during script execution: {e}")

finally:
    # Clean up the temporary directory
    import shutil
    shutil.rmtree(temp_dir)
