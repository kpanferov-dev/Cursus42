"""
ex0.ft_ancient_text
Learning how to open files
"""


print("=== CYBER ARCHIVES - DATA RECOVERY SYSTEM ===\n")
print("Accessing Storage Vault: ancient_fragment.txt")
try:
    with open("ancient_fragment.txt", "r") as file:
        data = file.read()
        print("Connection established...\n")
        print("RECOVERED DATA:")
        print(data)
except FileNotFoundError:
    print("ERROR: Storage vault not found.\n")
finally:
    print("\nData recovery complete. Storage unit disconnected.")
