"""
ex4.ft_crisis_response

"""


def crisis_handler(file_name):
    """
    Handles the operation of accessing and reading an archive file securely.
    Responds appropriately to various scenarios: missing file, security issues, or success.
    """
    try:
        print(f"CRISIS ALERT: Attempting access to '{file_name}'...")

        with open(file_name, "r") as archive:
            content = archive.read()
            print(f"SUCCESS: Archive recovered - ``{content.strip()}``")
            print("STATUS: Normal operations resumed")

    except FileNotFoundError:
        print(f"RESPONSE: Archive not found in storage matrix")
        print("STATUS: Crisis handled, system stable")

    except PermissionError:
        print(f"RESPONSE: Security protocols deny access")
        print("STATUS: Crisis handled, security maintained")

    except Exception as e:
        print(f"RESPONSE: Unexpected system anomaly: {e}")
        print("STATUS: Crisis handled, system stabilized")


def main():
    print("=== CYBER ARCHIVES - CRISIS RESPONSE SYSTEM ===\n")

    archives = [
        "lost_archive.txt",
        "classified_vault.txt",
        "standard_archive.txt"
    ]

    for file_name in archives:
        crisis_handler(file_name)
        print()

    print("All crisis scenarios handled successfully. Archives secure.")


if __name__ == "__main__":
    main()