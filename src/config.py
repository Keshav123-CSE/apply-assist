"""Configuration loader and path constants for apply-assist."""

import os
from pathlib import Path
from typing import Any, Dict
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yml"
COMPANIES_PATH = ROOT_DIR / "companies.yml"
COMPANIES_EXAMPLE_PATH = ROOT_DIR / "companies.example.yml"
PROFILE_PATH = ROOT_DIR / "profile.yml"
PROFILE_EXAMPLE_PATH = ROOT_DIR / "profile.example.yml"
RESUME_DIR = ROOT_DIR / "resume"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "apply_assist.db"
APPLICATIONS_MD_PATH = ROOT_DIR / "applications.md"
SCREENSHOTS_DIR = ROOT_DIR / "screenshots"

def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Safely loads a YAML file, returning an empty dict if not found."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data or {}

def get_app_config() -> Dict[str, Any]:
    """Loads system application configuration."""
    return load_yaml(CONFIG_PATH)

def get_companies_file() -> Path:
    """Returns companies.yml if present, otherwise companies.example.yml."""
    if COMPANIES_PATH.exists():
        return COMPANIES_PATH
    return COMPANIES_EXAMPLE_PATH
