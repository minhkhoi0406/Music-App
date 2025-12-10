from datetime import datetime
from bson import ObjectId
from database.mongo_connection import get_db

DB = get_db()
PLAYLISTS = DB.playlists


def create_playlist(name: str, song_ids: list = None):
    song_ids = song_ids or []
    doc = {
        "name": name,
        "song_ids": [ObjectId(s) for s in song_ids],
        "created_at": datetime.utcnow(),
    }
    res = PLAYLISTS.insert_one(doc)
    return str(res.inserted_id)


def get_playlists():
    return [p for p in PLAYLISTS.find().sort("created_at", -1)]


def get_playlist(playlist_id: str):
    return PLAYLISTS.find_one({"_id": ObjectId(playlist_id)})


def update_playlist(playlist_id: str, data: dict):
    data["updated_at"] = datetime.utcnow()
    if "song_ids" in data:
        data["song_ids"] = [ObjectId(s) for s in data["song_ids"]]
    res = PLAYLISTS.update_one({"_id": ObjectId(playlist_id)}, {"$set": data})
    return res.modified_count


def delete_playlist(playlist_id: str):
    res = PLAYLISTS.delete_one({"_id": ObjectId(playlist_id)})
    return res.deleted_count
