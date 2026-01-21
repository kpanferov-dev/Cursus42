"""
ex2.ft_stream_management
Learning how to use stream management
"""


import sys

print("=== CYBER ARCHIVES - COMMUNICATION SYSTEM ===\n")

sys.stdout.write("Input Stream active. Enter archivist ID: ")
archivist_id = input()

sys.stdout.write("Input Stream active. Enter status report: ")
sys.stdout.flush()
status_report = sys.stdin.readline().strip()

print(f"\n[STANDARD] Archive status from {archivist_id}: {status_report}")

sys.stderr.write("[ALERT] System diagnostic:" +
                 " Communication channels verified\n")
sys.stdout.write("[STANDARD] Data transmission complete: \n")

print("\nThree-channel communication test successful.")
