import json
import shutil
from pathlib import Path
from src.ingestion.clone_repo import extract_repo_name

# Registry path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "data" / "repositories.json"

class RepositoryNotFoundError(ValueError):
    """Exception raised when a repository does not exist or is not indexed."""
    pass

def load_registry() -> dict:
    """Load the repositories registry."""
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_registry(registry: dict):
    """Save the repositories registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

def list_repositories() -> list[str]:
    """Return a list of all registered repository names."""
    return list(load_registry().keys())

def validate_repository(repo_name: str) -> None:
    """Validate that the repository is registered and its datasets exist.
    
    Raises RepositoryNotFoundError if not valid.
    """
    registry = load_registry()
    if repo_name not in registry:
        raise RepositoryNotFoundError(f"Repository '{repo_name}' is not registered.")
    
    processed_dir = PROJECT_ROOT / "data" / "processed" / repo_name
    if not processed_dir.exists():
        raise RepositoryNotFoundError(
            f"Repository '{repo_name}' dataset directory '{processed_dir}' does not exist."
        )

def register_repository(
    repo_url: str,
    status: str = "indexing",
    index_version: str = "1.0",
    embedding_model: str = "BAAI/bge-small-en-v1.5"
) -> str:
    """Register a new repository or reset metadata for re-indexing."""
    repo_name = extract_repo_name(repo_url)
    registry = load_registry()
    
    registry[repo_name] = {
        "name": repo_name,
        "url": repo_url,
        "collection": f"repo_{repo_name}",
        "status": status,
        "indexed_at": None,
        "symbol_count": 0,
        "file_count": 0,
        "embedding_count": 0,
        "index_version": index_version,
        "embedding_model": embedding_model,
        "language_breakdown": {}
    }
    
    save_registry(registry)
    
    # Ensure processed directory exists
    processed_dir = PROJECT_ROOT / "data" / "processed" / repo_name
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    return repo_name

def update_repository_metadata(repo_name: str, **kwargs):
    """Update metadata fields for a specific repository."""
    registry = load_registry()
    if repo_name not in registry:
        raise RepositoryNotFoundError(f"Repository '{repo_name}' is not registered.")
    
    registry[repo_name].update(kwargs)
    save_registry(registry)

def delete_repository(repo_name: str) -> None:
    """Delete all files and data associated with a repository."""
    registry = load_registry()
    
    # 1. Delete cloned repository files
    clone_dir = PROJECT_ROOT / "data" / "repositories" / repo_name
    if clone_dir.exists():
        shutil.rmtree(clone_dir, ignore_errors=True)
        
    # 2. Delete processed datasets
    processed_dir = PROJECT_ROOT / "data" / "processed" / repo_name
    if processed_dir.exists():
        shutil.rmtree(processed_dir, ignore_errors=True)
        
    # 3. Delete isolated Chroma database folder
    chroma_dir = PROJECT_ROOT / "data" / "chroma_db" / repo_name
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir, ignore_errors=True)
        
    # 4. Remove from registry
    if repo_name in registry:
        del registry[repo_name]
        save_registry(registry)
