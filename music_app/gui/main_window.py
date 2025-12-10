import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from mutagen.mp3 import MP3
import time
import shutil

# IMPORT CÁC DỊCH VỤ VÀ LỖI TÙY CHỈNH TỪ DATABASE
from gui.song_form import SongForm
from gui.playlist_window import PlaylistWindow
from services.player_service import player
from services import song_service
from database.mongo_connection import DatabaseConnectionError

# ================= CONFIG =================
BASE = Path(__file__).parents[1]
SONGS_DIR = BASE / "music"
COVERS_DIR = BASE / "assets" / "covers"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Các màu Spotify-like
COLOR_BACKGROUND = "#121212"  # Màu nền chính
COLOR_SIDEBAR = "#000000"  # Màu Sidebar
COLOR_PLAYER_BAR = "#181818"  # Màu thanh Player
COLOR_ACCENT = "#1DB954"  # Màu xanh lá chính


# ================= MAIN WINDOW =================
class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify-Like Music Player")
        self.geometry("1100x720")
        self.minsize(900, 600)

        # Grid structure
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # State
        self.songs = []
        self.current_index = -1
        self.song_length = 1

        self.is_playing = False
        self.start_time = 0
        self.pause_pos = 0

        # Disc Rotation State
        self.rotation_angle = 0
        self.original_cover = None
        self.cover_img = None
        self.img_cache = None

        # KHẮC PHỤC VÀ TẠO ẢNH MẶC ĐỊNH CHO HIỆU ỨNG QUAY
        EMPTY_SIZE = 64
        self.DEFAULT_COVER = self._create_default_disc(EMPTY_SIZE)

        # Tạo ảnh trống 1x1 (ảnh TclError, không dùng, nhưng giữ lại cho an toàn)
        empty_img = Image.new('RGB', (1, 1), color="#282828")
        self.empty_cover_fix = ctk.CTkImage(empty_img, size=(1, 1))

        # Build UI
        self._setup_ui()
        self.refresh_songs()

    def _create_default_disc(self, size):
        """Tạo ảnh PIL hình đĩa 64x64 chứa nốt nhạc '♫'"""
        # Màu nền đĩa (Giống fg_color của cover_label)
        bg_color = "#282828"
        text_color = "white"

        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))  # Nền trong suốt
        draw = ImageDraw.Draw(img)

        # Vẽ nền đĩa màu xám đậm
        draw.ellipse((0, 0, size, size), fill=bg_color)

        # Cố gắng tải font (có thể cần thay thế bằng font có sẵn trong hệ thống)
        try:
            # Arial là font cơ bản thường có sẵn
            font = ImageFont.truetype("arial.ttf", size=30)
        except IOError:
            # Dùng font mặc định nếu không tìm thấy Arial
            font = ImageFont.load_default()

        # Vẽ nốt nhạc '♫'
        text = "♫"
        # Ước lượng kích thước chữ (hoặc dùng textlength)
        # Tọa độ (size/2, size/2) là trung tâm,
        # offset là -15,-15 (khoảng một nửa kích thước font để căn giữa)
        draw.text(
            (size / 2, size / 2),
            text,
            fill=text_color,
            font=font,
            anchor="mm"  # Căn giữa tuyệt đối
        )

        # Tạo mask tròn cho ảnh (dù đã vẽ hình tròn, tạo mask giúp xoay không bị lộ góc)
        mask = Image.new('L', (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)

        return img

    # ================= UI =================

    def _setup_ui(self):
        # -------- SIDEBAR --------
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="🎧  MY MUSIC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(pady=(30, 20))

        self._side_btn("Danh sách Playlist", self.open_playlists)
        self._side_btn("Thêm bài hát", self.open_add_song)

        # NÚT XÓA BÀI HÁT
        ctk.CTkButton(
            self.sidebar,
            text="Xóa bài hát",
            height=44,
            corner_radius=10,
            fg_color="#CC0000",
            hover_color="#FF3333",
            command=self.delete_selected_song
        ).pack(fill="x", padx=15, pady=20)

        # -------- MAIN CONTENT --------
        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # -------- SONG LIST --------
        tree_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BACKGROUND)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=20)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("title", "artist", "duration"),
            show="headings",
            selectmode="browse"
        )
        # Sử dụng Style cho Treeview để làm cho nó trông tối hơn
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview",
                        background=COLOR_BACKGROUND,
                        foreground="white",
                        fieldbackground=COLOR_BACKGROUND,
                        bordercolor=COLOR_BACKGROUND)
        style.map('Treeview', background=[('selected', COLOR_ACCENT), ('!selected', COLOR_BACKGROUND)])

        for col, txt, w in [
            ("title", "TITLE", 400),
            ("artist", "ARTIST", 300),
            ("duration", "TIME", 80)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.on_double)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=vsb.set)

        # -------- PLAYER BAR (Thanh điều khiển cố định) --------
        self.player_frame = ctk.CTkFrame(self, height=110, fg_color=COLOR_PLAYER_BAR)
        self.player_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=0)

        # Chia player_frame thành 3 cột cố định: Info (0), Controls (1), Volume (2)
        self.player_frame.grid_columnconfigure(0, weight=0, minsize=250)
        self.player_frame.grid_columnconfigure(1, weight=1)
        self.player_frame.grid_columnconfigure(2, weight=0, minsize=200)
        self.player_frame.grid_rowconfigure(0, weight=1)
        self.player_frame.grid_rowconfigure(1, weight=1)

        # Cột 0: Info (Ảnh bìa + Tên bài hát)
        info = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        info.grid(row=0, column=0, rowspan=2, padx=20, sticky="w")

        # Cập nhật cover_label: Ban đầu dùng DEFAULT_COVER
        default_cover_ctk = ctk.CTkImage(self.DEFAULT_COVER, size=(64, 64))
        self.cover_label = ctk.CTkLabel(
            info, width=64, height=64, text="",
            image=default_cover_ctk,  # Dùng ảnh mặc định ngay từ đầu
            fg_color="#282828",
            corner_radius=32  # Luôn là hình tròn
        )
        self.cover_label.pack(side="left")

        txt = ctk.CTkFrame(info, fg_color="transparent")
        txt.pack(side="left", padx=10, fill="y")

        TEXT_WIDTH = 150

        self.lbl_song_title = ctk.CTkLabel(
            txt, text="Chưa phát", font=ctk.CTkFont(size=14, weight="bold"),
            width=TEXT_WIDTH, anchor="w", compound="left",
            justify="left",
            wraplength=TEXT_WIDTH
        )
        self.lbl_song_title.pack(anchor="w")

        self.lbl_song_artist = ctk.CTkLabel(
            txt, text="--", font=ctk.CTkFont(size=12), text_color="#B3B3B3",
            width=TEXT_WIDTH, anchor="w", compound="left",
            justify="left",
            wraplength=TEXT_WIDTH
        )
        self.lbl_song_artist.pack(anchor="w")

        # Cột 1: Controls (Nút Play/Pause + Thanh Seek)
        self.controls = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        self.controls.grid(row=0, column=1, sticky="s", pady=(8, 0))

        self._ctrl_btn("⏮", self.play_prev)
        self.play_btn = self._ctrl_btn("▶", self.toggle_play, big=True)
        self._ctrl_btn("⏭", self.play_next)

        seek = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        seek.grid(row=1, column=1, pady=(0, 8), sticky="n")

        self.lbl_time_current = ctk.CTkLabel(seek, text="0:00", width=40)
        self.lbl_time_current.pack(side="left")

        self.seek_slider = ctk.CTkSlider(
            seek, from_=0, to=1, width=420, command=self.on_seek,
            fg_color="#404040", progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT, button_hover_color="#1ed760"
        )
        self.seek_slider.pack(side="left", padx=10, fill="x", expand=True)

        self.lbl_time_total = ctk.CTkLabel(seek, text="0:00", width=40)
        self.lbl_time_total.pack(side="left")

        # Cột 2: Volume
        vol_frame = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        vol_frame.grid(row=0, column=2, rowspan=2, padx=20, sticky="e")

        ctk.CTkLabel(vol_frame, text="🔉", font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 5))

        self.vol_slider = ctk.CTkSlider(
            vol_frame, from_=0, to=100, width=120,
            command=self.on_volume,
            fg_color="#404040", progress_color=COLOR_ACCENT,
            button_color=COLOR_ACCENT
        )
        self.vol_slider.pack(side="left")
        self.vol_slider.set(80)
        self.on_volume(80)

    # ================= BUTTON HELPERS =================
    def _side_btn(self, text, cmd):
        ctk.CTkButton(
            self.sidebar, text=text, height=44, corner_radius=10,
            fg_color="#181818", hover_color="#242424",
            command=cmd
        ).pack(fill="x", padx=15, pady=6)

    def _ctrl_btn(self, text, cmd, big=False):
        btn = ctk.CTkButton(
            self.controls,
            text=text,
            width=52 if big else 40,
            height=52 if big else 40,
            corner_radius=26,
            fg_color=COLOR_ACCENT if big else "#282828",
            text_color="black" if big else "white",
            hover_color="#1ed760",
            command=cmd
        )
        btn.pack(side="left", padx=8)
        return btn

    # ================= LOGIC =================

    def refresh_songs(self):
        self.tree.delete(*self.tree.get_children())
        self.songs = []

        try:
            self.songs = song_service.get_songs()
        except DatabaseConnectionError as e:
            messagebox.showerror("Lỗi Cấu hình Database", str(e))
            self.songs = []
            return
        except Exception as e:
            print(f"Error fetching songs from DB: {e}")
            messagebox.showerror("Lỗi Database", "Không thể tải danh sách bài hát từ cơ sở dữ liệu.")
            self.songs = []
            return

        for song_info in self.songs:
            file_path = SONGS_DIR / song_info.get("path", "")
            length = 0

            if file_path.exists():
                try:
                    audio = MP3(file_path)
                    length = int(audio.info.length)
                except Exception:
                    pass

            song_info["duration"] = length
            song_id = str(song_info.get("_id"))

            self.tree.insert("", "end", iid=song_id, values=(
                song_info.get("title", "No Title"),
                song_info.get("artist", "Unknown Artist"),
                self._fmt(length)
            ))

        if self.songs and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

    def delete_selected_song(self):
        """Xóa bài hát đã chọn khỏi UI và MongoDB."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bài hát cần xóa.")
            return

        song_id_to_delete = sel[0]

        # Tìm bài hát trong danh sách cục bộ
        song_to_delete = next((s for s in self.songs if str(s["_id"]) == song_id_to_delete), None)

        if not song_to_delete:
            messagebox.showerror("Lỗi", "Bài hát không tồn tại trong danh sách.")
            return

        confirm = messagebox.askyesno(
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa bài hát:\n'{song_to_delete['title']}' - '{song_to_delete['artist']}'?"
        )

        if confirm:
            try:
                # 1. Dừng phát nhạc nếu bài hát đang phát bị xóa
                if self.current_index != -1 and str(self.songs[self.current_index]["_id"]) == song_id_to_delete:
                    player.stop()
                    self.is_playing = False
                    self.play_btn.configure(text="▶")
                    self.current_index = -1

                # 2. Xóa khỏi Database
                deleted_count = song_service.delete_song(song_id_to_delete)

                if deleted_count > 0:
                    messagebox.showinfo("Thành công", "Bài hát đã được xóa khỏi database.")
                else:
                    messagebox.showwarning("Cảnh báo", "Không tìm thấy bản ghi để xóa.")

                # 3. Cập nhật lại danh sách trên UI
                self.refresh_songs()

            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể xóa bài hát: {e}")

    def play_selected(self):
        sel = self.tree.selection()
        if not sel:
            return

        index = next((i for i, s in enumerate(self.songs) if str(s["_id"]) == sel[0]), -1)
        if index != -1:
            self.play_by_index(index)
        else:
            messagebox.showerror("Error", "Bài hát không tồn tại.")

    def play_by_index(self, index):
        if index < 0 or index >= len(self.songs):
            return

        song = self.songs[index]
        path = SONGS_DIR / song["path"]
        if not path.exists():
            messagebox.showerror("Error", f"File not found:\n{path}")
            return

        if self.current_index != -1:
            self.tree.selection_remove(str(self.songs[self.current_index]["_id"]))
        self.tree.selection_set(str(song["_id"]))

        self.current_index = index

        player.load_queue([s["path"] for s in self.songs])
        player.play_index(index)

        self.is_playing = True
        self.play_btn.configure(text="⏸")

        self._update_now_playing(song)

        self.song_length = max(song.get("duration", 1), 1)
        self.seek_slider.configure(to=self.song_length, state="normal")
        self.seek_slider.set(0)

        self.start_time = time.time()
        self.pause_pos = 0

        self.lbl_time_total.configure(text=self._fmt(self.song_length))

        self.after(500, self.update_seek)

        # Điều kiện để bắt đầu quay đĩa nằm trong _update_now_playing

    def update_seek(self):
        pos = player.get_position()

        if self.is_playing:
            if pos < self.song_length:
                self.seek_slider.set(pos)
                self.lbl_time_current.configure(text=self._fmt(pos))

            elif pos >= self.song_length and self.current_index != -1:
                self.play_next()
                return

        self.after(500, self.update_seek)

    def on_seek(self, value):
        if self.song_length <= 1 or self.current_index == -1:
            return
        sec = int(value)
        player.seek(sec)

        if self.is_playing:
            self.start_time = time.time() - sec
            self.pause_pos = sec
        else:
            self.pause_pos = sec
            self.lbl_time_current.configure(text=self._fmt(sec))

    def toggle_play(self):
        if self.current_index == -1 and self.songs:
            self.play_by_index(0)
            return

        if self.current_index == -1:
            return

        if self.is_playing:
            player.pause()
            self.is_playing = False
            self.play_btn.configure(text="▶")

        else:
            player.play()
            self.is_playing = True
            self.play_btn.configure(text="⏸")

            self.after(500, self.update_seek)

            # BẮT ĐẦU QUAY ĐĨA MỌI LÚC KHI CHƠI, vì self.original_cover luôn là ảnh PIL hợp lệ
            if self.original_cover is not None:
                self.after(50, self.rotate_cover)

    def play_next(self):
        if player.next():
            self.play_by_index(self.current_index + 1)
        else:
            self.is_playing = False
            self.play_btn.configure(text="▶")
            self.lbl_time_current.configure(text=self._fmt(self.song_length))

            # CẬP NHẬT: Quay lại ảnh nốt nhạc mặc định
            self._update_now_playing(None)  # Dùng None để gọi logic set ảnh mặc định

            self.current_index = -1
            # Xóa selection nếu còn
            if self.tree.selection():
                self.tree.selection_remove(self.tree.selection())

    def play_prev(self):
        if player.previous():
            self.play_by_index(self.current_index - 1)

    def on_volume(self, v):
        player.set_volume(v / 100)

    def _fmt(self, s):
        s = int(s)
        return f"{s // 60}:{s % 60:02d}"

    # ================= ROTATE DISC =================

    def _update_cover_image(self, img):
        CORNER_RADIUS_DISC = 32

        # img ở đây LUÔN LÀ self.original_cover (ảnh PIL)

        # 1. Nếu chưa có đối tượng cover_img, TẠO MỚI.
        if self.cover_img is None:
            self.cover_img = ctk.CTkImage(img, size=(64, 64))

        # 2. Cấu hình nguồn ảnh (PIL Image) cho đối tượng CTkImage đã có
        self.cover_img.configure(light_image=img, dark_image=img)

        # 3. Gán đối tượng đã update vào label (text trống, tròn)
        self.cover_label.configure(image=self.cover_img, text="", corner_radius=CORNER_RADIUS_DISC)

        # Dọn dẹp cache cũ nếu có
        self.img_cache = img  # Lưu ảnh hiện tại vào cache

        # Nếu đang phát nhạc và đã có ảnh gốc (dù là ảnh mặc định hay cover), bắt đầu quay
        if self.is_playing and self.original_cover is not None:
            self.rotation_angle = 0
            self.after(50, self.rotate_cover)

    def rotate_cover(self):
        # Đảm bảo self.cover_img đã được tạo và đang phát
        if not self.is_playing or self.original_cover is None or self.cover_img is None:
            return

        self.rotation_angle = (self.rotation_angle + 1) % 360
        # Xoay ảnh gốc (self.original_cover)
        rotated = self.original_cover.rotate(-self.rotation_angle, resample=Image.BICUBIC)

        # Áp dụng lại mặt nạ (mask) sau khi xoay để giữ hình tròn
        mask = Image.new('L', (64, 64), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 64, 64), fill=255)
        rotated.putalpha(mask)

        # CẬP NHẬT NGUỒN ẢNH: Chỉ gọi configure trên đối tượng CTkImage
        self.cover_img.configure(light_image=rotated, dark_image=rotated)

        # Gọi lại rotate_cover sau 50ms
        self.after(50, self.rotate_cover)

    def _update_now_playing(self, song):

        # Trường hợp dừng phát hoặc chuyển bài không có (song=None)
        if song is None:
            self.lbl_song_title.configure(text="Chưa phát")
            self.lbl_song_artist.configure(text="--")
            self.original_cover = self.DEFAULT_COVER
            self._update_cover_image(self.original_cover)
            return

        # Trường hợp có bài hát
        self.lbl_song_title.configure(text=song.get("title"))
        self.lbl_song_artist.configure(text=song.get("artist"))

        cover_name = song.get("cover")
        if cover_name is None:
            cover_name = ""

        cover_path = COVERS_DIR / cover_name

        img = None

        if cover_name and cover_path.exists():
            # Xử lý cover thực
            try:
                # Đảm bảo file được đóng ngay lập tức sau khi đọc
                with Image.open(cover_path) as img_file:
                    # Load data vào memory và resize
                    img = img_file.resize((64, 64)).copy()

                    # Tạo mask tròn cho ảnh
                mask = Image.new('L', (64, 64), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 64, 64), fill=255)
                img.putalpha(mask)

                self.original_cover = img
                self._update_cover_image(img)

            except Exception as e:
                # Xử lý lỗi tải ảnh: in ra lỗi và chuyển về ảnh mặc định
                print(f"Error loading cover {cover_path}: {e}")
                self.original_cover = self.DEFAULT_COVER
                self._update_cover_image(self.original_cover)

        else:
            # Không có cover -> Dùng ảnh mặc định có nốt nhạc
            self.original_cover = self.DEFAULT_COVER
            self._update_cover_image(self.original_cover)

    def on_double(self, _):
        self.play_selected()

    def open_playlists(self):
        PlaylistWindow(self, on_change=self.refresh_songs)

    def open_add_song(self):
        SongForm(self, on_saved=self.refresh_songs)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()