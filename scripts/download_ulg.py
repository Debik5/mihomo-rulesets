#!/usr/bin/env python3
import os
import sys
import urllib.request
import json
import tarfile
import zipfile
import io

def download_ulg():
    # Use ULG_RELEASE_TOKEN (set by user in Actions secrets) or fallback to GITHUB_TOKEN
    token = os.getenv("ULG_RELEASE_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("PAT_TOKEN")
    if not token:
        print("[!] Warning: No GITHUB_TOKEN or ULG_RELEASE_TOKEN found. API requests to private repo may fail.")
    
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ULG-Downloader"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        
    # Get latest release metadata
    url = "https://api.github.com/repos/Debik5/ULG/releases/latest"
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"[-] Error fetching release metadata: {e}")
        print("Please check your GITHUB_TOKEN / permissions / network.")
        sys.exit(1)
        
    tag = data.get("tag_name")
    print(f"[+] Found ULG version: {tag}")
    
    # Determine OS and Arch
    platform = sys.platform # 'darwin', 'linux', 'win32'
    import platform as pf
    arch = pf.machine().lower() # 'x86_64', 'amd64', 'arm64', etc.
    
    # Map platform to GoReleaser naming
    if platform == "darwin":
        goos = "darwin"
    elif platform == "linux" or platform.startswith("linux"):
        goos = "linux"
    elif platform == "win32":
        goos = "windows"
    else:
        goos = platform

    if arch in ["amd64", "x86_64"]:
        goarch = "amd64"
    elif arch in ["arm64", "aarch64"]:
        goarch = "arm64"
    else:
        goarch = arch

    print(f"[+] Detected system: {goos}_{goarch}")
    
    # Look for matching asset
    target_asset = None
    for asset in data.get("assets", []):
        name = asset["name"].lower()
        if goos in name and goarch in name:
            target_asset = asset
            break
            
    if not target_asset:
        # Fallback search matching OS
        for asset in data.get("assets", []):
            name = asset["name"].lower()
            if goos in name:
                target_asset = asset
                break
                
    if not target_asset:
        print(f"[-] No matching asset found for {goos}_{goarch} in assets:")
        for asset in data.get("assets", []):
            print(f"  - {asset['name']}")
        sys.exit(1)
        
    asset_name = target_asset["name"]
    asset_url = target_asset["url"] # API URL for download
    print(f"[+] Downloading asset: {asset_name}")
    
    # Download asset using octet-stream header (needed for private repo assets)
    headers_download = headers.copy()
    headers_download["Accept"] = "application/octet-stream"
    req_download = urllib.request.Request(asset_url, headers=headers_download)
    
    try:
        with urllib.request.urlopen(req_download) as response:
            content = response.read()
    except Exception as e:
        print(f"[-] Error downloading asset: {e}")
        sys.exit(1)
        
    # Extract binary
    bin_name = "ulg.exe" if goos == "windows" else "ulg"
    extracted = False
    
    # We want to extract to the repository root directory
    dest_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_path = os.path.join(dest_dir, bin_name)
    
    if asset_name.endswith(".tar.gz") or asset_name.endswith(".tgz"):
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == bin_name or member.name.endswith("/" + bin_name):
                    f = tar.extractfile(member)
                    if f:
                        with open(dest_path, "wb") as dest:
                            dest.write(f.read())
                        extracted = True
                        break
    elif asset_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            for name in z.namelist():
                if name == bin_name or name.endswith("/" + bin_name):
                    with open(dest_path, "wb") as dest:
                        dest.write(z.read(name))
                    extracted = True
                    break
                    
    if not extracted:
        print(f"[-] Could not extract {bin_name} from archive. Saving archive directly as {asset_name}.")
        archive_path = os.path.join(dest_dir, asset_name)
        with open(archive_path, "wb") as dest:
            dest.write(content)
    else:
        # Set executable permissions on Unix
        if goos != "windows":
            os.chmod(dest_path, 0o755)
        print(f"[+] Successfully downloaded and extracted {dest_path}!")

if __name__ == "__main__":
    download_ulg()
