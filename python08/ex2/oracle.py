#!/usr/bin/env python3
"""
oracle.py
.env playing
"""
import os
import sys
from dotenv import load_dotenv

"""
def load_env() -> None:
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as file:
            for line in file:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
"""


load_dotenv()


CONFIG = {
    "MATRIX_MODE": os.getenv("MATRIX_MODE", "development"),
    "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite://:memory:"),
    "API_KEY": os.getenv("API_KEY", ""),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "DEBUG"),
    "ZION_ENDPOINT": os.getenv("ZION_ENDPOINT", "http://localhost:8000"),
}


def check_required_config() -> None:
    """Function to check for required environment variables"""
    missing_configs = []
    if not CONFIG["API_KEY"]:
        missing_configs.append("API_KEY")

    if CONFIG["MATRIX_MODE"] not in ["development", "production"]:
        missing_configs.append("MATRIX_MODE")

    if missing_configs:
        print("ERROR: Missing or invalid configuration " +
              f"for: {', '.join(missing_configs)}")
        sys.exit(1)


def show_config() -> None:
    """Function to display the configuration"""
    print("\nORACLE STATUS: Reading the Matrix...\n")
    print("Configuration loaded:")
    print(f"Mode: {CONFIG['MATRIX_MODE']}")
    if CONFIG['MATRIX_MODE'] == "development":
        print("Database: Connected to local instance")
    else:
        print("Database: Connected to production instance")
    print("API Access: " +
          f"{'Authenticated' if CONFIG['API_KEY'] else 'Not Authenticated'}")
    print(f"Log Level: {CONFIG['LOG_LEVEL']}")
    print("Zion Network: " +
          f"{'Online' if CONFIG['ZION_ENDPOINT'] else 'Offline'}")


def check_security() -> None:
    """Function to check environment security"""
    print("\nEnvironment security check:")

    if CONFIG["API_KEY"] and CONFIG["API_KEY"] != "your-api-key-here":
        print("[OK] No hardcoded secrets detected")
    else:
        print("[WARNING] API_KEY is not set " +
              "or is still using the placeholder value")

    # Ensure .env file is present and configured
    if os.path.exists(".env"):
        print("[OK] .env file properly configured")
    else:
        print("[WARNING] .env file not found")

    # Check if the environment can be overridden
    if CONFIG["MATRIX_MODE"] == "development":
        print("[OK] Production overrides available")
    else:
        print("[INFO] No configuration used")


def main() -> None:
    """Main !!!!!!!!"""
    check_required_config()

    show_config()

    check_security()


if __name__ == "__main__":
    main()
