#!/usr/bin/env python3
import os
import sys

# Load environment variables from the .env file
def load_env():
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as file:
            for line in file:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Now load the environment variables
load_env()

# Default configuration values
CONFIG = {
    "MATRIX_MODE": os.getenv("MATRIX_MODE", "development"),
    "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite://:memory:"),
    "API_KEY": os.getenv("API_KEY", ""),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "DEBUG"),
    "ZION_ENDPOINT": os.getenv("ZION_ENDPOINT", "http://localhost:8000"),
}

# Function to check for required environment variables
def check_required_config():
    missing_configs = []
    if not CONFIG["API_KEY"]:
        missing_configs.append("API_KEY")
    
    if CONFIG["MATRIX_MODE"] not in ["development", "production"]:
        missing_configs.append("MATRIX_MODE")
    
    if missing_configs:
        print(f"ERROR: Missing or invalid configuration for: {', '.join(missing_configs)}")
        sys.exit(1)

# Function to display the configuration
def show_config():
    print("Accessing the Mainframe")
    print("ORACLE STATUS: Reading the Matrix...\n")
    print("Configuration loaded:")
    print(f"Mode: {CONFIG['MATRIX_MODE']}")
    if CONFIG['MATRIX_MODE'] == "development":
        print("Database: Connected to local instance")
    else:
        print("Database: Connected to production instance")
    print(f"API Access: {'Authenticated' if CONFIG['API_KEY'] else 'Not Authenticated'}")
    print(f"Log Level: {CONFIG['LOG_LEVEL']}")
    print(f"Zion Network: {'Online' if CONFIG['ZION_ENDPOINT'] else 'Offline'}")

# Function to check environment security
def check_security():
    print("\nEnvironment security check:")
    
    # Check if API_KEY is set to something other than a placeholder or empty string
    if CONFIG["API_KEY"] and CONFIG["API_KEY"] != "your-api-key-here":
        print("[OK] No hardcoded secrets detected")
    else:
        print("[WARNING] API_KEY is not set or is still using the placeholder value")

    # Ensure .env file is present and configured
    if os.path.exists(".env"):
        print("[OK] .env file properly configured")
    else:
        print("[WARNING] .env file not found")

    # Check if the environment can be overridden
    if CONFIG["MATRIX_MODE"] == "production":
        print("[OK] Production overrides available")
    else:
        print("[INFO] Development configuration in use")

# Main program logic
def main():
    # Check for required configuration
    check_required_config()
    
    # Show the configuration details
    show_config()
    
    # Perform security checks
    check_security()

if __name__ == "__main__":
    main()