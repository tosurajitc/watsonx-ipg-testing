import yaml
import json
import os
from pathlib import Path
import logging
import psycopg2
import redis

class ConfigManager:
    def __init__(self, env: str = "dev", config_dir: str = "./configs"):
        self.env = env
        self.config_dir = Path(config_dir)
        self.config = {}
        self._load_config()
        try:
            self.conn = psycopg2.connect("dbname=config_db user=admin password=secure123")
            self.cursor = self.conn.cursor()
            self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        except psycopg2.Error as e:
            print(f"Database connection error: {e}")

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
    
    def get_config_from_DB(self, key):
        """Retrieve configuration, checking Redis cache first."""
        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                return cached_value

            self.cursor.execute("SELECT config_value FROM configurations WHERE config_key=%s ORDER BY version DESC LIMIT 1", (key,))
            result = self.cursor.fetchone()
            if result:
                self.redis_client.set(key, result[0])  # Cache the value
                return result[0]
            return None
        except psycopg2.Error as e:
            print(f"Error fetching configuration: {e}")
            
    def update_config_to_DB(self, key, value):
        """Update configuration with version tracking."""
        try:
            self.cursor.execute("""
                INSERT INTO configurations (config_key, config_value, version)
                VALUES (%s, %s, (SELECT COALESCE(MAX(version), 0) + 1 FROM configurations WHERE config_key=%s))
                ON CONFLICT (config_key) DO UPDATE SET config_value=%s, version=configurations.version + 1
            """, (key, value, key, value))
            self.conn.commit()
            self.redis_client.set(key, value)  # Update cache
        except psycopg2.Error as e:
            print(f"Error updating configuration: {e}")
    
    def bulk_update_configurations(self, updates):
        """
        Updates multiple configuration settings in bulk.

        :param updates: List of dictionaries containing 'config_key' and 'config_value'.
        """
        try:
            query = "UPDATE configurations SET config_value = %s WHERE config_key = %s"
            self.cursor.executemany(query, [(update["config_value"], update["config_key"]) for update in updates])

            self.conn.commit()
            return {"status": "Bulk update successful", "updated_records": len(updates)}

        except psycopg2.Error as e:
            return {"error": f"Bulk update failed: {str(e)}"}
    
    
