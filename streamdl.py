import os
import re
import subprocess
import time

import qbittorrentapi
import requests
from dotenv import load_dotenv


# --- Config helpers ---
def _require_env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


load_dotenv()

# --- Config ---
TMDB_API_KEY = _require_env("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
TORRENTIO_BASE = os.environ.get("TORRENTIO_BASE", "https://torrentio.strem.fun")
QB_HOST = os.environ.get("QB_HOST", "http://localhost:8080")
QB_USER = _require_env("QB_USER")
QB_PASS = _require_env("QB_PASS")
DOWNLOAD_DIR = _require_env("DOWNLOAD_DIR", "/home/chris/downloads/streamdl")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

client = qbittorrentapi.Client(host=QB_HOST, username=QB_USER, password=QB_PASS)
client.auth_log_in()


# --- Helpers ---
def pick(prompt, options):
    while True:
        try:
            choice = int(input(prompt))
            if 0 <= choice < len(options):
                return options[choice]
            print(f"Pick between 0 and {len(options) - 1}")
        except ValueError:
            print("Enter a number")


def get(url, **kwargs):
    try:
        res = requests.get(url, timeout=10, **kwargs)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


# --- Search ---
def search(query):
    params = {"api_key": TMDB_API_KEY, "query": query}
    data = get(TMDB_BASE + "/search/multi", params=params)
    if not data:
        return []
    clean = []
    for item in data["results"]:
        if item["media_type"] not in ("movie", "tv"):
            continue
        ext = get(
            TMDB_BASE + f"/{item['media_type']}/{item['id']}/external_ids",
            params=params,
        )
        if not ext or not ext.get("imdb_id"):
            continue
        clean.append(
            {
                "title": item.get("title") or item.get("name"),
                "year": (item.get("release_date") or item.get("first_air_date") or "")[
                    :4
                ],
                "type": item["media_type"],
                "imdb_id": ext["imdb_id"],
            }
        )
    return clean


def display_and_select(results):
    for i, item in enumerate(results):
        print(f"{i}. {item['title']} ({item['year']}) [{item['type']}]")
    return pick("\nPick a number: ", results)


# --- Streams ---
def get_streams(item):
    if item["type"] == "movie":
        url = f"{TORRENTIO_BASE}/stream/movie/{item['imdb_id']}.json"
    else:
        season = input("Season: ")
        episode = input("Episode: ")
        url = (
            f"{TORRENTIO_BASE}/stream/series/{item['imdb_id']}:{season}:{episode}.json"
        )
    data = get(url, headers=HEADERS)
    if not data:
        raise RuntimeError("Failed to fetch streams from Torrentio")
    return data["streams"]


def parse_seeders(stream):
    match = re.search(r"👤 (\d+)", stream["title"])
    return int(match.group(1)) if match else 0


def display_and_select_stream(streams):
    for i, s in enumerate(streams):
        last_line = s["title"].split("\n")[-1]
        print(
            f"{i}. Seeders:{parse_seeders(s)} {s['name'].replace(chr(10), ' ')} | {last_line}"
        )
    return pick("\nPick a stream: ", streams)


# --- qBittorrent ---
def add_to_qbit(stream):
    magnet = f"magnet:?xt=urn:btih:{stream['infoHash']}"
    client.torrents_add(
        urls=magnet,
        save_path=DOWNLOAD_DIR,
        is_sequential_download=True,
        is_first_last_piece_priority=True,
    )
    time.sleep(2)
    torrents = client.torrents_info(hashes=stream["infoHash"])
    attempts = 0
    while (not torrents or torrents[0].name == stream["infoHash"]) and attempts < 20:
        time.sleep(3)
        attempts += 1
        torrents = client.torrents_info(hashes=stream["infoHash"])
    if attempts >= 20:
        raise TimeoutError("Torrent metadata never resolved — dead magnet?")
    torrent = torrents[0]
    print(f"Added: {torrent.name}")
    return torrent.save_path


# --- Player ---
def open_in_player(stream, save_path):
    files = client.torrents_files(torrent_hash=stream["infoHash"])
    if not files:
        raise RuntimeError("No files found in torrent")
    file_idx = stream.get("fileIdx", 0)
    if file_idx >= len(files):
        file_idx = 0
    file_path = os.path.join(save_path, files[file_idx].name)

    print(f"Waiting for file: {file_path}")
    while True:
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        print(f"Buffering... {size // (1024 * 1024)}MB / 50MB", end="\r")
        if size > 50 * 1024 * 1024:
            break
        time.sleep(3)

    print("\nOpening in VLC...")
    subprocess.Popen(["vlc", file_path])


# --- Main ---
query = input("Search: ")
results = search(query)
if not results:
    print("No results found")
    exit(1)
option = display_and_select(results)
streams = get_streams(option)
selected_stream = display_and_select_stream(streams)
save_path = add_to_qbit(selected_stream)
open_in_player(selected_stream, save_path)
