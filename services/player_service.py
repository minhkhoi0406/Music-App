import pygame
from pathlib import Path
import time
import os

BASE_DIR = Path(__file__).parents[1]
MUSIC_DIR = BASE_DIR / "music"

pygame.mixer.init()


class PlayerService:
    def __init__(self):
        self.queue = []
        self.current_index = -1
        self.song_length = 0

        self.start_time = 0

        self.pause_offset = 0
        self.paused = False

        pygame.mixer.music.set_volume(0.8)


    def load_queue(self, paths: list):
        """Tải hàng đợi mới của các đường dẫn file (tương đối)."""
        self.queue = paths

    def play_index(self, index: int):
        """Tải và phát bài hát theo chỉ mục trong queue."""
        if index < 0 or index >= len(self.queue):
            return


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


    def play(self):
        """Tiếp tục phát nhạc."""
        if self.paused and self.current_index != -1:
            pygame.mixer.music.unpause()
            self.start_time = time.time() - self.pause_offset
            self.paused = False

    def pause(self):
        """Tạm dừng phát nhạc."""
        if not self.paused and self.current_index != -1:
            pygame.mixer.music.pause()
            self.pause_offset = time.time() - self.start_time
            self.paused = True

    def stop(self):
        """Dừng hoàn toàn phát nhạc và reset trạng thái."""
        pygame.mixer.music.stop()
        self.current_index = -1
        self.start_time = 0
        self.pause_offset = 0
        self.paused = False

    def next(self):
        """Chuyển sang bài tiếp theo trong queue."""
        if self.current_index + 1 < len(self.queue):
            self.play_index(self.current_index + 1)
            return True
        return False

    def previous(self):
        """Chuyển về bài trước trong queue."""
        if self.current_index > 0:
            self.play_index(self.current_index - 1)
            return True
        return False

    def seek(self, seconds: int):
        """Tua nhạc đến giây quy định."""
        if self.current_index == -1:
            return

        try:
            pygame.mixer.music.set_pos(seconds)

            if self.paused:
                self.pause_offset = seconds
            else:
                self.start_time = time.time() - seconds

        except pygame.error as e:
            print(f"Error seeking: {e}")


    def get_position(self):
        """Lấy vị trí hiện tại của bài hát (tính bằng giây)."""
        if self.current_index == -1:
            return 0

        if self.paused:
            return int(self.pause_offset)

        return int(time.time() - self.start_time)

    def set_volume(self, volume: float):
        """Điều chỉnh âm lượng (0.0 đến 1.0)."""
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def is_playing(self):
        """Kiểm tra xem nhạc có đang phát hay không (không paused và có index)."""
        return self.current_index != -1 and not self.paused

    def _full_path(self, fname):
        """Tạo đường dẫn tuyệt đối từ tên file tương đối."""
        return str(MUSIC_DIR / fname)

player = PlayerService()