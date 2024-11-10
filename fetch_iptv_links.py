import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# File to save working channels and keep track of duplicates
OUTPUT_FILE = "working_channels.m3u"
LOG_FILE = "channel_log.txt"
README_FILE = "README.md"

# Initial list of public IPTV playlist URLs
IPTV_SOURCES = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/countries/pk.m3u",
    "https://github.com/Free-TV/IPTV/blob/master/playlist.m3u8",
    "https://gist.github.com/didarulcseiubat17/8e643cd89a2ddecb4a8c6f1233cebb5f",
    "https://pdfcoffee.com/ipljiotvandairtel-iptv-m3u-playliststxt-4-pdf-free.html"
]

# Regex pattern for m3u8 links and channel names in EXTINF lines
M3U8_PATTERN = re.compile(r"(http[s]?://[^\s]+\.m3u8)")
EXTINF_PATTERN = re.compile(r"#EXTINF:[^\n]*,(.*)")

# Query URL for finding new IPTV links
SEARCH_QUERY_URL = "https://www.google.com/search?q=free+live+TV+channels+in+m3u8+format"

def fetch_links(playlist_url):
    """Fetch and extract .m3u8 links along with channel names from a playlist URL."""
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

def search_for_new_sources():
    """Search for additional IPTV sources."""
    try:
        response = requests.get(SEARCH_QUERY_URL, timeout=10)
        response.raise_for_status()
        new_sources = M3U8_PATTERN.findall(response.text)
        print(f"Found {len(new_sources)} new sources from search.")
        return new_sources
    except requests.RequestException as e:
        print(f"Failed to fetch search results: {e}")
        return []

def validate_link(channel_info):
    """Validate .m3u8 link by checking HTTP status and return with channel name."""
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

def load_existing_links():
    """Load existing links to avoid duplicates."""
    try:
        with open(LOG_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_links(valid_links):
    """Save validated links with channel names to .m3u file, avoiding duplicates."""
    existing_links = load_existing_links()
    new_links = [(name, link) for name, link in valid_links if link not in existing_links]

    if new_links:
        with open(OUTPUT_FILE, "a") as f:
            for channel_name, link in new_links:
                f.write(f"#EXTINF:-1,{channel_name} - {datetime.now()}\n{link}\n")

        with open(LOG_FILE, "a") as log:
            log.write("\n".join(link for _, link in new_links) + "\n")

        update_readme(new_links)  # Update README with new links

        print(f"Saved {len(new_links)} new links to {OUTPUT_FILE}")
    else:
        print("No new links found to add.")

def update_readme(new_links):
    """Update README.md with newly found working channels."""
    try:
        with open(README_FILE, "a") as readme:
            readme.write("\n## New Working Channels Found\n")
            readme.write(f"Updated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for channel_name, link in new_links:
                readme.write(f"- **{channel_name}**: [Stream Link]({link})\n")
        print("README.md updated with new channels.")
    except IOError as e:
        print(f"Error updating README.md: {e}")

def main():
    # Step 1: Load initial and new sources
    all_sources = set(IPTV_SOURCES)
    all_sources.update(search_for_new_sources())

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
