#!/usr/bin/env python3

import requests
from tqdm import tqdm
import sys
import math
import os
import os.path
import threading
import re
from colorama import Fore
import tempfile
import shutil
import time
import subprocess
from subprocess import call
import xml.etree.ElementTree as ET
import argparse
from urllib.parse import urlparse
from requests import get
from urllib.parse import quote
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from unidecode import unidecode
import configparser
import atexit

temp_files = []

# Configuration
def load_config():
    default_config = {
        'LANG': 'es-ES',
        'JACKETT_API_KEY': '',
        'JACKETT_URL': 'http://127.0.0.1:9117'
    }

    config = configparser.ConfigParser()

    config_dir = os.path.join(os.path.expanduser('~'), '.config')

    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    config_path = os.path.join(config_dir, "btstrm.conf")

    if not os.path.exists(config_path):
        print("Config file not found, creating one with default values...")

        config['DEFAULT'] = default_config

        with open(config_path, 'w') as f:
            config.write(f)

    else:

        try:
            config.read(config_path)
            for key in default_config.keys():
                if key not in config['DEFAULT']:
                    raise KeyError(f"Key {key} missing from existing configuration.")

                else:
                    value = str(config.get('DEFAULT', key))
                    globals()[key] = value


        except Exception as e:
            print(f"Error loading settings: {e}")

load_config()
extensions = ("mp4", "m4v", "mkv", "avi", "mpg", "mpeg", "flv", "webm")
home_dir = os.path.expanduser('~')
players = (
    ("omxplayer", "--timeout", "60"),
    ("mpv","--really-quiet","--cache=no"),
    # ("mpv", "--pause", "--cache=yes", "--cache-on-disk=yes", "--demuxer-thread=yes", "--demuxer-cache-dir=" + home_dir + "/.cache/mpv"),
    ("vlc", "--file-caching", "10000"),
)

# TMDB helper functions
def fetch_movie_data(search_term, language=LANG):
    QUERY = quote(search_term)
    url = f"https://www.themoviedb.org/search?query={QUERY}&language={language}"

    headers = {
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:122.0) Gecko/20100101 Firefox/122.0',
  }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch data from TMDB. Status code: {response.status_code}")
        return ""

def parse_html_for_posters_and_titles(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.select('img[loading][class="poster w-[100%]"][alt]')
    results = []
    for image in images:
        srcset = image.get('srcset').split(',')[-1].strip().split(' ')[0]
        title = image.get('alt').strip()
        results.append((srcset, title))
    return results

def search_alternative_titles(search_term):
    html_content = fetch_movie_data(search_term)
    results = parse_html_for_posters_and_titles(html_content)
    return results

def load_image(image_url):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()

    temp_filename = os.path.join(tempfile.gettempdir(), next(tempfile._get_candidate_names()) + ".jpg")

    with open(temp_filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)

    temp_files.append(temp_filename)

    return temp_filename

def load_images_threaded(urls):
    images = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(load_image, url): url for url in urls}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(urls), desc='Loading images', ncols=70):
            try:
                tmp_file_name = future.result()
                url = futures[future]
                images.append((tmp_file_name, url))
            except Exception as e:
                print(f"Error loading image: {e}")
    return sorted(images, key=lambda x: urls.index(x[1]))

def which(x):
    for d in os.getenv("PATH", "").split(":"):
        if os.path.exists(os.path.join(d, x)):
            return os.path.join(d, x)

def find_player(players):
    for player in players:
        if which(player[0]):
            return player

def find_files(filepath):
    for dirpath, dnames, fnames in os.walk(filepath):
        for f in fnames:
            yield os.path.join(dirpath, f)

def is_sample(filename):
    return "sample" in os.path.basename(filename).lower()

def is_video(filename):
    return any(filename.lower().endswith(i) for i in extensions)

def exit(tempdir, status):
    shutil.rmtree(tempdir)
    sys.exit(status)


def get_jackett_indexers():
    try:
        response = requests.get(f"{JACKETT_URL}/api/v2.0/indexers/all/results/torznab/api?apikey={JACKETT_API_KEY}&t=indexers&configured=true")
        response.raise_for_status()
        xml_response = ET.fromstring(response.content)
        indexers = [indexer.get('id') for indexer in xml_response.findall(".//indexer")]
        return indexers
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving indexers: {e}")
        return []

