import yaml
import json
import os
from pathlib import Path
import logging

class ConfigManager:
    def __init__(self, env: str = "dev", config_dir: str = "./configs"):
        self.env = env
        self.config_dir = Path(config_dir)
        self.config = {}
        self._load_config()

    def _load_config(self):
        config_path_json = self.config_dir / f"{self.env}.json"
        config_path_yaml = self.config_dir / f"{self.env}.yaml"

        if config_path_json.exists():
            with open(config_path_json, "r") as f:
                self.config = json.load(f)
        elif config_path_yaml.exists():
            with open(config_path_yaml, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            logging.warning(f"No configuration file found for environment: {self.env}")

        self._load_env_overrides()

    def _load_env_overrides(self):
        for key in self.config:
            if key.upper() in os.environ:
                self.config[key] = os.environ[key.upper()]

    def get_config(self, key):
        """Retrieve a specific configuration parameter."""
        config = self.load_config()
        keys = key.split(".")
        for k in keys:
            config = config.get(k, None)
            if config is None:
                return None
        return config

    def enable_feature(self, flag):
        self.config.setdefault("feature_flags", {})[flag] = True

    def disable_feature(self, flag):
        self.config.setdefault("feature_flags", {})[flag] = False
        
    def is_feature_enabled(self, flag):
        return self.config.get("feature_flags", {}).get(flag, False)
    
    def list_all(self):
        return self.config
    
    
