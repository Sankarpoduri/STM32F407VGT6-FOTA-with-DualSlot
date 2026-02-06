from flask import Flask, send_file, request
import os
import time
import threading
import requests  # pip install requests

app = Flask(__name__)

# ================= CONFIGURATION =================
FIRMWARE_FOLDER = "firmware"
VERSION_FILE = "version.txt"

# S3 CONFIGURATION
BUCKET_NAME = "stm32-fota-updates-2026"
# If your bucket is NOT in us-east-1, change this (e.g., 'us-west-2', 'ap-south-1')
REGION = "ap-south-1" 

# Base URL for Public S3 Access
# Format: https://<bucket-name>.s3.<region>.amazonaws.com/
S3_BASE_URL = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com"

# Files to sync
FILES_TO_SYNC = ["slot_a.bin", "slot_b.bin", "version.txt"]

BINARIES = {
    "to_bank_a": "slot_a.bin",  
    "to_bank_b": "slot_b.bin"   
}

# ================= HELPER FUNCTIONS =================
def get_local_version():
    """Reads the version number from local firmware/version.txt"""
    try:
        file_path = os.path.join(FIRMWARE_FOLDER, VERSION_FILE)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read().strip()
                if content.isdigit():
                    return int(content)
    except Exception as e:
        print(f"[ERROR] Could not read local version file: {e}")
    return 0  # Default if file missing or empty

def download_from_s3(filename):
    """Downloads a single file from public S3 to the firmware folder"""
    url = f"{S3_BASE_URL}/{filename}"
    local_path = os.path.join(FIRMWARE_FOLDER, filename)
    
    try:
        print(f"   ... Downloading {filename} from {url}")
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"   [ERROR] Failed to download {filename}. Status Code: {r.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] Exception downloading {filename}: {e}")
        return False

def s3_update_checker():
    """Background task to poll S3 for new versions"""
    print(f"[S3 SYNC] Monitoring Public Bucket: {BUCKET_NAME}")
    print(f"[S3 SYNC] Check URL: {S3_BASE_URL}/{VERSION_FILE}")

    while True:
        try:
            # 1. Check Version on S3
            version_url = f"{S3_BASE_URL}/{VERSION_FILE}"
            r = requests.get(version_url, timeout=5)
            
            if r.status_code == 200:
                remote_version_str = r.text.strip()
                
                if remote_version_str.isdigit():
                    remote_version = int(remote_version_str)
                    local_version = get_local_version()

                    # 2. If S3 has a higher version, download everything
                    if remote_version > local_version:
                        print(f"\n[S3 SYNC] New update found! S3: {remote_version} > Local: {local_version}")
                        print("[S3 SYNC] Starting download...")

                        success_a = download_from_s3("slot_a.bin")
                        success_b = download_from_s3("slot_b.bin")
                        
                        # Only update the local version file if binaries succeeded
                        if success_a and success_b:
                            # Save the new version.txt
                            local_ver_path = os.path.join(FIRMWARE_FOLDER, VERSION_FILE)
                            with open(local_ver_path, "w") as f:
                                f.write(str(remote_version))
                            print(f"[S3 SYNC] Update Complete! Server now hosting Version {remote_version}\n")
                        else:
                            print("[S3 SYNC] Download failed. Will retry next cycle.\n")
                    
                    # Optional: Print heartbeat every loop
                    # else:
                    #    print(f"[S3 SYNC] Up to date ({local_version})...")

                else:
                    print(f"[S3 ERROR] Remote version.txt is not a number: '{remote_version_str}'")
            
            elif r.status_code == 404:
                print(f"[S3 ERROR] version.txt not found in bucket (404)")
            elif r.status_code == 403:
                print(f"[S3 ERROR] Access Denied (403). Is the file definitely public?")
            else:
                print(f"[S3 ERROR] Failed to check version. Status: {r.status_code}")

        except requests.exceptions.ConnectionError:
            print("[S3 ERROR] Connection failed. Check internet.")
        except Exception as e:
            print(f"[S3 ERROR] Unexpected error: {e}")

        # Poll every 30 seconds
        time.sleep(30)

# ================= FLASK ROUTES =================
@app.route('/version')
def get_version_route():
    v = get_local_version()
    return str(v)

@app.route('/firmware')
def get_firmware():
    current_bank = request.args.get('current_bank')
    
    if current_bank is None:
        return "Error: Missing 'current_bank'", 400

    filename = ""
    
    # Ping-Pong Logic
    if current_bank == '0':
        filename = BINARIES["to_bank_b"]
    elif current_bank == '1':
        filename = BINARIES["to_bank_a"]
    else:
        return "Error: Invalid bank ID", 400

    file_path = os.path.join(FIRMWARE_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name='firmware.bin')
    else:
        return "Binary not found", 404

# ================= MAIN ENTRY =================
if __name__ == '__main__':
    # Create firmware folder if it doesn't exist
    if not os.path.exists(FIRMWARE_FOLDER):
        os.makedirs(FIRMWARE_FOLDER)
        
    # Start the S3 Sync Thread
    sync_thread = threading.Thread(target=s3_update_checker)
    sync_thread.daemon = True 
    sync_thread.start()

    print(f"Server running on 0.0.0.0:5000")
    print(f"Local storage: ./{FIRMWARE_FOLDER}")
    
    # Start Flask
    app.run(host='0.0.0.0', port=5000, debug=False)
