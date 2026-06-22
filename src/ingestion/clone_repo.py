"""Module for cloning and updating GitHub repositories locally."""

import logging
import shutil
import urllib.parse
from pathlib import Path
import git

logger = logging.getLogger(__name__)


def extract_repo_name(repo_url: str) -> str:
    """Extracts the repository name from a GitHub/Git repository URL.

    Args:
        repo_url: The URL of the repository (HTTPS, SSH, etc.).

    Returns:
        The extracted repository name string.

    Raises:
        ValueError: If the repository name cannot be extracted from the URL.
    """
    url_str = repo_url.strip()
    if url_str.endswith(".git"):
        url_str = url_str[:-4]
    url_str = url_str.rstrip("/")

    # Handle SSH git URLs vs HTTPS URLs
    if url_str.startswith("git@") or "git:" in url_str:
        # e.g., git@github.com:owner/repo.git -> split on last '/'
        parts = url_str.split("/")
    else:
        parsed = urllib.parse.urlparse(url_str)
        parts = parsed.path.split("/")

    if parts:
        name = parts[-1]
        if name:
            return name

    raise ValueError(f"Could not extract repository name from URL: {repo_url}")


def clone_repository(repo_url: str) -> str:
    """Clones a GitHub repository locally into 'data/repositories/{repo_name}'.

    If the directory already exists and is a valid Git repository, it pulls changes.
    If the directory exists but is invalid, it deletes the directory and re-clones.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        The absolute local path of the cloned repository as a string.

    Raises:
        ValueError: If the repo URL is invalid.
        git.exc.GitCommandError: If cloning or pulling fails.
    """
    repo_name = extract_repo_name(repo_url)

    # Determine project root and destination path
    project_root = Path(__file__).resolve().parents[2]
    dest_dir = project_root / "data" / "repositories" / repo_name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    if dest_dir.exists():
        try:
            logger.info(
                f"Directory {dest_dir} already exists. Verifying Git repository status."
            )
            repo = git.Repo(dest_dir)
            if not repo.bare and repo.remotes:
                logger.info("Valid Git repository found. Pulling latest changes...")
                origin = repo.remotes[0]
                origin.pull()
                logger.info("Successfully pulled latest changes.")
                return str(dest_dir.resolve())

            logger.warning(
                f"Repository at {dest_dir} is invalid or bare. Re-cloning..."
            )
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as e:
            logger.warning(
                f"Directory {dest_dir} is not a valid Git repository ({e}). Re-cloning..."
            )
        except Exception as e:
            logger.warning(
                f"Failed to update existing repository via pull: {e}. Re-cloning..."
            )

        # Cleanup the directory before re-cloning if pull failed or repo was invalid
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)

    logger.info(f"Cloning repository from {repo_url} into {dest_dir}...")
    git.Repo.clone_from(repo_url, dest_dir)
    logger.info(f"Successfully cloned repository into {dest_dir}.")

    return str(dest_dir.resolve())
