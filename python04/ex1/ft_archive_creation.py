"""
ex1.ft_archive_creation
Learning how to write in files
"""


print("=== CYBER ARCHIVES - DATA RECOVERY SYSTEM ===\n")
print("Accessing Storage Vault: ancient_fragment.txt")
try:
    file = open("new_discovery.txt", "w")
    data = ("{[}ENTRY 001{]} New quantum algorithm discovered\n" +
            "{[}ENTRY 002{]} Efficiency increased by 347%\n" +
            "{[}ENTRY 003{]} Archived by Data Archivist trainee")
    file.write(data)
    print("Storage unit created successfully......\n")
    print("Inscribing preservation data...")
    print(data)
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    file.close()
    print("Data inscription complete. Storage unit sealed")
    print("Archive 'new_discovery.txt' ready for long-term preservation.")
