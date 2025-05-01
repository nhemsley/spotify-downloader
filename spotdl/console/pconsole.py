"""
REPL-style console module for interactive downloads.
"""

import logging
import sys
from typing import List

from spotdl.download.downloader import Downloader
from spotdl.utils.search import get_simple_songs

__all__ = ["pconsole"]

logger = logging.getLogger(__name__)


def pconsole(
    query: List[str],  # This will be ignored as we read from stdin
    downloader: Downloader,
) -> None:
    """
    Run an interactive REPL-style console that reads from tty and downloads URLs.
    
    ### Arguments
    - query: list of strings (ignored in pconsole mode)
    - downloader: Downloader instance
    """
    
    # Get settings from downloader
    use_artist_album_structure = downloader.settings.get("structured", False)
    replace_spaces = downloader.settings.get("replace_spaces", False)
    
    # Store original settings to restore later
    original_output = downloader.settings["output"]
    
    # Override output template if -s flag was used
    if use_artist_album_structure:
        downloader.settings["output"] = "{artist}/{album}/{title}"
        logger.info("Using artist/album folder structure for downloads")
        
    # Set up a custom formatter if -r flag was used
    if replace_spaces:
        # Define a local function to replace spaces in filenames with hyphens
        def space_replacer(filename):
            if not filename:
                return filename
                
            # Replace spaces only in the filename part (not in the directory path)
            parts = filename.split('/')
            parts[-1] = parts[-1].replace(' ', '-')
            return '/'.join(parts)
            
        # Store the function in the downloader settings
        downloader.settings["space_replacer"] = space_replacer
        
        # We'll apply this in the download process instead of setting it as formatter
        # because the formatter API might not be stable
        logger.info("Replacing spaces with hyphens in filenames")
    
    print("Welcome to spotDL pconsole. Enter Spotify URLs to download (Ctrl+D to exit).")
    print("Currently supporting album links only.")
    print("Type 'help' to see available commands.")
    
    # Print info about current settings
    options = []
    if use_artist_album_structure:
        options.append("-s (artist/album structure)")
    if replace_spaces:
        options.append("-r (replace spaces)")
    
    if options:
        print(f"Active options: {', '.join(options)}")
    
    def show_help():
        print("\nAvailable commands:")
        print("  help             Show this help message")
        print("  exit, quit       Exit pconsole")
        print("  <spotify-url>    Download from the given Spotify album URL")
        print("\nCurrent settings:")
        print(f"  Output folder structure: {'artist/album' if use_artist_album_structure else 'default'}")
        print(f"  Space replacement: {'hyphens' if replace_spaces else 'none'}")
        print(f"  Output format: {downloader.settings.get('format', 'mp3')}")
        print("\nUsage examples:")
        print("  spotdl pconsole -s     # Use artist/album folder structure")
        print("  spotdl pconsole -r     # Replace spaces with hyphens")
        print("  spotdl pconsole -sr    # Use both options together")
    
    try:
        while True:
            # Read input from user
            sys.stdout.write("> ")
            sys.stdout.flush()
            url = sys.stdin.readline().strip()
            
            if not url:
                continue
                
            # Echo back the URL so it remains visible
            print(f"Input: {url}")
                
            if url.lower() in ["exit", "quit"]:
                break
                
            if url.lower() == "help":
                show_help()
                continue
                
            # Process the URL
            if "album" in url and "open.spotify.com" in url:
                logger.info(f"Processing album: {url}")
                
                # Use the same logic as the download command
                songs = get_simple_songs(
                    [url],
                    use_ytm_data=downloader.settings["ytm_data"],
                    playlist_numbering=downloader.settings["playlist_numbering"],
                    albums_to_ignore=downloader.settings["ignore_albums"],
                    album_type=downloader.settings["album_type"],
                    playlist_retain_track_cover=downloader.settings["playlist_retain_track_cover"],
                )
                
                # Create a wrapper for download_multiple_songs if we need to replace spaces
                if replace_spaces:
                    # Override the file path during download when using -r
                    original_download_song_to_file = downloader.download_song_to_file
                    
                    def download_song_to_file_wrapper(song, file_path, *args, **kwargs):
                        # Apply space replacement to file_path
                        if file_path and "space_replacer" in downloader.settings:
                            file_path = downloader.settings["space_replacer"](file_path)
                            
                        return original_download_song_to_file(song, file_path, *args, **kwargs)
                    
                    # Replace the method temporarily
                    downloader.download_song_to_file = download_song_to_file_wrapper
                
                # Download the songs
                downloader.download_multiple_songs(songs)
                
                # Restore original download method if we replaced it
                if replace_spaces:
                    downloader.download_song_to_file = original_download_song_to_file
            else:
                logger.error("Currently only supporting Spotify album links")
                
    except (KeyboardInterrupt, EOFError):
        print("\nExiting pconsole mode.")
    finally:
        # Restore original output template if it was changed
        if use_artist_album_structure:
            downloader.settings["output"] = original_output
            
        # Remove the space_replacer if it was added
        if replace_spaces and "space_replacer" in downloader.settings:
            del downloader.settings["space_replacer"]