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
    "https://github.com/iptv-org/iptv/blob/master/streams/at_samsung.m3u",
    "https://github.com/iptv-org/iptv/blob/master/streams/pk.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/qa.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/sa.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/uk.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/us.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/in.m3u8",
    "https://github.com/iptv-org/iptv/blob/master/streams/in_samsung.m3u8",
    "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/ae.m3u8",
    "https://gist.github.com/didarulcseiubat17/8e643cd89a2ddecb4a8c6f1233cebb5f"
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
    """Validate .m3u or .m3u8 link by checking HTTP status and return with channel name."""
    channel_name, url = channel_info
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            print(f"Valid link found: {url} - {channel_name}")
            return channel_name, url
        else:
            print(f"Invalid link (Status: {response.status_code}): {url}")
    except requests.RequestException as e:
        print(f"Connection error for link {url}: {e}")
    return None

def save_links(valid_links):
    """Save validated links with channel names to .m3u file, avoiding duplicates."""
    existing_links = load_existing_links()
    new_links = []
    
    # Use a set to track channels already added in this run
    seen_channels = set(existing_links)
    
    for channel_name, link in valid_links:
        # Check for duplication based on link and channel name
        if link not in seen_channels:
            new_links.append((channel_name, link))
            seen_channels.add(link)

    # Write new links if there are any
    if new_links:
        with open(OUTPUT_FILE, "w") as f:  # Overwrite the file with new links
            for channel_name, link in new_links:
                f.write(f"#EXTINF:-1,{channel_name}\n{link}\n")

        with open(LOG_FILE, "w") as log:  # Overwrite the log file with all seen links
            log.write("\n".join(seen_channels) + "\n")

        update_readme(new_links)  # Update README with new links
        print(f"Saved {len(new_links)} new links to {OUTPUT_FILE}")
    else:
        print("No new links found to add.")

def load_existing_links():
    """Load existing links to avoid duplicates."""
    try:
        with open(LOG_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def update_readme(new_links):
    """Update README.md with newly found working channels, replacing previous entries."""
    try:
        with open(README_FILE, "r") as readme:
            lines = readme.readlines()

        # Find the "## New Working Channels Found" section in README and replace it
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

        print("README.md updated with new channels.")
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
        valid_links = list(filter(None, executor.map(validate_link, all_links)))

    # Step 4: Save only new, unique links
    save_links(valid_links)

if __name__ == "__main__":
    main()
