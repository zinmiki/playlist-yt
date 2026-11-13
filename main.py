import json
from pathlib import Path
import re
import shutil

import questionary

import utils


CONFIG_PATH = Path(__file__).with_name("config.json")
DEFAULT_OUTPUT_FOLDER = "static"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"output_folder": DEFAULT_OUTPUT_FOLDER, "playlists": []}

    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    if not isinstance(config, dict) or not isinstance(config.get("playlists"), list):
        raise ValueError("Plik config.json musi zawierać listę 'playlists'.")
    if "output_folder" not in config:
        config["output_folder"] = DEFAULT_OUTPUT_FOLDER
    if not isinstance(config["output_folder"], str) or not config["output_folder"].strip():
        raise ValueError("Pole 'output_folder' w config.json musi być niepustym tekstem.")

    return config


def show_intro() -> bool:
    print(
        "==============================\n"
        "        PLAYLIST + \n"
        "==============================\n"
        "Witaj w programie do pobieranie playlist z youtube!\n\n"

        "• Możesz tutaj pobierać dowolną playlistę wystarczy ją wybrać lub utworzyć nową wprowadzając URL z yt (Ważne: playlista musi być publiczna lub z dostempem na link. Nie może być prywatna bo nie zadziała)\n"
        "• Po wybraniu playlisty możesz pobrać/zaktualizować zawartość, wyświetlić listę lub usunąć\n"
        "• Jeśli zmienisz online zawartość playlisty (np: dodasz nowe pozycje) to musisz wejść tutaj i zaktualizować\n"
        "• Jeśli aktualizowanie nie działa lub chcesz pobrać wszystko od nowa, wybierz Usuń -> usuń tylko pliki i pobierz jeszcze raz\n"
        "• Ważne: Ten program służy wyłącznie do pobierania playlist, czyli nie możesz tutaj odsłuchać (użyj np: programu VLC, lub innego przez ciebie preferowanego).\n"
    )
    return questionary.select(
        "Naciśnij „Dalej”, aby rozpocząć:",
        choices=["Dalej"],
    ).ask() == "Dalej"


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")


def add_playlist(config: dict) -> None:
    name = questionary.text("Nazwa playlisty:").ask()
    if name is None:
        return
    name = name.strip()
    if not name:
        print("Nazwa playlisty nie może być pusta.")
        return
    if any(playlist["name"] == name for playlist in config["playlists"]):
        print(f"Playlista „{name}” już istnieje.")
        return
    folder_name = playlist_folder_name(name)
    if any(
        playlist_folder_name(playlist["name"]).casefold() == folder_name.casefold()
        for playlist in config["playlists"]
    ):
        print("Nazwa playlisty koliduje z nazwą folderu innej playlisty.")
        return

    url = questionary.text("URL playlisty:").ask()
    if url is None:
        return
    url = url.strip()
    if not url:
        print("URL playlisty nie może być pusty.")
        return

    next_index = max(
        (playlist.get("index", -1) for playlist in config["playlists"]),
        default=-1,
    ) + 1
    config["playlists"].append(
        {"name": name, "index": next_index, "url": url, "entries": []}
    )
    save_config(config)
    print(f"Dodano playlistę „{name}”.")


def list_entries(playlist: dict) -> None:
    entries = playlist.get("entries", [])
    if not entries:
        print("Brak zapisanych utworów. Wybierz „Uaktualnij/Pobierz”, aby pobrać listę.")
        return

    for entry in entries:
        position = entry.get("position", "?")
        title = entry.get("title") or "Nieznany tytuł"
        duration = entry.get("duration") or "0"

        minuty = int(duration) // 60
        sekundy = int(duration) % 60

        print(f"{position}. {title} [{minuty}:{sekundy}]")


def entry_identifier(entry: dict) -> str | None:
    return entry.get("id") or entry.get("url")


def playlist_items(entries: list[dict]) -> str:
    positions = sorted(
        {
            entry["position"]
            for entry in entries
            if isinstance(entry.get("position"), int) and entry["position"] > 0
        }
    )
    if not positions:
        return ""

    ranges = []
    start = previous = positions[0]
    for position in positions[1:]:
        if position == previous + 1:
            previous = position
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = position
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def playlist_folder_name(name: str) -> str:
    folder_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if not folder_name:
        folder_name = "playlist"
    return folder_name


def playlist_output_folder(config: dict, playlist: dict) -> Path:
    output_folder = Path(config.get("output_folder", DEFAULT_OUTPUT_FOLDER)).expanduser()
    if not output_folder.is_absolute():
        output_folder = CONFIG_PATH.parent / output_folder
    return output_folder / playlist_folder_name(playlist["name"])


