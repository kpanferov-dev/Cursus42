#!/usr/bin/env python3
"""
construct.py
Has functions to check if we are in an environment or not
"""
import sys
import os
import site


def is_virtual_environment():
    """Check current env with global env"""
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def get_venv_name():
    """Get name of env"""
    return os.path.basename(sys.prefix)


def main():
    """main to test if we are in or out of venv"""
    print()

    try:
        in_venv = is_virtual_environment()
    except Exception as e:
        print(f"ERROR detecting virtual environment: {e}")
        in_venv = False

    if in_venv:
        print("MATRIX STATUS: Welcome to the construct")
        try:
            print(f"\nCurrent Python: {sys.executable}")
            print(f"Virtual Environment: {get_venv_name()}")
            print(f"Environment Path: {sys.prefix}")
        except Exception as e:
            print(f"ERROR retrieving Python paths: {e}")

        print("\nSUCCESS: You're in an isolated environment!")
        print("Safe to install packages without affecting")
        print("the global system.")
        print("\nPackage installation path:")

        try:
            site_packages = None
            for path in site.getsitepackages():
                if "site-packages" in path:
                    site_packages = path
                    break
            if not site_packages:
                site_packages = site.getusersitepackages()
            print(site_packages)
        except Exception as e:
            print(f"ERROR finding site-packages: {e}")

    else:
        print("MATRIX STATUS: You're still plugged in")
        print(f"Current Python: {sys.executable}")
        print("Virtual Environment: None detected")
        print("\nWARNING: You're in the global environment!")
        print("The machines can see everything you install.")
        print("\nTo enter the construct, run:")
        print("python -m venv matrix_env")
        print("source matrix_env/bin/activate  # On Unix")
        print("source matrix_env/Scripts/activate   # On bash")
        print("matrix_env\\Scripts\\activate   # On Windows")
        print("Then run this program again.")


if __name__ == "__main__":
    main()
