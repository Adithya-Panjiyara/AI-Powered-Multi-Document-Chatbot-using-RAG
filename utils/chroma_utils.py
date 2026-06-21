import chromadb
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_or_create_collection(
    db_path: str, collection_name: str = "file_chunks"
) -> chromadb.Collection:
    """
    Creates or retrieves a ChromaDB collection.

    Args:
        db_path (str): The file system path to the ChromaDB database directory.
        collection_name (str): The name of the collection.

    Returns:
        chromadb.Collection: The ChromaDB collection object.

    Raises:
        Exception: If there is an error initializing the client or getting the collection.
    """
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(f"Successfully accessed collection '{collection_name}' at '{db_path}'.")
        return collection
    except Exception as e:
        logger.error(f"Failed to get or create ChromaDB collection '{collection_name}': {e}")
        raise


def delete_chroma_folder(db_path: str) -> None:
    """Deletes a specific ChromaDB folder and its contents."""
    db_path_obj = Path(db_path)
    if db_path_obj.exists() and db_path_obj.is_dir():
        logger.info(f"Attempting to delete ChromaDB folder: {db_path_obj}")
        try:
            shutil.rmtree(db_path_obj)
            logger.info(f"Successfully deleted ChromaDB folder: {db_path_obj}")
        except OSError as e:
            logger.error(f"Error deleting ChromaDB folder {db_path_obj}: {e}")
    else:
        logger.info(f"ChromaDB folder not found, skipping deletion: {db_path_obj}")
