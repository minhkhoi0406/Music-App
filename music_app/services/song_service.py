from datetime import datetime
from bson import ObjectId
from database.mongo_connection import get_db
import shutil
from pathlib import Path
import os

# Khởi tạo DB ngay khi file service được import
DB = get_db()
SONGS = DB.songs

# Định nghĩa các thư mục
MUSIC_DIR = Path(__file__).parents[1] / "music"
COVERS_DIR = Path(__file__).parents[1] / "assets" / "covers"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)


def create_song(title: str, artist: str, album: str, file_path: str, cover_path: str = None):
    try:
        # Xử lý copy file nhạc
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError("Music file not found")
        dest = MUSIC_DIR / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(str(src), str(dest))

        cover_dest_name = None
        # Xử lý copy cover
        if cover_path:
            cover_src = Path(cover_path)
            if cover_src.exists():
                cover_dest = COVERS_DIR / cover_src.name
                if cover_src.resolve() != cover_dest.resolve():
                    shutil.copy2(str(cover_src), str(cover_dest))
                cover_dest_name = str(cover_dest.name)

        doc = {
            "title": title,
            "artist": artist,
            "album": album,
            "path": str(dest.name),  # Chỉ lưu tên file
            "cover": cover_dest_name,  # Chỉ lưu tên file cover
            "play_count": 0,
            "created_at": datetime.utcnow(),
        }
        res = SONGS.insert_one(doc)
        return str(res.inserted_id)
    except Exception:
        raise


def get_songs(filter_q: dict = None):
    filter_q = filter_q or {}
    docs = SONGS.find(filter_q).sort("created_at", -1)
    return [doc for doc in docs]


def get_song(song_id: str):
    return SONGS.find_one({"_id": ObjectId(song_id)})


def update_song(song_id: str, data: dict):
    data["updated_at"] = datetime.utcnow()
    res = SONGS.update_one({"_id": ObjectId(song_id)}, {"$set": data})
    return res.modified_count


def delete_song(song_id: str):
    doc = get_song(song_id)
    if not doc:
        return 0
    res = SONGS.delete_one({"_id": ObjectId(song_id)})
    return res.deleted_count


def increment_play_count(song_id: str):
    SONGS.update_one({"_id": ObjectId(song_id)}, {"$inc": {"play_count": 1}})