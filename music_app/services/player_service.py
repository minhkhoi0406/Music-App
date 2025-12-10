import pygame
from pathlib import Path
import time
import os

# Định nghĩa BASE
# Giả định file này nằm trong 'services/' và music nằm trong thư mục gốc
BASE_DIR = Path(__file__).parents[1]
MUSIC_DIR = BASE_DIR / "music"

pygame.mixer.init()


class PlayerService:
    def __init__(self):
        self.queue = []
        self.current_index = -1
        self.song_length = 0  # Thêm để lưu trữ độ dài bài hát

        # Thời gian bắt đầu phát nhạc lần cuối (dùng để tính vị trí)
        self.start_time = 0
        # Tổng thời gian đã phát trước khi tạm dừng
        self.pause_offset = 0
        self.paused = False

        pygame.mixer.music.set_volume(0.8)

    # ========= LOAD =========
    def load_queue(self, paths: list):
        self.queue = paths

    def play_index(self, index: int):
        if index < 0 or index >= len(self.queue):
            return

        # Dùng Path.joinpath để xây dựng đường dẫn an toàn
        path = self._full_path(self.queue[index])
        file_path = Path(path)

        if not file_path.exists():
            print(f"File not found: {path}")
            return

        self.current_index = index

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error loading/playing file: {e}")
            return

        self.start_time = time.time()
        self.pause_offset = 0
        self.paused = False

        # Bắt đầu quay đĩa ngay lập tức (logic này sẽ ở MainWindow)

    # ========= CONTROLS =========
    def play(self):
        if self.paused and self.current_index != -1:
            # Tiếp tục từ vị trí đã tạm dừng
            pygame.mixer.music.unpause()
            # Cập nhật thời gian bắt đầu dựa trên offset cũ
            self.start_time = time.time() - self.pause_offset
            self.paused = False

    def pause(self):
        if not self.paused and self.current_index != -1:
            pygame.mixer.music.pause()
            # Tính offset (thời gian đã phát)
            self.pause_offset = time.time() - self.start_time
            self.paused = True

    def stop(self):
        pygame.mixer.music.stop()
        self.current_index = -1
        self.start_time = 0
        self.pause_offset = 0
        self.paused = False

    def next(self):
        if self.current_index + 1 < len(self.queue):
            self.play_index(self.current_index + 1)
            return True
        return False

    def previous(self):
        if self.current_index > 0:
            self.play_index(self.current_index - 1)
            return True
        return False

    # ========= SEEK (FIXED) =========
    def seek(self, seconds: int):
        if self.current_index == -1:
            return

        try:
            # 1. Tua nhạc (chỉ hoạt động khi nhạc đang phát/tạm dừng)
            pygame.mixer.music.set_pos(seconds)

            # 2. Cập nhật vị trí bắt đầu và offset (quan trọng!)
            # Nếu đang tạm dừng, offset là vị trí tua đến
            if self.paused:
                self.pause_offset = seconds
                # Nếu đang phát, cập nhật start_time để get_position() tính đúng
            else:
                self.start_time = time.time() - seconds

        except pygame.error as e:
            # Lỗi set_pos thường xảy ra nếu file nhạc chưa được tải
            print(f"Error seeking: {e}")

    # ========= POSITION (FIXED) =========
    def get_position(self):
        if self.current_index == -1:
            return 0

        # Nếu đang tạm dừng, trả về vị trí offset đã lưu
        if self.paused:
            return int(self.pause_offset)

        # Nếu đang phát, tính toán dựa trên thời gian thực
        return int(time.time() - self.start_time)

    # ========= VOLUME =========
    def set_volume(self, volume: float):
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    # ========= STATE CHECK =========
    def is_playing(self):
        return self.current_index != -1 and not self.paused

    # ========= HELP =========
    def _full_path(self, fname):
        # Đảm bảo đường dẫn sử dụng Path.joinpath
        return str(MUSIC_DIR / fname)


# ✅ SINGLETON
player = PlayerService()