def remove_playlist_files(config: dict, playlist: dict) -> None:
    output_folder = playlist_output_folder(config, playlist)
    if output_folder.is_symlink():
        raise OSError(f"Katalog playlisty jest dowiązaniem symbolicznym: {output_folder}")
    if output_folder.exists():
        if not output_folder.is_dir():
            raise NotADirectoryError(
                f"Ścieżka plików playlisty nie jest katalogiem: {output_folder}"
            )
        shutil.rmtree(output_folder)


def delete_playlist(config: dict, playlist: dict) -> None:
    remove_playlist_files(config, playlist)
    config["playlists"].remove(playlist)
    save_config(config)
    print("Usunięto pliki playlisty i samą playlistę.")


def update_playlist(config: dict, playlist: dict) -> None:
    url = playlist.get("url")
    if not url:
        print("Ta playlista nie ma zapisanego URL. Dodaj ją ponownie z adresem.")
        return

    old_entries = playlist.get("entries", [])
    new_entries = utils.playlist(url)
    old_by_id = {
        identifier: entry
        for entry in old_entries
        if (identifier := entry_identifier(entry)) is not None
    }
    new_by_id = {
        identifier: entry
        for entry in new_entries
        if (identifier := entry_identifier(entry)) is not None
    }
    added = [
        entry
        for entry in new_entries
        if entry_identifier(entry) is None
        or entry_identifier(entry) not in old_by_id
    ]
    removed = [
        entry
        for entry in old_entries
        if entry_identifier(entry) is not None
        and entry_identifier(entry) not in new_by_id
    ]
    renamed = [
        (old_by_id[identifier], entry)
        for identifier, entry in new_by_id.items()
        if identifier in old_by_id
        and old_by_id[identifier].get("title") != entry.get("title")
    ]

    if added:
        items = playlist_items(added)
        if not items:
            print("Nie można pobrać nowych filmów: brak ich pozycji na playliście.")
            return
        print(f"Nowe filmy: {len(added)}. Pobieranie pozycji: {items}")
        utils.download(url, items, str(playlist_output_folder(config, playlist)))
    else:
        print("Brak nowych filmów do pobrania.")

    if removed:
        print(f"Usunięte z playlisty online: {len(removed)}")
    if renamed:
        print(f"Zmienione tytuły: {len(renamed)}")

    playlist["entries"] = new_entries
    save_config(config)


def handle_playlist(config: dict, playlist: dict) -> None:
    is_empty = not playlist.get("entries", [])
    update_action = "Pobierz" if is_empty else "Uaktualnij"
    action = questionary.select(
        f"Wybierz akcję dla playlisty {playlist['name']}:",
        choices=[update_action, "Lista", "Usuń", "Anuluj"],
    ).ask()

    if action in (None, "Anuluj"):
        return

    if action == update_action:
        update_playlist(config, playlist)
        return

    if action == "Lista":
        list_entries(playlist)
        return

    if action == "Usuń" and is_empty:
        confirmed = questionary.confirm(
            f"Playlista „{playlist['name']}” jest pusta. Czy na pewno ją usunąć?",
            default=False,
        ).ask()
        if confirmed:
            delete_playlist(config, playlist)
        return

    if action == "Usuń":
        delete_action = questionary.select(
            f"Co usunąć z playlisty „{playlist['name']}”?",
            choices=["Tylko pliki", "Playlistę i pliki", "Anuluj"],
        ).ask()
        if delete_action in (None, "Anuluj"):
            return

        if delete_action == "Tylko pliki":
            confirmed = questionary.confirm(
                f"Czy na pewno usunąć pobrane pliki playlisty „{playlist['name']}”?",
                default=False,
            ).ask()
            if confirmed:
                remove_playlist_files(config, playlist)
                playlist["entries"] = []
                save_config(config)
                print("Usunięto pliki playlisty.")
            return

        confirmed = questionary.confirm(
            f"Czy na pewno usunąć playlistę „{playlist['name']}” i jej pliki?",
            default=False,
        ).ask()
        if confirmed:
            delete_playlist(config, playlist)


def main() -> None:
    print(
        "==============================\n"
        "        PLAYLIST + \n"
        "==============================\n"
    )
    first_run = not CONFIG_PATH.exists()
    config = load_config()
    if first_run:
        if not show_intro():
            return
        save_config(config)

    while True:
        choices = [
            questionary.Choice(playlist["name"], value=index)
            for index, playlist in enumerate(config["playlists"])
        ]
        choices.extend(
            [
                questionary.Choice("+ Nowa", value="new"),
                questionary.Choice("Wyjście", value="exit"),
            ]
        )
        selected = questionary.select(
            "Wybierz playlistę:",
            choices=choices,
        ).ask()

        if selected in (None, "exit"):
            return
        if selected == "new":
            add_playlist(config)
        else:
            handle_playlist(config, config["playlists"][selected])


if __name__ == "__main__":
    main()