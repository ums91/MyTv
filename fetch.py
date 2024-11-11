import os

# Paths for the m3u files
source_file_path = 'ums91/MyTv/in.m3u'  # Source file with the new links
target_file_path = 'ums91/umsiptv/streams/index.m3u'  # Target file to update

def add_m3u_links():
    # Check if the source file exists
    if not os.path.exists(source_file_path):
        print(f"Source file {source_file_path} does not exist.")
        return

    # Read the content of the source file (in.m3u)
    with open(source_file_path, 'r') as source_file:
        new_links = source_file.readlines()

    # Read the current content of the target file (index.m3u)
    if os.path.exists(target_file_path):
        with open(target_file_path, 'r') as target_file:
            existing_links = target_file.readlines()
    else:
        existing_links = []

    # Add new links at the top
    updated_links = new_links + existing_links

    # Write the updated links back to the target file
    with open(target_file_path, 'w') as target_file:
        target_file.writelines(updated_links)

    print(f"Successfully added {len(new_links)} new links to {target_file_path}.")

# Run the function to add the links
add_m3u_links()
