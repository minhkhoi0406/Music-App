from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import os
from pathlib import Path


# Lỗi tùy chỉnh để báo hiệu lỗi kết nối database
class DatabaseConnectionError(Exception):
    pass


class MongoConnection:
    def __init__(self, uri: str = None, db_name: str = "music_app"):
        # KIỂM TRA URI NÀY: Thay đổi nếu MongoDB của bạn không chạy trên cổng 27017
        self.uri = uri or os.environ.get("MONGO_URI") or "mongodb://localhost:27017"
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        if self.client is None:
            try:
                self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
                self.client.admin.command('ping')

                self.db = self.client[self.db_name]
                print(f"Connected to MongoDB database: {self.db_name}")

            except ServerSelectionTimeoutError as e:
                self.client = None
                raise DatabaseConnectionError(
                    "Không thể kết nối đến máy chủ MongoDB. Vui lòng kiểm tra URI và trạng thái server.") from e
            except Exception as e:
                self.client = None
                raise DatabaseConnectionError(f"Lỗi kết nối không xác định: {e}") from e

        return self.db


def get_db():
    conn = MongoConnection()
    return conn.connect()