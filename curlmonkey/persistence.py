#persistence for settings, history, and collections

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import platform

from .models import Settings, HistoryEntry, Collection, Environment

logger = logging.getLogger(__name__)


def get_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    elif system == "Darwin":  #macOS
        base = Path.home() / "Library" / "Application Support"
    else:  #Linux and others
        base = Path.home() / ".local" / "share"
    
    data_dir = base / "curlmonkey"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_settings_path() -> Path:
    return get_data_dir() / "settings.json"


def get_history_path() -> Path:
    return get_data_dir() / "history.json"


def get_collections_path() -> Path:
    return get_data_dir() / "collections.json"


def get_environments_path() -> Path:
    return get_data_dir() / "environments.json"


def load_settings() -> Settings:
    settings_path = get_settings_path()
    if not settings_path.exists():
        logger.info("Settings file not found, using defaults")
        return Settings()
    
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings.from_dict(data)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return Settings()


def save_settings(settings: Settings) -> None:
    settings_path = get_settings_path()
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)
        logger.info("Settings saved successfully")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")


def load_history() -> List[HistoryEntry]:
    history_path = get_history_path()
    if not history_path.exists():
        return []
    
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [HistoryEntry.from_dict(entry) for entry in data]
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return []


def save_history(history: List[HistoryEntry]) -> None:
    history_path = get_history_path()
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump([entry.to_dict() for entry in history], f, indent=2)
        logger.info(f"History saved: {len(history)} entries")
    except Exception as e:
        logger.error(f"Error saving history: {e}")


def add_history_entry(entry: HistoryEntry) -> None:
    history = load_history()
    history.insert(0, entry)  #add to beginning
    #keep only last 1000 entries
    
    history = history[:1000]
    save_history(history)


def clear_history() -> None:
    save_history([])


def load_collections() -> List[Collection]:
    collections_path = get_collections_path()
    if not collections_path.exists():
        return []
    
    try:
        with open(collections_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Collection.from_dict(coll) for coll in data]
    except Exception as e:
        logger.error(f"Error loading collections: {e}")
        return []


def save_collections(collections: List[Collection]) -> None:
    collections_path = get_collections_path()
    try:
        with open(collections_path, "w", encoding="utf-8") as f:
            json.dump([coll.to_dict() for coll in collections], f, indent=2)
        logger.info(f"Collections saved: {len(collections)} collections")
    except Exception as e:
        logger.error(f"Error saving collections: {e}")


def load_environments() -> Dict[str, Environment]:
    environments_path = get_environments_path()
    if not environments_path.exists():
        #create default environment
        default_env = Environment(name="Default", variables={})
        envs = {"Default": default_env}
        save_environments(envs)
        return envs
    
    try:
        with open(environments_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {name: Environment.from_dict(env_data) for name, env_data in data.items()}
    except Exception as e:
        logger.error(f"Error loading environments: {e}")
        default_env = Environment(name="Default", variables={})
        return {"Default": default_env}


def save_environments(environments: Dict[str, Environment]) -> None:
    environments_path = get_environments_path()
    try:
        with open(environments_path, "w", encoding="utf-8") as f:
            data = {name: env.to_dict() for name, env in environments.items()}
            json.dump(data, f, indent=2)
        logger.info(f"Environments saved: {len(environments)} environments")
    except Exception as e:
        logger.error(f"Error saving environments: {e}")

