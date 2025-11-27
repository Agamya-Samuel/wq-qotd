from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
import configparser
from pathlib import Path

load_dotenv()

def _get_toolforge_credentials():
    """
    Read Toolforge database credentials from replica.my.cnf file.
    This file is automatically created by Toolforge and contains credentials.
    Returns tuple of (user, password) or (None, None) if not on Toolforge.
    """
    replica_cnf_path = Path.home() / "replica.my.cnf"
    if not replica_cnf_path.exists():
        return None, None
    
    try:
        config = configparser.ConfigParser()
        config.read(replica_cnf_path)
        user = config.get("client", "user")
        password = config.get("client", "password")
        return user, password
    except Exception:
        return None, None

class Settings(BaseSettings):
    # Database settings
    # On Toolforge, credentials come from replica.my.cnf or environment variables
    # For local development, use .env file or environment variables
    
    # Check if we're on Toolforge and get credentials
    _toolforge_user, _toolforge_password = _get_toolforge_credentials()
    _is_toolforge = _toolforge_user is not None
    
    if _is_toolforge:
        # Use Toolforge environment variables if available, otherwise use replica.my.cnf
        DB_HOST: str = os.getenv("TOOL_TOOLSDB_HOST", "tools.db.svc.wikimedia.cloud")
        DB_USER: str = os.getenv("TOOL_TOOLSDB_USER", _toolforge_user)
        DB_PASSWORD: str = os.getenv("TOOL_TOOLSDB_PASSWORD", _toolforge_password)
        # Database name format on Toolforge: s12345__dbname (where s12345 is the user)
        # Get tool name from environment or use default pattern
        DB_NAME: str = os.getenv("DB_NAME", f"{_toolforge_user}__qotd")
        DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    else:
        # Local development settings
        DB_HOST: str = os.getenv("DB_HOST", "localhost")
        DB_USER: str = os.getenv("DB_USER", "root")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        DB_NAME: str = os.getenv("DB_NAME", "qotd")
        DB_PORT: int = int(os.getenv("DB_PORT", "3306"))

    # for mysql/mariadb with pymysql driver
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # for postgres (commented out)
    # @property
    # def DATABASE_URL(self) -> str:
    #     return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
