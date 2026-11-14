import yt_dlp, os

download_index = 0

def progress_hook(data):
    global download_index

    info = data.get("info_dict", {})

    if data["status"] == "downloading":
        if not info.get("_title_printed"):
            download_index += 1

            total = info.get("n_entries", "?")
            title = info.get("title", "Nieznany tytuł")

            print(f" | [{download_index}/{total}] {title}")
            info["_title_printed"] = True

def playlist(url: str) -> list[dict]:
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": False
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    videos = []

    for index, video in enumerate(info.get("entries", []), start=1):
        if video is None:
            continue

        videos.append({
            "position": index,
            "id": video.get("id"),
            "title": video.get("title"),
            "url": video.get("url"),
            "duration": video.get("duration"),
            "thumbnail": video.get("thumbnails", [{}])[-1].get("url")
                if video.get("thumbnails") else None
        })

    return videos

def download(url: str, items: str, output_folder: str = "static") -> None:
    global download_index

    download_index = 0

    folder = output_folder
    os.makedirs(folder, exist_ok=True)

    options = {
        "format": "bestaudio",
        "outtmpl": os.path.join(folder, "%(playlist_index)s - %(title)s.%(ext)s"),
        "playlist_items": items,
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
    }

    if os.path.isfile("cookies.txt"):
        options["cookiefile"] = "cookies.txt"

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    print("Zakończono pobieranie!")
