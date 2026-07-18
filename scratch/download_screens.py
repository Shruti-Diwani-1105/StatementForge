import urllib.request
import os

os.makedirs("scratch", exist_ok=True)

urls = {
    "dashboard.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwMDY1NmJhMTAyNzE2NGQwNGVhYWM1OGQ5MDM3ODNlEgsSBxCbjPyv2xgYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDQ4MTM1NDMwMTMwNDQxMDIwMQ&filename=&opi=96797242",
    "parser.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2FmODgxODg1ZTNjZDQxMjc5OGEwOTg3OTA1NWM4NjY4EgsSBxCbjPyv2xgYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDQ4MTM1NDMwMTMwNDQxMDIwMQ&filename=&opi=96797242",
    "auditor.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzkyMGQwOWJmNTQ1ZjQxZTZhYzljNzIxMDgzYzM2OWE5EgsSBxCbjPyv2xgYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDQ4MTM1NDMwMTMwNDQxMDIwMQ&filename=&opi=96797242"
}

for filename, url in urls.items():
    try:
        print(f"Downloading {filename}...")
        filepath = os.path.join("scratch", filename)
        urllib.request.urlretrieve(url, filepath)
        print(f"Saved to {filepath}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
