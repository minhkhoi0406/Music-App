from datetime import datetime
from bson import ObjectId
from database.mongo_connection import get_db
import shutil
from pathlib import Path
import os
import time

# === KHỞI TẠO VÀ CẤU HÌNH ===
DB = get_db()
HISTORY = DB.song_history
FAVORITES = DB.song_favorites  # Bảng lưu trữ liên kết YÊU THÍCH
SONGS = DB.songs
# Giả định: PLAYLISTS là DB.playlists (cần thiết cho các dịch vụ khác, nhưng không có trong file này)
# Nếu bạn có collection PLAYLISTS, bạn cần thêm code để xóa tham chiếu khỏi đó nữa
# PLAYLISTS = DB.playlists

# Định nghĩa các thư mục (Giả định thư mục gốc của dự án là parents[1])
MUSIC_DIR = Path(__file__).parents[1] / "music"
COVERS_DIR = Path(__file__).parents[1] / "assets" / "covers"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)


# ============================


def create_song(title: str, artist: str, album: str, file_path: str, cover_path: str = None, duration: int = 0):
    """
    Thêm bài hát mới vào Database và sao chép file.
    Ghi chú: Lưu TÊN file (path) chứ không phải đường dẫn tuyệt đối (file_path).
    """
    try:
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"Music file not found: {file_path}")

        # 1. Xử lý file nhạc
        dest = MUSIC_DIR / src.name
        # Chỉ copy nếu file nguồn và đích KHÔNG giống nhau (tránh copy chính nó)
        if src.resolve() != dest.resolve():
            shutil.copy2(str(src), str(dest))

        # 2. Xử lý ảnh bìa
        cover_dest_name = None
        if cover_path:
            cover_src = Path(cover_path)
            if cover_src.exists():
                # Tạo tên file cover duy nhất bằng timestamp + tên gốc để tránh trùng lặp
                cover_dest_name = f"{int(time.time())}_{cover_src.name}"
                cover_dest = COVERS_DIR / cover_dest_name
                shutil.copy2(str(cover_src), str(cover_dest))

        # 3. Tạo document
        doc = {
            "title": title,
            "artist": artist,
            "album": album,
            "path": str(dest.name),  # TÊN file nhạc
            "cover": cover_dest_name,  # TÊN file cover
            "duration": duration,
            "play_count": 0,
            "favorite": False,  # Mặc định là False
            "created_at": datetime.utcnow(),
        }
        res = SONGS.insert_one(doc)
        return str(res.inserted_id)
    except Exception as e:
        print(f"Error creating song: {e}")
        raise


def get_songs(filter_q: dict = None):
    """Lấy danh sách tất cả bài hát."""
    filter_q = filter_q or {}
    docs = SONGS.find(filter_q).sort("created_at", -1)
    return [doc for doc in docs]


def get_song(song_id: str):
    """Lấy thông tin một bài hát theo ID."""
    try:
        if not ObjectId.is_valid(song_id):
            return None
        return SONGS.find_one({"_id": ObjectId(song_id)})
    except:
        return None


def update_song(song_id: str, data: dict, file_path: str = None, cover_path: str = None):
    """
    Cập nhật thông tin bài hát và tùy chọn thay thế file nhạc/cover.
    """
    if not ObjectId.is_valid(song_id):
        return 0

    update_fields = data.copy()
    update_fields["updated_at"] = datetime.utcnow()

    # 1. Xử lý file nhạc mới
    if file_path and update_fields.get("duration", 0) > 0:
        src = Path(file_path)
        # Giả định chỉ xử lý đường dẫn tuyệt đối hoặc tương đối hợp lệ
        if src.is_absolute() and src.exists():
            dest = MUSIC_DIR / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(str(src), str(dest))
            update_fields["path"] = str(dest.name)

    # 2. Xử lý ảnh bìa mới
    if cover_path:
        cover_src = Path(cover_path)
        if cover_src.is_absolute() and cover_src.exists():
            cover_dest_name = f"{int(time.time())}_{cover_src.name}"
            cover_dest = COVERS_DIR / cover_dest_name
            shutil.copy2(str(cover_src), str(cover_dest))
            update_fields["cover"] = cover_dest_name  # Lưu TÊN file cover mới

    try:
        res = SONGS.update_one({"_id": ObjectId(song_id)}, {"$set": update_fields})
        return res.modified_count
    except Exception as e:
        print(f"Error updating song {song_id}: {e}")
        return 0


