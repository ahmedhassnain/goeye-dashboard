# check_dns_files.py
from pathlib import Path

print("Checking for DNS CSV files in raw folders...")
print("="*50)

raw_dir = Path("raw")
if raw_dir.exists():
    for date_folder in sorted(raw_dir.iterdir()):
        if date_folder.is_dir():
            dns_files = list(date_folder.rglob("curr_dns*.csv"))
            if dns_files:
                print(f"✅ {date_folder.name}: Found {len(dns_files)} DNS file(s)")
                for f in dns_files:
                    print(f"   - {f.relative_to(date_folder)}")
            else:
                print(f"❌ {date_folder.name}: No DNS files found")
else:
    print("raw directory doesn't exist")

print("\n" + "="*50)
print("\nChecking staging folders...")
staging_dir = Path("staging")
if staging_dir.exists():
    for date_folder in sorted(staging_dir.iterdir()):
        if date_folder.is_dir():
            dns_files = list(date_folder.rglob("curr_dns*.csv"))
            if dns_files:
                print(f"✅ {date_folder.name}: Found {len(dns_files)} DNS file(s)")
            else:
                print(f"❌ {date_folder.name}: No DNS files found")