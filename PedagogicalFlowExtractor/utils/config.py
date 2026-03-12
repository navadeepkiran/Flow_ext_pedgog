"""Configuration management for PedagogicalFlowExtractor."""

import os
import re
import yaml
from dotenv import load_dotenv


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CONFIG_PATH = os.path.join(_BASE_DIR, "config.yaml")


def _substitute_env_vars(config_dict: dict) -> dict:
    """Recursively substitute environment variables in config."""
    if isinstance(config_dict, dict):
        return {key: _substitute_env_vars(value) for key, value in config_dict.items()}
    elif isinstance(config_dict, list):
        return [_substitute_env_vars(item) for item in config_dict]
    elif isinstance(config_dict, str):
        # Handle ${VAR} and ${VAR:default} syntax
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            
            # Get environment variable value
            env_value = os.getenv(var_name, default_value)
            
            # Convert string representations of booleans/numbers
            if env_value.lower() in ('true', 'false'):
                return env_value.lower() == 'true'
            elif env_value.lower() == 'null':
                return None
            elif env_value.isdigit():
                return int(env_value)
            elif env_value.replace('.', '', 1).isdigit():
                return float(env_value)
            else:
                return env_value
        
        return re.sub(pattern, replace_var, config_dict)
    else:
        return config_dict


def load_config(config_path: str = None) -> dict:
    """Load YAML configuration file with environment variable substitution.

    Args:
        config_path: Path to config file. Defaults to project root config.yaml.

    Returns:
        Configuration dictionary with env vars substituted.
    """
    # Load .env file if it exists
    env_path = os.path.join(_BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    path = config_path or _DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    # Substitute environment variables
    return _substitute_env_vars(raw_config)


def get_project_root() -> str:
    """Return the absolute path to the project root directory."""
    return _BASE_DIR


def resolve_path(relative_path: str) -> str:
    """Resolve a path relative to the project root."""
    return os.path.join(_BASE_DIR, relative_path)


def get_api_key(service: str = 'groq') -> str:
    """Get API key from environment or config.
    
    Args:
        service: Service name ('groq', 'openai', etc.)
        
    Returns:
        API key string or raises ValueError if not found.
    """
    # Load .env if exists
    env_path = os.path.join(_BASE_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Try environment variable first
    env_var = f"{service.upper()}_API_KEY"
    api_key = os.getenv(env_var)
    
    if api_key:
        return api_key
    
    # Try config file as fallback
    config = load_config()
    if service in config and 'api_key' in config[service]:
        api_key = config[service]['api_key']
        if api_key and not api_key.startswith('${'):
            return api_key
    
    raise ValueError(f"API key for {service} not found. Set {env_var} in .env file or update config.yaml")


def validate_config() -> bool:
    """Validate that required configuration is present.
    
    Returns:
        True if config is valid, False otherwise.
    """
    try:
        config = load_config()
        
        # Check for required API key
        try:
            get_api_key('groq')
        except ValueError:
            print("⚠️  Missing GROQ_API_KEY. Set it in .env file.")
            return False
        
        # Check for required files
        required_files = [
            config['normalizer']['lexicon_path'],
            config['normalizer']['telugu_lexicon_path'],
            config['extractor']['concepts_path']
        ]
        
        for file_path in required_files:
            full_path = resolve_path(file_path)
            if not os.path.exists(full_path):
                print(f"⚠️  Missing required file: {file_path}")
                return False
        
        return True
        
    except Exception as e:
        print(f"⚠️  Config validation error: {e}")
        return False
