"""
ex3.ft_vault_security
Learn how to use with statement
"""


def print_file(file_name):
    """open and print file"""
    try:
        with open(file_name, "r") as vault:
            data = vault.read()
            print(data, end="")
    except FileNotFoundError:
        print("[ERROR] Vault not found. Secure extraction failed.")


def save_info(file_name):
    """write in file"""
    try:
        with open(file_name, "w") as vault:
            vault.write("[CLASSIFIED] New security protocols archived\n")
    except Exception as e:
        print("[ERROR] An unexpected error " +
              f"occurred during secure preservation: {e}")


def main():
    """main"""
    print("=== CYBER ARCHIVES - VAULT SECURITY SYSTEM ===\n")
    print("Initiating secure vault access...")
    file_name = "classified_data.txt"

    print("Vault connection established with failsafe protocols\n")
    print("SECURE EXTRACTION:")
    print_file(file_name)

    print("\nSECURE PRESERVATION:")
    save_info(file_name)
    print_file(file_name)

    print("Vault automatically sealed upon completion\n")
    print("All vault operations completed with maximum security.")


if __name__ == "__main__":
    main()