def delete_song(song_id: str):
    """
    Xóa bài hát khỏi DB và xóa file liên quan.
    BỔ SUNG: Xóa bản ghi khỏi FAVORITES và HISTORY để duy trì tính toàn vẹn.
    """
    if not ObjectId.is_valid(song_id):
        return 0

    obj_id = ObjectId(song_id)
    doc = get_song(song_id)

    if not doc:
        return 0

    try:
        # Xóa file nhạc
        if doc.get("path"):
            (MUSIC_DIR / doc["path"]).unlink(missing_ok=True)
        # Xóa file cover
        if doc.get("cover"):
            (COVERS_DIR / doc["cover"]).unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not delete associated files for song ID {song_id}: {e}")

    # === BỔ SUNG: XÓA THAM CHIẾU KHỎI CÁC BẢNG KHÁC ===
    # 1. Xóa khỏi danh sách YÊU THÍCH (FAVORITES)
    FAVORITES.delete_one({"song_id": obj_id})

    # 2. Xóa lịch sử nghe của bài hát này
    HISTORY.delete_many({"song_id": obj_id})

    # 3. Xóa tham chiếu khỏi PLAYLISTS (Nên được thêm vào nếu có collection PLAYLISTS)
    # Nếu bạn có collection PLAYLISTS, hãy bỏ comment dòng sau:
    # DB.playlists.update_many({}, {'$pull': {'song_ids': obj_id}})

    # === KẾT THÚC BỔ SUNG ===

    res = SONGS.delete_one({"_id": obj_id})

    return res.deleted_count


# === CHỨC NĂNG FAVORITE ===

def is_favorite(song_id: str) -> bool:
    """Kiểm tra bài hát có trong bảng FAVORITES hay không."""
    if song_id.startswith("FILE_") or not ObjectId.is_valid(song_id):
        return False
    try:
        # Tìm xem có document nào trong FAVORITES có song_id tương ứng không
        favorite_doc = FAVORITES.find_one({"song_id": ObjectId(song_id)})
        return favorite_doc is not None
    except Exception as e:
        print(f"Lỗi khi kiểm tra is_favorite: {e}")
        return False


def toggle_favorite(song_id: str):
    """
    Thêm/Xóa liên kết bài hát vào/khỏi bảng FAVORITES và đồng bộ trạng thái trong SONGS.
    Trả về trạng thái yêu thích MỚI (True nếu đã thêm, False nếu đã xóa).
    """
    if song_id.startswith("FILE_") or not ObjectId.is_valid(song_id):
        return False

    try:
        obj_id = ObjectId(song_id)

        # 1. Kiểm tra trạng thái hiện tại (dựa trên collection FAVORITES)
        if is_favorite(song_id):
            # A. ĐANG YÊU THÍCH -> XÓA (UNFAVORITE)

            # XÓA KHỎI BẢNG FAVORITES (Nơi lưu danh sách)
            FAVORITES.delete_one({"song_id": obj_id})

            # ĐỒNG BỘ: Cập nhật trạng thái 'favorite' trong SONGS thành False (Nơi lưu trạng thái UI)
            SONGS.update_one({"_id": obj_id}, {"$set": {"favorite": False}})

            return False  # Trạng thái mới: KHÔNG yêu thích
        else:
            # B. CHƯA YÊU THÍCH -> THÊM (FAVORITE)

            # THÊM VÀO BẢNG FAVORITES
            doc = {
                "song_id": obj_id,
                "added_at": datetime.utcnow()
            }
            FAVORITES.insert_one(doc)

            # ĐỒNG BỘ: Cập nhật trạng thái 'favorite' trong SONGS thành True
            SONGS.update_one({"_id": obj_id}, {"$set": {"favorite": True}})

            return True  # Trạng thái mới: YÊU THÍCH

    except Exception as e:
        print(f"Lỗi khi toggle favorite: {e}")
        return False


