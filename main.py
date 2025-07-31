import os
import re
import subprocess
import tempfile
from pathlib import Path

os.environ["translators_default_region"] = "EN"

import translators
import webvtt
import yt_dlp


def _get_url_info(url: str):
    ydl_opts = {
        "cookiesfrombrowser": ("chrome",),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False, process=False)


def download_url(url: str):
    ydl_opts = {
        "writesubtitles": True,
        "subtitleslangs": ["fr"],
        "writeautomaticsub": True,
        "cookiesfrombrowser": ("chrome",),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def translate_subtitles(fname: str, delimiter="\n"*3):
    subtitles = webvtt.read(fname)
    subtitle_texts = [caption.text.replace("&nbsp;", "") for caption in subtitles]

    translated = []
    for chunk in _chunk_subtitles(subtitle_texts, delimiter):
        merged_chunk = delimiter.join(chunk)
        translated_chunk = translators.translate_text(merged_chunk, translator="google", from_language="fr")
        translated += translated_chunk.split(delimiter)

    assert len(subtitles) == len(translated)
    for (caption, new_text) in zip(subtitles, translated):
        caption.lines = new_text.splitlines()

    return subtitles


def _chunk_subtitles(subtitle_texts, delimiter):
    chunk, char_count = [], 0
    for txt in subtitle_texts:
        if char_count + len(txt) + (len(chunk) - 1) * len(delimiter) > translators.server.GoogleV2().input_limit:
            yield chunk
            chunk, char_count = [], 0
        chunk.append(txt)
        char_count += len(txt)
    if chunk:
        yield chunk


def main(url: str):

    vid_dir = _get_all_files(url)
    video_path = _get_file_with_filetype(vid_dir, "webm")
    os.chdir(vid_dir)
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(b"UP cycle secondary-sid")
        fp.flush()
        subprocess.run(f"mpv --sub-files=fr.vtt:en.vtt --secondary-sid=2 --input-conf=\"{fp.name}\" \"{video_path}\"", shell=True)


def _get_all_files(url: str):
    curdir = Path(os.getcwd())
    info = _get_url_info(url)
    video_dir = curdir / "videos" / info["title"]
    video_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(video_dir)

    download_url(url)
    foreign_subtitles_path = _get_file_with_filetype(video_dir, "fr.vtt")
    native_subtitles = translate_subtitles(foreign_subtitles_path)
    native_subtitles_path = video_dir / "en.vtt"
    native_subtitles.save(str(native_subtitles_path))

    foreign_subtitles_path.rename(video_dir / "fr.vtt")

    return video_dir


def _get_file_with_filetype(dir_path: Path, filetype: str):
    files = list(dir_path.glob(f"*.{filetype}"))
    assert len(files) == 1
    return files[0]


def _extract_id_from_path(url: str):
    pattern = r"youtube\.com\/watch\?v=(.*?)(&.*)?$"
    id_ = re.search(pattern, url).group(1)
    return id_


if __name__ == '__main__':
    test_url = "https://www.youtube.com/watch?v=KFv8aqRdlqk"
    main(test_url)
