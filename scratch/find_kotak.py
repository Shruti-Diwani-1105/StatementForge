import os
import glob

# Search in current directory, D:/ and C:/Users/HP/Downloads/ or standard downloads
paths = [
    ".",
    "D:/",
    "C:/Users/HP/Downloads",
    "C:/Users/HP/Desktop"
]

print("Searching for Kotak statement files...")
for p in paths:
    if os.path.exists(p):
        pattern = os.path.join(p, "*[Kk]otak*.pdf")
        for f in glob.glob(pattern):
            print(f"Found: {f} (Size: {os.path.getsize(f)} bytes)")
        
        # Also check subdirectories recursively up to 1 level
        for sub in os.listdir(p):
            sub_path = os.path.join(p, sub)
            if os.path.isdir(sub_path) and not sub.startswith('.'):
                try:
                    for f in glob.glob(os.path.join(sub_path, "*[Kk]otak*.pdf")):
                        print(f"Found: {f} (Size: {os.path.getsize(f)} bytes)")
                except:
                    pass
