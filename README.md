# streamdl

A minimal CLI tool to search, stream, and download movies and TV shows via torrent. Built with Python. With future integration into mind as a stremio addon. This removes the bloat between stremio's bulky addons and load times of your shows.

## How it works

1. Search for a movie or TV show by name (powered by TMDB)
2. Pick a result from the list
3. Choose a torrent source from Torrentio (same sources as Stremio addons)
4. The torrent is added to qBittorrent with sequential download enabled
5. VLC opens and starts playing once enough data has buffered

## Requirements

- Python 3.10+
- [qBittorrent](https://www.qbittorrent.org/) with Web UI enabled
- [VLC](https://www.videolan.org/)

## Installation

```bash
git clone https://github.com/youruser/streamdl
cd streamdl
pip install requests qbittorrent-api
```

## Configuration

Edit the config section at the top of `streamdl.py`:

```python
TMDB_API_KEY = "your_tmdb_api_key"
QB_HOST      = "http://localhost:8080"
QB_USER      = "admin"
QB_PASS      = "adminadmin"
DOWNLOAD_DIR = "/home/youruser/downloads/streamdl"
```

- Get a free TMDB API key at [themoviedb.org](https://www.themoviedb.org/settings/api)
- Enable qBittorrent Web UI under Tools → Preferences → Web UI

## Usage

```bash
python streamdl.py
```

```
Search: fury
0. Fury (2014) [movie]
1. Fury (2021) [tv]
...
Pick a number: 0

0. Seeders:843 Torrentio 1080p | 👤 843 💾 2.14 GB ⚙️ ThePirateBay
1. Seeders:201 Torrentio 1080p | 👤 201 💾 4.42 GB ⚙️ 1337x
...
Pick a stream: 0

Added: Fury (2014) 1080p BluRay x264
Buffering... 32MB / 50MB
Opening in VLC...
```

For TV shows, you'll also be prompted for season and episode number.

## Notes

- Sequential download is enabled by default so playback can start before the download completes
- Torrent sources and quality are sorted by Torrentio (4K → 1080p → 720p)
- Downloads are saved to `DOWNLOAD_DIR` and persist after playback

## Planned

- [ ] Subtitle auto-download via OpenSubtitles
- [ ] VLC path fix for filenames with special characters
- [ ] Config file instead of hardcoded values
- [ ] Better fuzzy search

## License

MIT
