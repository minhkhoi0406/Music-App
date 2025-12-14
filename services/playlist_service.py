from datetime import datetime
from bson import ObjectId
from database.mongo_connection import get_db
from pymongo.errors import DuplicateKeyError  # Import để xử lý lỗi trùng lặp

DB = get_db()
PLAYLISTS = DB.playlists
SONGS = DB.songs


def create_playlist(name: str, song_ids: list = None):
    """Tạo một playlist mới."""
    song_ids = song_ids or []
    doc = {
        "name": name,
        "song_ids": [ObjectId(s) for s in song_ids if ObjectId.is_valid(s)],
        "created_at": datetime.utcnow(),
    }
    # Thêm xử lý lỗi trùng tên tại đây
    try:
        res = PLAYLISTS.insert_one(doc)
        return str(res.inserted_id)
    except DuplicateKeyError:
        raise ValueError(f"Tên playlist '{name}' đã tồn tại.")


def get_playlists():
    """Lấy tất cả các playlist, sắp xếp theo thời gian tạo mới nhất."""
    return [p for p in PLAYLISTS.find().sort("created_at", -1)]


def get_playlist(playlist_id: str):
    """Lấy thông tin chi tiết của một playlist dựa trên ID."""
    if not ObjectId.is_valid(playlist_id):
        return None
    return PLAYLISTS.find_one({"_id": ObjectId(playlist_id)})


def update_playlist(playlist_id: str, data: dict):
    """Cập nhật thông tin của một playlist (chung)."""
    if not ObjectId.is_valid(playlist_id):
        return 0

    data["updated_at"] = datetime.utcnow()

    if "song_ids" in data:
        data["song_ids"] = [ObjectId(s) for s in data["song_ids"] if ObjectId.is_valid(s)]

    res = PLAYLISTS.update_one({"_id": ObjectId(playlist_id)}, {"$set": data})
    return res.modified_count


# HÀM MỚI: DÙNG ĐỂ SỬA TÊN VÀ XỬ LÝ LỖI TRÙNG TÊN RÕ RÀNG HƠN
def update_playlist_name(playlist_id: str, new_name: str):
    """Cập nhật tên của một playlist và xử lý lỗi trùng lặp."""
    if not ObjectId.is_valid(playlist_id):
        raise ValueError("ID Playlist không hợp lệ.")

    try:
        res = PLAYLISTS.update_one(
            {"_id": ObjectId(playlist_id)},
            {"$set": {"name": new_name, "updated_at": datetime.utcnow()}}
        )
        return res.modified_count

    except DuplicateKeyError:
        # Xử lý khi tên đã tồn tại trong DB (nếu bạn có index unique cho trường 'name')
        raise ValueError(f"Tên playlist '{new_name}' đã tồn tại. Vui lòng chọn tên khác.")
    except Exception as e:
        # Bắt các lỗi database khác
        raise Exception(f"Lỗi database khi cập nhật tên: {e}")


def delete_playlist(playlist_id: str):
    """Xóa một playlist."""
    if not ObjectId.is_valid(playlist_id):
        return 0
    res = PLAYLISTS.delete_one({"_id": ObjectId(playlist_id)})
    return res.deleted_count


def add_songs_to_playlist(playlist_id: str, song_id_list: list):
    """
    Thêm danh sách ID bài hát (string) vào playlist.
    Sử dụng $addToSet để tránh trùng lặp.
    """
    if not ObjectId.is_valid(playlist_id):
        return 0

    if not song_id_list:
        return 0

    object_ids = [ObjectId(s) for s in song_id_list if ObjectId.is_valid(s)]

    if not object_ids:
        return 0

    res = PLAYLISTS.update_one(
        {"_id": ObjectId(playlist_id)},
        {"$addToSet": {"song_ids": {"$each": object_ids}}}
    )
    return res.modified_count


def remove_song_from_playlist(playlist_id: str, song_id: str):
    """
    Xóa một bài hát khỏi danh sách song_ids của playlist.
    """
    if not ObjectId.is_valid(playlist_id) or not ObjectId.is_valid(song_id):
        return 0

    res = PLAYLISTS.update_one(
        {"_id": ObjectId(playlist_id)},
        {"$pull": {"song_ids": ObjectId(song_id)}}
    )
    return res.modified_count


def get_songs_in_playlist(playlist_id: str) -> list:
    # ... (giữ nguyên, vì nó hoạt động tốt)
    if not ObjectId.is_valid(playlist_id):
        return []

    playlist_doc = PLAYLISTS.find_one(
        {"_id": ObjectId(playlist_id)},
        {"song_ids": 1}
    )

    if not playlist_doc:
        return []

    raw_song_ids = playlist_doc.get('song_ids', [])

    song_object_ids = []
    for id_entry in raw_song_ids:
        if isinstance(id_entry, ObjectId):
            song_object_ids.append(id_entry)
        elif isinstance(id_entry, str) and ObjectId.is_valid(id_entry):
            song_object_ids.append(ObjectId(id_entry))

    if not song_object_ids:
        return []

    detailed_songs = list(SONGS.find({"_id": {"$in": song_object_ids}}))

    song_map = {str(s['_id']): s for s in detailed_songs}

    sorted_songs = []
    for oid in song_object_ids:
        song_id_str = str(oid)
        if song_id_str in song_map:
            sorted_songs.append(song_map[song_id_str])

    return sorted_songs