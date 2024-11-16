import requests
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# File to save working channels and keep track of duplicates
OUTPUT_FILE = "working_channels.m3u"
LOG_FILE = "channel_log.txt"
README_FILE = "README.md"

# Initial list of public IPTV playlist URLs
IPTV_SOURCES = [
    #"https://github.com/iptv-org/iptv/blob/master/streams/pk.m3u",
    #"https://github.com/iptv-org/iptv/blob/master/streams/qa.m3u",
    #"https://github.com/iptv-org/iptv/blob/master/streams/sa.m3u",
    #"https://github.com/iptv-org/iptv/blob/master/streams/in.m3u",
    #"https://github.com/iptv-org/iptv/blob/master/streams/in_samsung.m3u",
    #"https://github.com/iptv-org/iptv/blob/master/streams/ae.m3u",
    #"https://gist.githubusercontent.com/Shah12345678890/8b230a9ef007d5c17b96e54a0f8685e9/raw/allChannelPlaylist.m3u",
    #"https://paste.sgpedia.com/paste.php?id=125",
    #"https://paste.sgpedia.com/paste.php?id=128",
    #"https://gist.github.com/didarulcseiubat17/8e643cd89a2ddecb4a8c6f1233cebb5f",
    "https://raw.githubusercontent.com/imdhiru/bloginstall-iptv/main/bloginstall-iptv.m3u"
]

# Regex patterns for .m3u/.m3u8 links and channel names in EXTINF lines
M3U8_PATTERN = re.compile(r"(http[s]?://[^\s]+\.m3u8?)")
EXTINF_PATTERN = re.compile(r"#EXTINF:[^\n]*,(.*)")

def fetch_links(playlist_url):
    """Fetch and extract .m3u or .m3u8 links along with channel names from a playlist URL."""
    try:
        response = requests.get(playlist_url, timeout=10)
        response.raise_for_status()
        
        # Extract all EXTINF tags and URLs
        content = response.text
        links = M3U8_PATTERN.findall(content)
        extinf_tags = EXTINF_PATTERN.findall(content)
        
        # Pair each link with its channel name if available
        channels = []
        for i, link in enumerate(links):
            channel_name = extinf_tags[i] if i < len(extinf_tags) else "Unknown Channel"
            channels.append((channel_name, link))
        
        return channels
    except requests.RequestException as e:
        print(f"Failed to fetch from {playlist_url}: {e}")
        return []

def validate_link(channel_info):
    """Validate .m3u or .m3u8 link by attempting to play it for 10 seconds."""
    channel_name, url = channel_info
    try:
        with requests.get(url, stream=True, timeout=10) as response:
            if response.status_code == 200 and response.headers.get("content-type", "").startswith("video"):
                print(f"Testing link for playback: {url} - {channel_name}")
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=1024):
                    if time.time() - start_time >= 10:  # Check if the link plays for 10 seconds
                        print(f"Valid link confirmed: {url} - {channel_name}")
                        return channel_name, url
                print(f"Link did not sustain playback for 10 seconds: {url}")
            else:
                print(f"Invalid link (Status: {response.status_code}): {url}")
    except requests.RequestException as e:
        print(f"Connection error for link {url}: {e}")
    return None

def load_existing_links(file_path):
    """Load existing links from a given file."""
    existing_links = set()
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    channel_name = lines[i].strip()[len("#EXTINF:-1,"):]
                    link = lines[i + 1].strip()
                    existing_links.add((channel_name, link))
    except FileNotFoundError:
        pass
    return existing_links

def save_links(valid_links):
    """Save validated links to OUTPUT_FILE and update the tracking file."""
    tracked_links = load_tracked_links()
    new_links = valid_links - tracked_links

    if new_links:
        with open(OUTPUT_FILE, "a") as f:
            for channel_name, link in new_links:
                f.write(f"#EXTINF:-1,{channel_name}\n{link}\n")

        tracked_links.update(new_links)
        save_tracked_links(tracked_links)  # Update the tracking file
        print(f"Added {len(new_links)} new links to {OUTPUT_FILE}.")
    else:
        print("No new links to add.")

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
        all_links.extend(fetch_links(source))

    # Step 3: Use multithreading to validate links faster
    with ThreadPoolExecutor(max_workers=10) as executor:
        valid_links = set(filter(None, executor.map(validate_link, all_links)))

    # Step 4: Save new links and sync OUTPUT_FILE
    save_links(valid_links)
    sync_output_file(load_tracked_links())

if __name__ == "__main__":
    main()