def search_torrents(query, indexer):
    torrents = []
    try:
        response = requests.get(f"{JACKETT_URL}/api/v2.0/indexers/{indexer}/results/torznab/api?apikey={JACKETT_API_KEY}&q={query}", timeout=20)
        response.raise_for_status()
        xml_response = ET.fromstring(response.content)

        items = xml_response.findall(".//item")

        for item in items:
            title = item.find("title").text if item.find("title") is not None else "No Title"
            link  = item.find("link").text if item.find("link") is not None else "No Link"
            seeds_str  = item.find("*[@name='seeders']").get('value') if item.find("*[@name='seeders']") is not None else "0"
            seeds_int  = int(seeds_str)
            size_bytes_str  = item.find("size").text if item.find("size") is not None else "0"
            size_bytes_int  = int(size_bytes_str)
            size_human_readable   ='%.2f GB' % (size_bytes_int / (1024*1024*1024))
            title_with_tracker_name= f'{title} [{indexer}]'
            torrents.append({'title': title_with_tracker_name, 'seeds': seeds_int , 'size': size_human_readable , 'link': link})

    except requests.exceptions.RequestException as e:
         print(f"Error searching torrents for indexer {indexer}: {e}")

    return torrents


def normalize_query(query):
    ascii_query = unidecode(query)
    return ascii_query

def search_torrents_threaded(query, indexer):
    non_ascii_letters = ['á', 'é', 'í', 'ó', 'ú',
                         'ü', 'ñ', 'ç', 'à', 'è',
                         'ì', 'ò', 'ù', 'â', 'ê',
                         'î', 'ô', 'û', 'ä', 'ë',
                         'ï', 'ö', 'ü', 'ÿ', 'ø',
                         'å', 'æ', 'œ', 'ß', 'ð',
                         'þ', 'ł', 'ž', 'š', 'ý']

    if any(letter in query for letter in non_ascii_letters):
        ascii_query = normalize_query(query)
        torrents = search_torrents(query, indexer) + search_torrents(ascii_query, indexer)
    else:
        torrents = search_torrents(query, indexer)

    torrents_unique = list({v['link']: v for v in torrents}.values())
    return torrents_unique

def call_fzf_with_results(results):
    with tempfile.NamedTemporaryFile(mode='w+', delete=True) as temp_file:
        for result in results:
            temp_file.write(f"{result['title']}\t{result['seeds']}\t{result['size']}\t{result['link']}\n")
        temp_file.flush()

        selected = subprocess.check_output(['fzf', '--height=20', '--no-sort', '--delimiter', '\t', '--with-nth', '1,2,3',
                                   "--preview", "echo {} | awk -F'\t' '{print \"\\033[1mName:\\033[0m \", $1, \"\\n\\033[1mSeeders:\\033[0m \", $2, \"\\n\\033[1mSize:\\033[0m \", $3}'", "--preview-window", "right:wrap",
                                   '-q', ''], stdin=open(temp_file.name))




        return selected.decode('utf-8').split('\t')[-1]



def scan(directory, indent=""):
    completed_files = []
    try:
        for path in sorted(os.listdir(directory)):
            absolute_path = os.path.join(directory, path)
            if os.path.isdir(absolute_path):
                completed_files.extend(scan(absolute_path, indent + "    "))
            else:
                file_stat = os.stat(absolute_path)
                progress = round(100.0 * 512.0 * file_stat.st_blocks / file_stat.st_size, 0)
                if progress == 100:
                    completed_files.append(absolute_path)
    except PermissionError:
        print("Access denied to directory: ", directory)
    return completed_files


def add_to_playlist(completed_files):
    try:
        impd_path = which("impd")
        if impd_path:
            print("Adding downloaded files into impd:")
            print(completed_files)
            call([impd_path, "add"] + completed_files)
        else:
            print("impd not found in PATH.")
    except Exception as e:
        print(f"Error: {e}")


def read_log(log_file):
    trackers = {}
    total_pieces_downloaded = 0
    first_piece_downloaded = False
    if os.path.exists(log):
        with open(log_file, 'r') as f:
            for line in f.readlines():
                match = re.search(r'\((.*?)\)\[.*?\].*?received .*?peers: (\d+)', line)
                if match:
                    tracker = match.group(1)
                    peers_count = int(match.group(2))
                    trackers[tracker] = peers_count

                if re.search(r'piece.*finished downloading', line):
                    total_pieces_downloaded += 1

                if re.search(r'piece: 0 finished downloading', line):
                    first_piece_downloaded = True

        total_peers_counts_for_unique_trackers_last_occurrence = sum(trackers.values())
        # total_downloaded_MBs = round(total_pieces_downloaded * .25,2)

        output_str=""

        if first_piece_downloaded:
            output_str=Fore.GREEN + f"Peers: {total_peers_counts_for_unique_trackers_last_occurrence}; Downloaded {total_pieces_downloaded} pieces"
        else:
            output_str=Fore.LIGHTBLACK_EX + f"Peers: {total_peers_counts_for_unique_trackers_last_occurrence}; Downloaded {total_pieces_downloaded} pieces"


        sys.stdout.write("\r"+ " "*80 + "\r"+output_str)
        sys.stdout.flush()

        threading.Timer(2, read_log, [log_file]).start() # run every 2 seconds


def cleanup(mount_point):
    with open(os.devnull, 'w') as DEVNULL:
        subprocess.call(["fusermount", "-z", "-u", mount_point], stderr=DEVNULL)


def cleanup_temp_files():
    for filepath in temp_files:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error deleting {filepath}: {e}")

