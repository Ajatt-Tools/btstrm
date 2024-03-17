# btstrm - BitTorrent Streaming Program

`btstrm` is a Python program that allows you to stream torrents directly from the command line. It provides a seamless streaming experience by leveraging the power of BitTorrent and integrating with popular media players.

## Features

- Stream torrents directly without waiting for the entire download to complete
- Search for torrents using multiple indexers through `Jackett` integration
- Fetch movie titles and posters from The Movie Database (TMDB)
- Interactive selection of torrents and movie titles using `fzf`
- Automatic detection and use of available media players (`omxplayer`, `mpv`, `vlc`)
- Option to keep downloaded files after streaming
- Integration with [`impd`](https://github.com/ajatt-tools/impd) for condensing videos for language learning
- Real-time display of download progress and peer information
- Support for multiple languages and configurable settings

## Prerequisites

Before using `btstrm`, ensure that you have the following dependencies installed:

- Python 3.x
- `btfs` (BitTorrent Filesystem)
- `fzf` (fuzzy finder)
- `Jackett` (for torrent indexer integration)
- `impd` (**optional**, for language immersion enthusiasts)
- `chafa` (for displaying movie posters)
- Required Python packages: `requests`, `tqdm`, `colorama`, `beautifulsoup4`, `unidecode`

## Installation via PyPi

```bash
pipx install btstrm
```

### Manual installation

1. Clone the repository or download the `btstrm.py` file.

2. Install the required Python packages:
   ```
   pip install requests tqdm colorama beautifulsoup4 unidecode
   ```

3. Install btfs, fzf, and Jackett by following their respective installation instructions.

4. Configure Jackett and obtain the API key.

5. Create a configuration file named `btstrm.conf` in the `~/.config` directory with the following content:
   ```
   [DEFAULT]
   LANG = es-ES
   JACKETT_API_KEY = your_jackett_api_key
   JACKETT_URL = http://127.0.0.1:9117
   ```
   Replace `your_jackett_api_key` with your actual Jackett API key and adjust the `JACKETT_URL` if necessary.

   You can omit this step because `btstrm` creates configuration file automatically.

## Usage

To use `btstrm`, run the following command:

```
python btstrm.py [options] [URI]
```

Options:
- `-p PLAYER`, `--player PLAYER`: Specify the media player to use for streaming (default: auto-detect)
- `-k`, `--keep`: Keep the downloaded files after streaming (default: delete files)
- `-i`, `--impd`: Add the downloaded files to impd playlist (default: disabled)
- `-t TITLE`, `--title TITLE`: Search for alternative movie titles and select using fzf

URI:
- Video/audio content name, magnet link or torrent file

Examples:
```
python btstrm.py -p mpv -k magnet:?xt=urn:btih:example
python btstrm.py -t "Movie Title"
python btstrm.py "Big Buck Bunny"
```

## Configuration

The `btstrm.conf` file allows you to customize the following settings:

- `LANG`: Set the language code for TMDB searches (default: es-ES)
- `JACKETT_API_KEY`: Set your Jackett API key
- `JACKETT_URL`: Set the URL of your Jackett server (default: http://127.0.0.1:9117)

## Contributing

Contributions to `btstrm` are welcome! If you find any bugs, have feature requests, or want to contribute improvements, please open an issue or submit a pull request on the GitHub repository.

## Acknowledgements

`btstrm` was inspired by the need for a simple and efficient way to stream torrents from the command line. It wouldn't have been possible without the following projects:

- btfs: https://github.com/johang/btfs
- fzf: https://github.com/junegunn/fzf
- Jackett: https://github.com/Jackett/Jackett
- The Movie Database: https://www.themoviedb.org/

## Disclaimer

Please note that streaming copyrighted content without permission is illegal in many jurisdictions. The authors of `btstrm` do not condone or encourage the illegal use of this software. Use it responsibly and respect the rights of content creators.
