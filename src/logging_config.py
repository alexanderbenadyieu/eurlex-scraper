import sys
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger


def setup_logging(config_path: Optional[Path] = None) -> None:
    """
    Configure logging for the application using loguru.
    
    Args:
        config_path: Path to the configuration file. If None, uses default config.
    """
    # Load configuration
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    with open(config_path) as f:
        config = yaml.safe_load(f)["logging"]
    
    # Remove default logger
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=config["format"],
        level=config["level"],
        backtrace=True,
        diagnose=True,
    )
    
    # Add file handler
    log_path = Path(__file__).parent.parent / "logs" / "eurlex_scraper.log"
    log_path.parent.mkdir(exist_ok=True)
    
    logger.add(
        str(log_path),
        rotation=config["rotation"],
        retention=config["retention"],
        format=config["format"],
        level=config["level"],
        backtrace=True,
        diagnose=True,
    )
    
    logger.info("Logging configured successfully")