atexit.register(cleanup_temp_files)

def main():
    global log
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--player", action="store", help="player to launch")
    parser.add_argument('-k', '--keep', action='store_true', help='keep files and do not delete them')
    parser.add_argument("-i", "--impd", action="store_true", help="add downloaded files into impd")
    parser.add_argument("-t", "--title", action="store", help="search for alternative titles")
    parser.add_argument("URI", nargs='?', action="store", help="magnet link or HTTP metadata URL to play", default="")
    args = parser.parse_args()

    if args.title:
        results = search_alternative_titles(args.title)
        if not results:
            print("No alternative titles found.")
            return

        poster_urls = [srcset for srcset, _ in results]
        loaded_posters = load_images_threaded(poster_urls)

        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as temp_file:
            for (srcset, title), (poster_file, _) in zip(results, loaded_posters):
                temp_file.write(f"{poster_file}\t{title}\n")
            temp_file.flush()

            selected_title = subprocess.check_output(['fzf', '--height=20', '--no-sort',
                                                      "--delimiter", '\t',
                                                      "--with-nth", '2',
                                                      "--preview", "echo {} | awk -F'\t' '{print $1}' | xargs -I{} sh -c 'chafa -s x20 --format=symbols {}'",
                                                      '-q', ''], stdin=open(temp_file.name))




            query = selected_title.decode('utf-8').strip().split('\t')[1]  # Get only the title part from selection
    elif args.URI:
        query = args.URI
        uri = args.URI
    else:
        parser.error("No input provided. Use -t to search for titles or provide a URI.")

    if not (query.startswith("magnet:") or query.endswith(".torrent") or query.startswith("http://127.0.0.1:9117")) and query:
        indexers = get_jackett_indexers()
        all_torrents = []

        with tqdm(total=len(indexers), desc='Searching torrents', ncols=70) as pbar:
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(search_torrents_threaded, query, indexer): indexer for indexer in indexers}
                for future in concurrent.futures.as_completed(futures):
                    torrents = future.result()
                    all_torrents.extend(torrents)
                    pbar.update()

            pbar.close()

        all_torrents.sort(key=lambda x: x['seeds'], reverse=True)

        if all_torrents:
             uri = call_fzf_with_results(all_torrents)
             print(uri)
        else:
             print("No torrents found.")
             return

    if uri.startswith("http://127.0.0.1:9117"):
        response = get(uri, allow_redirects=False)
        content_type = response.headers.get("Content-Type")

        if content_type == "application/x-bittorrent":
            with open("/tmp/temp.torrent", "wb") as f:
                f.write(response.content)
            uri = "/tmp/temp.torrent"
        elif "Location" in response.headers:
            uri = response.headers["Location"]

    player = find_player([args.player.split()] if args.player else players)

    if not player:
        print("Could not find a player", file=sys.stderr)
        return

    mount_dir = os.path.join(os.environ['HOME'], '.cache', 'btstrm')
    ddir = os.path.join(mount_dir, 'download')
    os.makedirs(mount_dir, exist_ok=True)
    os.makedirs(ddir, exist_ok=True)
    mountpoint = tempfile.mkdtemp(prefix="btstrm-", dir=mount_dir)

    # atexit
    atexit.register(lambda: cleanup(mountpoint))
    # atexit.register(cleanup_temp_files)



    if args.keep:
        failed=subprocess.call(["btfs","--keep",f"--data-directory={ddir}",uri,mountpoint])
    else:
        failed=subprocess.call(["btfs",f"--data-directory={ddir}",uri,mountpoint])

    if failed:
        exit(mountpoint, failed)
        return

    try:
        while not os.listdir(mountpoint):
            time.sleep(0.25)

        subdirs = [os.path.join(ddir, d) for d in os.listdir(ddir) if os.path.isdir(os.path.join(ddir, d))]
        last_created_dir = max(subdirs, key=os.path.getmtime)
        log = last_created_dir + "/log.txt"


        media = sorted(
            i for i in find_files(mountpoint) if not is_sample(i) and is_video(i)
        )

        mountpoint_removed = [m.replace(mountpoint, '') for m in media]
        file_paths = [last_created_dir + "/files" + m for m in mountpoint_removed]

        for file_path in file_paths:
            print(file_path)

        read_log(log)


        if media:
            status = subprocess.call(list(player) + media, stdin=sys.stdin)
        else:
            print("No video media found", file=sys.stderr)
            status = 3

        if media and status == 0 and args.impd:
            completed_files = scan(mountpoint)
            if completed_files:
                add_to_playlist(completed_files)
            else:
                print("No fully downloaded media found.")

    except KeyboardInterrupt:
        status = 1

    except Exception as e:
        print("Error:", e, file=sys.stderr)
        status = 2

    finally:
        subprocess.call(["fusermount", "-z", "-u", mountpoint])

    exit(mountpoint, status)
if __name__ == "__main__":
    main()
