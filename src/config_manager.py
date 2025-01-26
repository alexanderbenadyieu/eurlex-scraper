from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


class ConfigManager:
    """Manages configuration for the EUR-Lex scraper."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file. If None, uses default path.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
            
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get scraping-related configuration."""
        return self.config["scraping"]
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage-related configuration."""
        return self.config["storage"]
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """Get metrics-related configuration."""
        return self.config.get("metrics", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation-related configuration."""
        return self.config["validation"]
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update configuration and save to file.
        
        Args:
            new_config: New configuration dictionary to merge with existing config.
        """
        self.config.update(new_config)
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info("Configuration updated successfully")
        except Exception as e:
            logger.error(f"Failed to update configuration: {str(e)}")
            raise
