import urllib.request
import os
import json

os.makedirs("scratch", exist_ok=True)

# Path to the list_screens output file
json_path = r"C:/Users/HP/.gemini/antigravity-ide/brain/1584119f-bfaf-46fc-9066-35c6fae3c02c/.system_generated/steps/18/output.txt"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

screens = data.get("screens", [])
print(f"Found {len(screens)} screens. Downloading HTML...")

for screen in screens:
    title = screen.get("title", "unknown")
    # Clean title for filename
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
    clean_title = clean_title.replace(" ", "_")
    
    html_info = screen.get("htmlCode", {})
    url = html_info.get("downloadUrl")
    if not url:
        print(f"Skipping {title} (no downloadUrl)")
        continue
        
    filename = f"{clean_title}.html"
    filepath = os.path.join("scratch", filename)
    try:
        print(f"Downloading {title} from {url}...")
        urllib.request.urlretrieve(url, filepath)
        print(f"Saved to {filepath}")
    except Exception as e:
        print(f"Failed to download {title}: {e}")
