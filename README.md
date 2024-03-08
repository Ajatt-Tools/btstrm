# btstrm
stream torrents without soy webtorrent (and with some features)

This script based on btfs' `btplay` command and qbittorrent's jackett search add-on.

It handles magnets, torrent files and search queries (that work through Jackett API).

### Installation
```bash
yay -Syu python btfs jackett chafa fzf curl base-devel --needed 
# setup jackett and get its API key
git clone https://github.com/asakura42/btstrm
cd btstrm
# modify language and jackett api key in btstrm.py
python btstrm.py --help   
```

#TODO write this readme