def get_favorite_songs():
    """
    Lấy danh sách bài hát yêu thích bằng cách JOIN (sử dụng $lookup hoặc 2 bước truy vấn).
    """
    try:
        # 1. Lấy tất cả các liên kết song_id từ bảng FAVORITES
        favorite_docs = list(FAVORITES.find().sort("added_at", -1))

        if not favorite_docs:
            return []

        song_ids = [doc["song_id"] for doc in favorite_docs]

        # 2. Truy vấn chi tiết bài hát từ bảng SONGS
        songs = list(SONGS.find({"_id": {"$in": song_ids}}))

        # Chuyển kết quả thành Map để dễ dàng ghép lại theo thứ tự thêm vào yêu thích
        song_map = {s["_id"]: s for s in songs}

        result = []
        for fav_doc in favorite_docs:
            song = song_map.get(fav_doc["song_id"])
            if song:
                result.append(song)

        return result

    except Exception as e:
        print(f"Lỗi khi lấy bài hát yêu thích: {e}")
        return []


# === CHỨC NĂNG HISTORY ===

def increment_play_count(song_id: str):
    """Tăng số lần phát bài hát."""
    if not ObjectId.is_valid(song_id):
        return
    try:
        SONGS.update_one({"_id": ObjectId(song_id)}, {"$inc": {"play_count": 1}})
    except Exception as e:
        print(f"Lỗi tăng play count: {e}")


# Trong file song_service.py (hoặc nơi định nghĩa hàm này)

def add_song_to_history(song_id: str):
    """
    Ghi lại 1 lần nghe nhạc.
    """
    if not ObjectId.is_valid(song_id):
        return

    try:
        HISTORY.insert_one({
            "song_id": ObjectId(song_id),
            "played_at": datetime.utcnow()
        })
    except Exception as e:
        print(f"Lỗi ghi lịch sử nghe nhạc: {e}")


def get_song_history(limit: int = 50):
    """
    Lấy danh sách bài hát nghe gần nhất.
    Sử dụng $in để tối ưu truy vấn.
    """
    try:
        history_docs = list(
            HISTORY.find().sort("played_at", -1).limit(limit)
        )

        if not history_docs:
            return []

        # 1. Lấy tất cả song_id duy nhất từ lịch sử
        song_ids = list(set(h["song_id"] for h in history_docs))

        # 2. Truy vấn tất cả thông tin bài hát cần thiết trong 1 lần
        songs = list(SONGS.find({"_id": {"$in": song_ids}}))
        song_map = {s["_id"]: s for s in songs}

        # 3. Gộp lịch sử và thông tin bài hát theo thứ tự chơi
        result = []
        for h in history_docs:
            sid = h["song_id"]
            if sid in song_map:
                song = song_map[sid].copy()  # Dùng .copy() để tránh thay đổi bản ghi gốc trong map
                song["played_at"] = h["played_at"]
                result.append(song)

        return result

    except Exception as e:
        print(f"Lỗi lấy lịch sử nghe nhạc: {e}")
        # Không throw e, trả về list rỗng nếu lỗi
        return []


def clear_song_history():
    """Xoá toàn bộ lịch sử nghe nhạc."""
    try:
        HISTORY.delete_many({})
    except Exception as e:
        print(f"Lỗi xoá lịch sử: {e}")


# === HÀM BỔ SUNG KHÁC ===
def get_all_songs():
    """Hàm wrapper tiện ích để lấy tất cả bài hát."""
    return get_songs({})