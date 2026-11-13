# Playlist+

Playlist+ is a terminal application for keeping track of YouTube playlists and downloading their audio. It can show playlist contents, download newly added items, and remove downloaded files.

## Requirements

- Python 3.10 or newer
- Internet access
- A playlist that is public or accessible to you by link

## Installation

Install the Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Run

Start the application from the project directory:

```bash
python3 main.py
```

Alternatively, if `make` is installed:

```bash
make start
```

On the first run, follow the introduction. Use the menu to add a playlist by name and URL, then select it to update or view its contents.

## Playlist actions

- **Update/download:** Retrieves the current playlist and downloads items that are new since the previous update.
- **List:** Displays the saved track titles and durations.
- **Delete:** Remove only the downloaded files, or remove both the files and the playlist from the app.

Downloaded audio is placed in `static/<playlist name>/` by default. The downloader selects the best available audio format; the application does not play audio.

## Project files

- `main.py` — interactive menu and playlist management
- `utils.py` — playlist retrieval and audio downloading
- `requirements.txt` — Python dependencies
- `Makefile` — shortcut for starting the application
