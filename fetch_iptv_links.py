import requests
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# File to save working channels and keep track of duplicates
OUTPUT_FILE = "working_channels.m3u"
LOG_FILE = "channel_log.txt"
README_FILE = "README.md"

# Initial list of public IPTV playlist URLs
IPTV_SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/pk.m3u",
    "https://iptv-org.github.io/iptv/countries/om.m3u",
    "https://iptv-org.github.io/iptv/countries/qa.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/lb.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u",
    "https://iptv-org.github.io/iptv/countries/bh.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/in_samsung.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://gist.githubusercontent.com/Shah12345678890/8b230a9ef007d5c17b96e54a0f8685e9/raw/allChannelPlaylist.m3u",
    #"https://paste.sgpedia.com/paste.php?id=125",
    #"https://paste.sgpedia.com/paste.php?id=128",
    #"https://gist.github.com/didarulcseiubat17/8e643cd89a2ddecb4a8c6f1233cebb5f",
    #"https://raw.githubusercontent.com/imdhiru/bloginstall-iptv/main/bloginstall-iptv.m3u"
]

# Regex patterns for .m3u/.m3u8 links and channel names in EXTINF lines
M3U8_PATTERN = re.compile(r"(http[s]?://[^\s]+\.m3u8?)")
EXTINF_PATTERN = re.compile(r"#EXTINF:[^\n]*,(.*)")

# Configure logging to track failed attempts
logging.basicConfig(filename=LOG_FILE, level=logging.WARNING)

def fetch_links(playlist_url, retries=5, backoff_factor=2):
    """Fetch and extract .m3u or .m3u8 links with retry mechanism."""
    for attempt in range(retries):
        try:
            response = requests.get(playlist_url, timeout=15)  # Increased timeout
            response.raise_for_status()
            # Extract all EXTINF tags and URLs
            content = response.text
            links = M3U8_PATTERN.findall(content)
            extinf_tags = EXTINF_PATTERN.findall(content)
            channels = [
                (extinf_tags[i] if i < len(extinf_tags) else "Unknown Channel", link)
                for i, link in enumerate(links)
            ]
            print(f"Fetched {len(channels)} channels from {playlist_url}")  # Debug print
            return channels
        except requests.RequestException as e:
            print(f"Error fetching {playlist_url} (Attempt {attempt + 1}): {e}")
            # Log the failure to a file for future reference
            logging.warning(f"Failed to fetch {playlist_url}: {e}")
            if attempt < retries - 1:
                # Exponential backoff: wait for longer before retrying
                sleep_time = backoff_factor ** attempt
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    print(f"Failed to fetch {playlist_url} after {retries} attempts.")
    return []  # Return an empty list if all attempts fail

def validate_link(channel_info):
    """Validate .m3u or .m3u8 link by attempting to play it for 10 seconds."""
    channel_name, url = channel_info
    try:
        with requests.get(url, stream=True, timeout=10) as response:
            if response.status_code == 200 and response.headers.get("content-type", "").startswith("video"):
                print(f"Testing link for playback: {url} - {channel_name}")  # Debug print
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=1024):
                    if time.time() - start_time >= 10:  # Check if the link plays for 10 seconds
                        print(f"Valid link confirmed: {url} - {channel_name}")  # Debug print
                        return channel_name, url
                print(f"Link did not sustain playback for 10 seconds: {url}")  # Debug print
            else:
                print(f"Invalid link (Status: {response.status_code}): {url}")  # Debug print
    except requests.RequestException as e:
        print(f"Connection error for link {url}: {e}")
        # Log the failure to a file for future reference
        logging.warning(f"Failed to validate {url}: {e}")
    return None

def load_existing_links(file_path):
    """Load existing links from a given file."""
    existing_links = set()
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    channel_name = lines[i].strip()[len("#EXTINF:-1,"): ]
                    link = lines[i + 1].strip()
                    existing_links.add((channel_name, link))
    except FileNotFoundError:
        pass
    return existing_links

def save_links(valid_links):
    """Save validated links with channel names to .m3u file, avoiding duplicates and ensuring manually deleted links are restored."""
    existing_links = load_existing_links(OUTPUT_FILE)  # Load existing entries to avoid duplicates
    new_links = []

    # Ensure manually deleted links are restored
    all_links = set(existing_links)
    for channel_name, link in valid_links:
        all_links.add((channel_name, link))

    # Save all tracked links back to the file
    with open(OUTPUT_FILE, "w") as f:  # Overwrite the file with the complete list
        for channel_name, link in all_links:
            f.write(f"#EXTINF:-1,{channel_name}\n{link}\n")

    # Identify newly added links
    new_links = [link for link in valid_links if link not in existing_links]

    if new_links:
        update_readme(new_links)  # Update README with new links
        print(f"Updated {OUTPUT_FILE} with {len(new_links)} new links.")  # Debug print
    else:
        print("No new links found to add.")  # Debug print

def update_readme(new_links):
    """Update README.md with newly found working channels."""
    try:
        with open(README_FILE, "r") as readme:
            lines = readme.readlines()

        start_idx = next((i for i, line in enumerate(lines) if "## New Working Channels Found" in line), None)
        end_idx = next((i for i in range(start_idx + 1, len(lines)) if lines[i].startswith("## ")), len(lines)) if start_idx is not None else None

        new_content = ["## New Working Channels Found\n", f"Updated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"]
        new_content.extend([f"- **{channel_name}**: [Stream Link]({link})\n" for channel_name, link in new_links])

        if start_idx is not None and end_idx is not None:
            lines = lines[:start_idx] + new_content + lines[end_idx:]
        else:
            lines.extend(new_content)

        with open(README_FILE, "w") as readme:
            readme.writelines(lines)
        print("README.md updated.")
    except IOError as e:
        print(f"Error updating README.md: {e}")

def main():
    # Step 1: Load initial and new sources
    all_sources = set(IPTV_SOURCES)

    # Step 2: Fetch and validate links
    all_links = []
    for source in all_sources:
        all_links.extend(fetch_links(source))  # Try fetching links

    # Step 3: Use multithreading to validate links faster
    with ThreadPoolExecutor(max_workers=10) as executor:
        valid_links = list(filter(None, executor.map(validate_link, all_links)))

    # Step 4: Save all fetched links
    save_links(valid_links)

if __name__ == "__main__":
    main()
