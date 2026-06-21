import logging
from pathlib import Path

import torch
import pandas as pd
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from utils.File_handling import Filehandle
from utils.chroma_utils import get_or_create_collection, delete_chroma_folder

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lazy-loaded model to avoid re-initializing on every call
_model = None


# Used for making Chunks 
def _get_model() -> SentenceTransformer:
    """Initializes and returns a singleton SentenceTransformer model."""
    global _model
    if _model is None:
        logger.info("Loading sentence transformer model...")
        _model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        logger.info("Model loaded.")
    return _model


def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into overlapping word chunks.

    Args:
        text: Input text.
        chunk_size: Number of words per chunk.
        overlap: Number of overlapping words.

    Returns:
        List of chunks.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = text.split()

    chunks = []

    step = chunk_size - overlap

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])

        if chunk.strip():
            chunks.append(chunk)

    return chunks


def table_to_chunks(file_path, rows_per_chunk=10):
    """Convert CSV/Excel rows into chunks."""
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)

    else:
        df = pd.read_excel(file_path)

    chunks = []

    for i in range(0, len(df), rows_per_chunk):
        chunk_df = df.iloc[i:i + rows_per_chunk]

        chunk_text = chunk_df.to_string(index=False)

        chunks.append(chunk_text)

    return chunks


# Used for storing vectorize chunks into db
def store_text_as_vectors(file_path: str):
    # To ensure the file_path is a Path object, not just a plain string.
    # In Python, file paths are often passed as strings (e.g., "data/file.csv"). 
    # But pathlib provides a Path object that gives you powerful, clean, and cross-platform path handling features.
    file_path = Path(file_path)
    file_name = Path(file_path).stem
    db_folder = Path("chroma_db") / file_name 

    try:
        # Checking if file exists or not
        if db_folder.exists():
            choice = input(
                f"Vector data for '{file_name}' already exists. Replace it? (y/n): "
            ).strip().lower()
            if choice not in ['y', 'yes']:
                logger.info(f"Keeping existing vector data for '{file_name}'.")
                return
            else:
                delete_chroma_folder(str(db_folder))
                logger.info(f"Removed old vector data for '{file_name}'.")

        collection = get_or_create_collection(str(db_folder))

        # Making chunks of the file
        extension = file_path.suffix.lower()
        if extension in [".csv", ".xlsx", ".xls"]:
            chunks = table_to_chunks(
                file_path,
                rows_per_chunk=10
            )
        else:
            fh = Filehandle()
            text = fh.file_path(str(file_path))
            if not text:
                logger.warning(
                    f"No text extracted from '{file_name}'."
                )
                return
            chunks = split_into_chunks(
                text,
                chunk_size=500,
                overlap=50
            )

        # Helps debugging
        logger.info(
            f"Created {len(chunks)} chunks from '{file_name}'"
        )

        # Vectorizing the Chunks
        model = _get_model()
        embeddings = model.encode(chunks, show_progress_bar=True).tolist()

        # Embedding vectoried chunks into db
        ids = [f"{file_name}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": file_name,
                "chunk_id": i,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )

        logger.info(f"File '{file_name}' processed and stored in '{db_folder}'.")
    except Exception as e:
        logger.error(f"An error occurred during vectorization for '{file_name}': {e}", exc_info=True)


def _select_file_for_query(available_files: list[str]) -> str | None:
    """Prompts the user to select a file and returns the selection."""
    print("\nAvailable files for querying:")
    for idx, name in enumerate(available_files, 1):
        print(f"  {idx}. {name}")

    while True:
        try:
            choice_str = input(f"Enter file number (1-{len(available_files)}): ").strip()
            choice = int(choice_str)
            if 1 <= choice <= len(available_files):
                return available_files[choice - 1]
            else:
                print("Invalid selection. Please try again.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number from the list.")


def process_query(query: str, selected_file: str) -> list[str]:
    db_root = Path("chroma_db")
    if not db_root.exists():
        print("No files have been uploaded yet.")
        return []

    # Checking if files are in db or not
    available_files = [
        d.name
        for d in Path(db_root).iterdir()
        if d.is_dir()
    ]
    if selected_file not in available_files:
        print(f"{selected_file} not found")
        return []

    try:
        db_path = db_root / selected_file
        collection = get_or_create_collection(str(db_path))

        results = collection.get(include=["documents", "embeddings", "metadatas"])
        if not results or not results['documents']:
            print(f"No content found for '{selected_file}'.")
            return []

        documents = results['documents']
        embeddings = results['embeddings']
        metadatas = results["metadatas"]

        # Query embedding and getting result
        model = _get_model()
        query_embedding = torch.tensor(model.encode(query), dtype=torch.float32)
        doc_embeddings = torch.tensor(embeddings, dtype=torch.float32)

        similarities = cos_sim(query_embedding, doc_embeddings)[0]
        # Get top 3 results
        top_indices = similarities.argsort(descending=True)[:3]

        return [{"text": documents[i], "metadata": metadatas[i]} for i in top_indices]
    except Exception as e:
        logger.error(f"Error processing query for '{selected_file}': {e}", exc_info=True)
        print("An error occurred while processing your query. Please check the logs.")
        return []
