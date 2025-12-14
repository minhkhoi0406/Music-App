import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk
from mutagen.mp3 import MP3
import time
import shutil
import pygame
import random
from gui.select_playlist_dialog import SelectPlaylistDialog
from gui.song_form import SongForm
from gui.playlist_window import PlaylistWindow
from services.player_service import player
from services import song_service, playlist_service
from database.mongo_connection import DatabaseConnectionError

BASE = Path(__file__).parents[1]
SONGS_DIR = BASE / "music"
COVERS_DIR = BASE / "assets" / "covers"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

COLOR_BACKGROUND = "#121212"
COLOR_SIDEBAR = "#000000"
COLOR_PLAYER_BAR = "#181818"
COLOR_ACCENT = "#1DB954"

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify-Like Music Player")
        # Thay đổi minsize cho phù hợp với kích thước gợi ý
        self.geometry("1400x700")
        self.minsize(1400, 700)
        self.configure(fg_color=COLOR_BACKGROUND)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- KHAI BÁO BIẾN TRẠNG THÁI ---
        self.songs = []
        self.current_index = -1
        self.song_length = 1
        self.is_playing = False
        self.start_time = 0
        self.pause_pos = 0
        self.rotation_angle = 0
        self.original_cover = None
        self.cover_img = None
        self.img_cache = None
        self.playlist_buttons = {}
        self.current_view_is_playlist = False
        self.current_playlist_id = None
        self.history_list = []

        # --- KHAI BÁO BIẾN ĐIỀU KHIỂN (CTKStringVar) CHO TÌM KIẾM/LỌC ---
        # Bổ sung: Biến cho ô tìm kiếm
        self.search_var = ctk.StringVar(value="")
        # Bổ sung: Biến cho bộ lọc số lần nghe
        self.plays_var = ctk.StringVar(value="")

        # --- KHAI BÁO ẢNH MẶC ĐỊNH ---
        EMPTY_SIZE = 64
        # (Giả định: _create_default_disc tạo ra PIL Image)
        self.DEFAULT_COVER = self._create_default_disc(EMPTY_SIZE)
        empty_img = Image.new('RGB', (1, 1), color="#282828")
        self.empty_cover_fix = ctk.CTkImage(empty_img, size=(1, 1))

        # --- THIẾT LẬP UI VÀ TẢI DỮ LIỆU ---
        self._setup_ui()
        self.load_all_songs()

    def _create_default_disc(self, size):
        """Tạo ảnh PIL hình đĩa 64x64 chứa nốt nhạc '♫'"""
        bg_color = "#282828"
        text_color = "white"

        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.ellipse((0, 0, size, size), fill=bg_color)

        try:
            font = ImageFont.truetype("arial.ttf", size=30)
        except IOError:
            font = ImageFont.load_default()

        text = "♫"
        draw.text(
            (size / 2, size / 2),
            text,
            fill=text_color,
            font=font,
            anchor="mm"
        )

        mask = Image.new('L', (size, size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)

        return img

    def _setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="🎧  MY MUSIC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLOR_ACCENT
        ).grid(row=0, column=0, padx=15, pady=(30, 20), sticky="ew")

        self.playlist_scroll_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            label_text="DANH SÁCH PLAYLIST",
            label_font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_SIDEBAR,
            label_fg_color=COLOR_SIDEBAR
        )
        self.playlist_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.playlist_scroll_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            self.playlist_scroll_frame,
            text="TẤT CẢ BÀI HÁT",
            anchor="w",
            fg_color="#282828",
            hover_color="#303030",
            command=self.load_all_songs
        ).grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.btn_favorites = ctk.CTkButton(
            self.playlist_scroll_frame,
            text="BÀI HÁT YÊU THÍCH",
            anchor="w",
            fg_color="#282828",
            hover_color="#303030",
            command=self.load_favorite_songs
        )
        self.btn_favorites.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.control_frame = ctk.CTkFrame(self.sidebar, fg_color=COLOR_SIDEBAR)
        self.control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.btn_ranking = ctk.CTkButton(
            self.playlist_scroll_frame,
            text="BẢNG XẾP HẠNG",
            anchor="w",
            fg_color="#282828",
            hover_color="#303030",
            command=self.open_ranking_chart
        )
        self.btn_ranking.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 5))

        self.btn_history = ctk.CTkButton(
            self.playlist_scroll_frame,
            text="LỊCH SỬ NGHE NHẠC",
            anchor="w",
            fg_color="#282828",
            hover_color="#303030",
            command=self.load_song_history
        )
        self.btn_history.grid(row=4, column=0, sticky="ew", padx=5, pady=(0, 5))

        ctk.CTkButton(
            self.control_frame,
            text=" Thêm Bài Hát",
            height=44,
            corner_radius=10,
            fg_color="#181818", hover_color="#242424",
            command=self.open_add_song
        ).pack(fill="x", padx=5, pady=6)

        ctk.CTkButton(
            self.control_frame,
            text=" Quản Lý Playlists",
            height=44,
            corner_radius=10,
            fg_color=COLOR_ACCENT, hover_color="#1ed760",
            command=self.open_playlists
        ).pack(fill="x", padx=5, pady=(6, 10))

        self.main_frame = ctk.CTkFrame(self, fg_color=COLOR_BACKGROUND)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, minsize=50)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.main_title = ctk.CTkLabel(self.main_frame, text="TẤT CẢ BÀI HÁT", font=ctk.CTkFont(size=24, weight="bold"))
        self.main_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        row1_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        row1_frame.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        row1_frame.grid_columnconfigure(1, weight=1)

        self.btn_random = ctk.CTkButton(
            row1_frame,
            text="Phát Ngẫu Nhiên",
            height=40,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color="#1ed760",
            command=self.play_random_song
        )
        self.btn_random.grid(row=0, column=0, padx=(0, 20))

        filter_frame = ctk.CTkFrame(row1_frame, fg_color="transparent")
        filter_frame.grid(row=0, column=1, sticky="ew")
        filter_frame.grid_columnconfigure(2, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write",
                                  lambda name, index, mode: self.on_search_filter_change()
                                  )
        ctk.CTkLabel(
            filter_frame,
            text="Tìm:",
            text_color="white",
            font=ctk.CTkFont(size=14)
        ).grid(row=0, column=0, padx=(0, 5))

        search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Tìm bài hát, album, nghệ sĩ...",
            textvariable=self.search_var,
            width=250,
            fg_color="#282828",
            text_color="white",
            placeholder_text_color="#A0A0A0"
        )
        search_entry.grid(row=0, column=1, padx=(0, 20))
        self.search_var.trace_add("write",
                                  lambda name, index, mode: self.on_search_filter_change()
                                  )

        self.plays_var = tk.StringVar(value="0")  # Phải là StringVar
        self.plays_var.trace_add("write",
                                 lambda name, index, mode: self.on_search_filter_change()
                                 )

        ctk.CTkLabel(filter_frame, text="Số lần nghe ≥").grid(row=0, column=3, padx=(0, 5))
        ctk.CTkEntry(filter_frame, textvariable=self.plays_var, width=50).grid(row=0, column=4, padx=(0, 20))

        tree_frame = ctk.CTkFrame(self.main_frame, fg_color=COLOR_BACKGROUND)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=2)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_images = {}
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("cover", "title", "artist", "album", "duration", "plays", "action"),
            show="tree headings",
            selectmode="extended"
        )
        self.tree.column("#0", width=75, anchor="center", stretch=tk.NO )
        self.tree.heading("#0", text="Đĩa tròn")
        self.tree.column("cover", width=0, anchor="center", stretch=tk.NO)
        self.tree.heading("action", text="Thao tác")
        self.tree.column("action", width=80, anchor="center")
        style = ttk.Style(self)
        style.theme_use("default")

        ROW_HEIGHT_WITH_COVER = 45
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=ROW_HEIGHT_WITH_COVER)

        style.configure("Treeview",
                        background=COLOR_BACKGROUND,
                        foreground="white",
                        fieldbackground=COLOR_BACKGROUND,
                        bordercolor=COLOR_BACKGROUND,
                        rowheight=ROW_HEIGHT_WITH_COVER,
                        font=("Arial", 14))
        style.map('Treeview', background=[('selected', COLOR_ACCENT), ('!selected', COLOR_BACKGROUND)])

        style.configure("Custom.Vertical.TScrollbar",
                        troughcolor=COLOR_BACKGROUND,
                        background="#404040",
                        arrowcolor="white",
                        bordercolor=COLOR_BACKGROUND),
        style.map("Custom.Vertical.TScrollbar",
                  background=[('active', '#505050')])
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 14))

        for col, txt, w in [
            ("title", "Tên bài hát", 300),
            ("artist", "Nghệ sĩ", 200),
            ("album", "Album", 200),
            ("duration", "Thời lượng", 80),
            ("plays", "Số lần nghe", 80)
        ]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w,  anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<Button-1>", self.on_tree_click)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview, style="Custom.Vertical.TScrollbar")
        vsb.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=vsb.set)

        self.player_frame = ctk.CTkFrame(self, height=110, fg_color=COLOR_PLAYER_BAR)
        self.player_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=0)

        self.player_frame.grid_columnconfigure(0, weight=0, minsize=250)
        self.player_frame.grid_columnconfigure(1, weight=1)
        self.player_frame.grid_columnconfigure(2, weight=0, minsize=200)
        self.player_frame.grid_rowconfigure(0, weight=1)
        self.player_frame.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        info.grid(row=0, column=0, rowspan=2, padx=20, sticky="w")

        default_cover_ctk = ctk.CTkImage(self.DEFAULT_COVER, size=(64, 64))
        self.cover_label = ctk.CTkLabel(
            info, width=64, height=64, text="",
            image=default_cover_ctk,
            fg_color="#282828",
            corner_radius=32
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

        self.controls = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        self.controls.grid(row=0, column=1, sticky="s", pady=(8, 0))

        self._ctrl_btn("⏮", self.play_prev)
        self.play_btn = self._ctrl_btn("▶", self.toggle_play, big=True)
        self._ctrl_btn("⏭", self.play_next)

        seek = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        seek.grid(row=1, column=1, pady=(0, 8), sticky="n")

        self.add_to_playlist_btn = ctk.CTkButton(
            seek,
            text="Thêm vào Playlist",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=140,
            height=35,
            corner_radius=8,
            fg_color=COLOR_ACCENT,
            hover_color="#1ed760",
            text_color="white",
            command=self.add_current_song_to_playlist,
            state="disabled"
        )
        self.add_to_playlist_btn.pack(side="left", padx=(0, 10))

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

        self.favorite_btn_img_empty = "🤍"
        self.favorite_btn_img_filled = "❤️"
        self.favorite_btn = ctk.CTkButton(
            seek,
            text=self.favorite_btn_img_empty,
            font=ctk.CTkFont(size=18),
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color="#282828",
            command=self.toggle_favorite_current_song,
            anchor="center"
        )
        self.favorite_btn.pack(side="left", padx=(10, 10))

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


    def load_sidebar_playlists(self):
        """Tải danh sách Playlist từ DB và tạo nút ở Sidebar."""

        for i, widget in enumerate(self.playlist_scroll_frame.winfo_children()):
            if i > 3:
                widget.destroy()

        self.playlist_buttons = {}

        try:
            playlists = playlist_service.get_playlists()
            current_row = 5
            for p in playlists:
                playlist_id = str(p['_id'])
                playlist_name = p['name']

                btn = ctk.CTkButton(
                    self.playlist_scroll_frame,
                    text=f"▶ {playlist_name}",
                    anchor="w",
                    fg_color="transparent",
                    hover_color="#2A2A2A",
                    command=lambda pid=playlist_id: self.load_songs_from_playlist(pid)
                )
                btn.grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
                self.playlist_buttons[playlist_id] = btn
                current_row += 1

        except Exception as e:
            print(f"Lỗi tải Playlist: {e}")
            messagebox.showerror("Lỗi Database", "Không thể tải danh sách Playlist.")

    def load_all_songs(self):
        """Tải tất cả bài hát vào Treeview chính và đặt làm danh sách phát chính."""
        self.main_title.configure(text="TẤT CẢ BÀI HÁT")
        self.current_view_is_playlist = False
        self.current_playlist_id = None
        self.refresh_songs()

    def load_songs_from_playlist(self, playlist_id):
        """Tải và hiển thị bài hát của Playlist được chọn lên Treeview chính."""
        try:
            playlist = playlist_service.get_playlist(playlist_id)
            if not playlist:
                messagebox.showerror("Lỗi", "Playlist không tồn tại.")
                return

            playlist_songs = playlist_service.get_songs_in_playlist(playlist_id)

            self.main_title.configure(text=f"PLAYLIST: {playlist['name']}")
            self.current_view_is_playlist = True
            self.current_playlist_id = playlist_id

            self.songs = playlist_songs

            self.tree.delete(*self.tree.get_children())
            self.tree_images = {}

            self.reset_treeview_style()

            COVER_SIZE_TREEVIEW = 40

            for song_info in self.songs:
                song_id = str(song_info.get("_id"))
                length = song_info.get("duration", 0)

                # --- SỬA LỖI: Kiểm tra cover_name an toàn ---
                cover_name = song_info.get("cover")  # Lấy None nếu key không tồn tại
                cover_path = None

                # Chỉ tạo cover_path nếu cover_name là chuỗi hợp lệ và không rỗng
                if cover_name and isinstance(cover_name, str) and cover_name.strip():
                    try:
                        # KHỐI CODE ĐÃ SỬA LỖI
                        cover_path = COVERS_DIR / cover_name
                    except TypeError:
                        cover_path = None

                pil_img = None

                # Xử lý Ảnh Bìa
                if cover_path and cover_path.exists():
                    try:
                        pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                        mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                        pil_img.putalpha(mask)

                    except Exception:
                        # Lỗi đọc/xử lý ảnh: dùng ảnh mặc định
                        pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
                else:
                    # Không có tên ảnh/ảnh không tồn tại: dùng ảnh mặc định
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

                tk_img = ImageTk.PhotoImage(pil_img)
                img = tk_img
                self.tree_images[song_id] = img

                # Cần đảm bảo rằng bạn chỉ gán img cho một key.
                # self.tree_images[song_id] = img # Dòng này đã được gán ở trên.
                three_dot_img = self.create_three_dot_icon(24)
                self.tree_images[song_id + "_action"] = three_dot_img

                self.tree.insert("", "end", iid=song_id, image=img, values=(
                    "",
                    song_info.get("title", "No Title"),
                    song_info.get("artist", "Unknown Artist"),
                    song_info.get("album", "Unknown Album"),
                    self._fmt(length),
                    song_info.get("play_count", 0),
                    "☰"
                ))

            if self.songs and self.tree.get_children():
                self.tree.selection_set(self.tree.get_children()[0])


        except Exception as e:
            # Thêm in lỗi chi tiết ra console để dễ dàng gỡ lỗi
            import traceback
            print("-" * 50)
            print("LỖI KHÔNG THỂ TẢI BÀI HÁT TỪ PLAYLIST:")
            traceback.print_exc()
            print("-" * 50)

            messagebox.showerror("Lỗi", f"Không thể tải bài hát trong Playlist. Lỗi chi tiết: {e}")

    def refresh_songs(self):
        """Tải lại danh sách bài hát từ DB và cập nhật Treeview."""

        # Thoát nếu đang ở chế độ xem Playlist, chỉ tải lại sidebar
        if self.current_view_is_playlist:
            self.load_sidebar_playlists()
            return

        # Dọn dẹp Treeview và cache ảnh
        self.tree.delete(*self.tree.get_children())
        self.songs = []
        self.tree_images = {}

        # 1. Tải danh sách bài hát từ DB
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

        COVER_SIZE_TREEVIEW = 40

        # 2. Xử lý và chèn từng bài hát vào Treeview
        for song_info in self.songs:

            file_path = SONGS_DIR / song_info.get("path", "")
            length = song_info.get("duration", 0)

            # Cập nhật thời lượng nếu cần (chỉ khi file tồn tại và duration là 0)
            if file_path.exists() and length == 0:
                try:
                    # Giả định MP3 đã được import
                    audio = MP3(file_path)
                    length = int(audio.info.length)
                except Exception:
                    pass

            song_info["duration"] = length
            song_id = str(song_info.get("_id"))

            # --- SỬA LỖI: Kiểm tra cover_name trước khi tạo đường dẫn ---
            cover_name = song_info.get("cover")  # Lấy giá trị, mặc định là None nếu key không tồn tại
            cover_path = None

            # CHỈ NỐI ĐƯỜNG DẪN NẾU cover_name TỒN TẠI VÀ KHÔNG PHẢI CHUỖI RỖNG
            if cover_name:
                try:
                    cover_path = COVERS_DIR / cover_name
                except TypeError:
                    # Bắt lỗi nếu cover_name là None hoặc kiểu dữ liệu không hợp lệ khác
                    cover_path = None

            pil_img = None

            # Xử lý ảnh bìa
            if cover_path and cover_path.exists():
                try:
                    pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                    # Áp dụng mask (làm tròn)
                    mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                    pil_img.putalpha(mask)

                except Exception:
                    # Sử dụng cover mặc định nếu lỗi đọc/xử lý ảnh
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
            else:
                # Sử dụng cover mặc định nếu không có cover_name hoặc file không tồn tại
                pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

            tk_img = ImageTk.PhotoImage(pil_img)
            img = tk_img
            self.tree_images[song_id] = img

            self.tree.insert("", "end", iid=song_id, image=img, values=(
                "",  # cover
                song_info.get("title", "No Title"),
                song_info.get("artist", "Unknown Artist"),
                song_info.get("album", "Unknown Album"),
                self._fmt(length),
                song_info.get("play_count", 0),
                "☰"
            ))

        # 3. Thiết lập lựa chọn và tải lại Sidebar
        if self.songs and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

        self.load_sidebar_playlists()

    def delete_selected_song(self):
        """
        Xóa bài hát đã chọn. Tùy thuộc vào chế độ xem,
        hàm sẽ Xóa khỏi Playlist (Xóa tham chiếu) HOẶC Xóa Vĩnh viễn (Xóa khỏi DB gốc).
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bài hát cần xóa.")
            return

        song_id_to_delete = sel[0]
        song_to_delete = next((s for s in self.songs if str(s.get("_id")) == song_id_to_delete), None)

        if not song_to_delete:
            messagebox.showerror("Lỗi", "Bài hát không tồn tại trong danh sách hiện tại.")
            return

        # === BƯỚC SỬA LỖI: PHÂN NHÁNH LOGIC XÓA ===

        # 1. NGỮ CẢNH: Đang xem Playlist (Xóa tham chiếu)
        if self.current_view_is_playlist and self.current_playlist_id:

            confirm = messagebox.askyesno(
                "Xác nhận Xóa khỏi Playlist",
                f"Bạn có chắc chắn muốn XÓA BÀI HÁT này khỏi playlist hiện tại:\n'{song_to_delete['title']}' - '{song_to_delete['artist']}'?"
            )

            if not confirm:
                return

            try:
                # 🟢 GỌI HÀM DỊCH VỤ ĐÚNG: CHỈ XÓA ID BÀI HÁT KHỎI TÀI LIỆU PLAYLIST
                # Đây là hàm mà bạn đã viết đúng trong playlist_service.py
                deleted_count = playlist_service.remove_song_from_playlist(self.current_playlist_id, song_id_to_delete)

                if deleted_count > 0:
                    messagebox.showinfo("Thành công", "Bài hát đã được xóa khỏi Playlist.")

                    # Cập nhật lại giao diện Playlist
                    self.load_songs_from_playlist(self.current_playlist_id)
                else:
                    messagebox.showwarning("Cảnh báo", "Không tìm thấy bài hát trong Playlist để xóa.")

            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể xóa khỏi Playlist: {e}")

        # 2. NGỮ CẢNH: Đang xem Danh sách Tổng quát (Xóa Vĩnh viễn khỏi DB)
        else:
            confirm = messagebox.askyesno(
                "Xác nhận Xóa Vĩnh Viễn",
                f"CẢNH BÁO: Bạn có chắc chắn muốn XÓA VĨNH VIỄN bài hát này khỏi hệ thống:\n'{song_to_delete['title']}' - '{song_to_delete['artist']}'?"
            )

            if not confirm:
                return

            try:
                # Xử lý dừng phát nhạc nếu cần
                if self.current_index != -1 and str(self.songs[self.current_index].get("_id")) == song_id_to_delete:
                    player.stop()
                    self.is_playing = False
                    self.play_btn.configure(text="▶")
                    self.current_index = -1

                #  GỌI HÀM XÓA GỐC: Chỉ được gọi ở chế độ xem tổng quát
                deleted_count = song_service.delete_song(
                    song_id_to_delete)  # Giả định đây là hàm xóa khỏi collection SONGS

                if deleted_count > 0:
                    messagebox.showinfo("Thành công", "Bài hát đã được xóa vĩnh viễn khỏi hệ thống.")
                else:
                    messagebox.showwarning("Cảnh báo", "Không tìm thấy bản ghi để xóa.")

                # Tải lại danh sách tổng quát
                self.refresh_songs()

            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể xóa bài hát: {e}")

    def play_selected(self):
        """Phát bài hát được chọn từ Treeview."""
        sel = self.tree.selection()
        if not sel:
            return

        index = next((i for i, s in enumerate(self.songs) if str(s["_id"]) == sel[0]), -1)
        if index != -1:
            self.play_by_index(index)
        else:
            messagebox.showerror("Error", "Bài hát không tồn tại.")

    def play_by_index(self, index):
        """Tải và phát bài hát dựa trên index trong self.songs."""
        if index < 0 or index >= len(self.songs):
            return

        song = self.songs[index]

        if song.get("_id") == "0":
            messagebox.showwarning("Cảnh báo", "Không thể phát bài hát giả định.")
            return

        path = SONGS_DIR / song["path"]
        if not path.exists():
            messagebox.showerror("Error", f"File not found:\n{path}")
            return

        is_current_index_valid = (
                self.current_index != -1 and
                0 <= self.current_index < len(self.songs)
        )

        if is_current_index_valid:
            old_song_id = str(self.songs[self.current_index].get("_id"))
            if self.tree.exists(old_song_id):
                self.tree.selection_remove(old_song_id)

        new_song_id = str(song.get("_id"))
        if self.tree.exists(new_song_id):
            self.tree.selection_set(new_song_id)

        self.current_index = index

        song_id = str(self.songs[self.current_index].get("_id"))
        song_service.add_song_to_history(song_id)

        full_paths_for_player = []
        for s in self.songs:
            if s.get("_id") != "0":
                # Sử dụng SONGS_DIR để xây dựng đường dẫn tuyệt đối đầy đủ
                full_path = str(SONGS_DIR / s["path"])
                full_paths_for_player.append(full_path)

        # 2. Load queue
        player.load_queue(full_paths_for_player)

        player_index = index
        if self.songs and self.songs[0].get("_id") == "0":
            player_index = index - 1

        if player_index < 0:
            player_index = 0

        player.play_index(player_index)

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

    def update_seek(self):
        """Cập nhật thanh trượt và thời gian hiện tại."""
        pos = player.get_position()
        is_mixer_busy = pygame.mixer.music.get_busy()

        # Chỉ xử lý khi trạng thái là ĐANG CHƠI
        if self.is_playing:

            # 1. Cập nhật thanh trượt và thời gian
            if is_mixer_busy or pos < self.song_length:
                self.seek_slider.set(pos)
                self.lbl_time_current.configure(text=self._fmt(pos))

                # CHÚ Ý: Tiếp tục lặp timer chỉ khi đang phát/cập nhật thành công
                self.after(500, self.update_seek)  # <-- Đặt AFTER ở đây nếu đang phát
                return  # Thoát khỏi hàm ngay sau khi cập nhật thành công

            # 2. Xử lý Bài hát đã Kết thúc (End of Song)
            # Chỉ chạy nếu Mixer KHÔNG bận VÀ đã gần hết bài
            # (Lưu ý: Logic này chỉ chạy khi bài hát kết thúc tự nhiên, không phải khi chuyển bài thủ công)
            if not is_mixer_busy and self.current_index != -1 and pos >= self.song_length - 1:

                current_song = self.songs[self.current_index]
                song_id_to_update = str(current_song.get("_id"))

                # ... (Cập nhật Play Count trong DB và Treeview)
                song_service.increment_play_count(song_id_to_update)
                current_plays = current_song.get("play_count", 0)
                new_plays = current_plays + 1
                current_song["play_count"] = new_plays
                current_values = list(self.tree.item(song_id_to_update, 'values'))

                if len(current_values) >= 6:
                    current_values[5] = new_plays
                    self.tree.item(song_id_to_update, values=tuple(current_values))

                # 3. CHUYỂN BÀI TỰ ĐỘNG
                # play_next() sẽ tự gọi self.after(500, self.update_seek) khi kết thúc
                self.play_next()

                return  # Thoát sau khi chuyển bài thành công

        # Nếu self.is_playing là False (người dùng đã tạm dừng/dừng hẳn)
        # HOẶC: Nếu hàm kết thúc mà chưa gọi self.after, ta gọi nó ở đây để đảm bảo vòng lặp timer không bị ngắt.
        self.after(500, self.update_seek)

    def on_seek(self, value):
        """Xử lý khi người dùng kéo thanh seek."""
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
        """Chuyển đổi trạng thái Play/Pause."""
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

            if self.original_cover is not None:
                self.after(50, self.rotate_cover)

    def play_next(self):
        """
        Chuyển đến bài tiếp theo, lặp lại khi đến cuối danh sách.
        FIXED: Đã điều chỉnh logic so sánh đường dẫn để khớp với cấu trúc thư mục 'music'.
        """

        can_move = player.next()
        queue_length = len(player.queue)

        # Xử lý LẶP DANH SÁCH (Loop Queue: Cuối -> Đầu)
        if not can_move and queue_length > 0:
            player.play_index(0)  # Buộc phát bài đầu tiên
            can_move = True

        if can_move:
            # Lấy đường dẫn từ Player Queue và CHUẨN HÓA
            new_song_path = player.queue[player.current_index]
            normalized_path = str(Path(new_song_path).resolve())

            # --- DEBUG START ---
            print(f"--- DEBUG PLAY_NEXT: Start Trace ---")
            print(f"DEBUG: PLAYER PATH: {normalized_path}")
            # --- DEBUG END ---

            # Bắt đầu tìm kiếm bài hát trong self.songs
            new_index = -1
            for i, s in enumerate(self.songs):
                song_file_path = s.get("file_path")

                # Logic dự phòng cho các bản ghi DB chỉ có 'path' cũ
                if not song_file_path and s.get("path"):
                    # Dùng SONGS_DIR để xây dựng đường dẫn tuyệt đối từ DB record
                    # Đây là bước quan trọng nhất: Đảm bảo path này có '/music/'
                    song_file_path = str(SONGS_DIR / s["path"])

                if song_file_path:
                    # CHUẨN HÓA đường dẫn của bản ghi trước khi so sánh
                    song_path_in_list = str(Path(song_file_path).resolve())

                    # Bỏ comment dòng này để so sánh
                    # print(f"DEBUG: Comparing against list item {i}: {song_path_in_list}")

                    if song_path_in_list == normalized_path:
                        new_index = i
                        break

            print(f"DEBUG: NEW INDEX found: {new_index}")

            if new_index != -1:
                # Ghi lịch sử và CẬP NHẬT UI
                new_song_id = str(self.songs[new_index].get("_id"))
                if not new_song_id.startswith("FILE_"):
                    song_service.add_song_to_history(new_song_id)

                self.current_index = new_index
                song = self.songs[new_index]
                self.song_length = max(song.get("duration", 1), 1)

                self.is_playing = True
                self.play_btn.configure(text="⏸")
                self._update_now_playing(song)  # Cập nhật Tên/Tác giả
                self.seek_slider.configure(to=self.song_length, state="normal")
                self.seek_slider.set(0)
                self.lbl_time_total.configure(text=self._fmt(self.song_length))
                self.start_time = time.time()
                self.pause_pos = 0

                # Cập nhật lựa chọn Treeview
                if self.tree.selection():
                    self.tree.selection_remove(self.tree.selection())

                if self.tree.exists(new_song_id):
                    self.tree.selection_set(new_song_id)

            else:
                print("DEBUG: LỖI ĐỒNG BỘ: RESET UI.")
                self.stop_playback_and_reset_ui()
        else:
            print("DEBUG: PLAYER LỖI: RESET UI.")
            self.stop_playback_and_reset_ui()

    def play_prev(self):

        can_move = player.previous()
        queue_length = len(player.queue)
        last_index = queue_length - 1

        # Xử lý LẶP DANH SÁCH (Loop Queue: Đầu -> Cuối)
        if not can_move and last_index >= 0:
            player.play_index(last_index)  # Buộc phát bài cuối cùng
            can_move = True

        if can_move:
            # Lấy đường dẫn từ Player Queue và CHUẨN HÓA
            new_song_path = player.queue[player.current_index]
            normalized_path = str(Path(new_song_path).resolve())

            # Bắt đầu tìm kiếm bài hát trong self.songs
            new_index = -1
            for i, s in enumerate(self.songs):
                song_file_path = s.get("file_path")

                # Logic dự phòng cho các bản ghi DB chỉ có 'path' cũ
                # THAY THẾ self.MUSIC_DIR BẰNG SONGS_DIR
                if not song_file_path and s.get("path"):
                    song_file_path = str(SONGS_DIR / s["path"])

                if song_file_path:
                    # CHUẨN HÓA đường dẫn của bản ghi trước khi so sánh
                    if str(Path(song_file_path).resolve()) == normalized_path:
                        new_index = i
                        break

            if new_index != -1:
                # Ghi lịch sử và CẬP NHẬT UI
                new_song_id = str(self.songs[new_index].get("_id"))
                if not new_song_id.startswith("FILE_"):
                    song_service.add_song_to_history(new_song_id)

                self.current_index = new_index
                song = self.songs[new_index]
                self.song_length = max(song.get("duration", 1), 1)

                self.is_playing = True
                self.play_btn.configure(text="⏸")
                self._update_now_playing(song)
                self.seek_slider.configure(to=self.song_length, state="normal")
                self.seek_slider.set(0)
                self.lbl_time_total.configure(text=self._fmt(self.song_length))
                self.start_time = time.time()
                self.pause_pos = 0

                # Cập nhật lựa chọn Treeview
                if self.tree.selection():
                    self.tree.selection_remove(self.tree.selection())

                if self.tree.exists(new_song_id):
                    self.tree.selection_set(new_song_id)

            else:
                self.stop_playback_and_reset_ui()
        else:
            self.stop_playback_and_reset_ui()

    def stop_playback_and_reset_ui(self):


        # 1. Reset Trạng thái Player
        self.is_playing = False
        self.current_index = -1  # Đặt lại index bài hát đang phát
        self.song_length = 0  # Đặt lại thời lượng bài hát

        # 2. Reset Giao diện Điều khiển
        self.play_btn.configure(text="▶")

        # Đặt lại thời gian hiện tại về 0:00
        self.lbl_time_current.configure(text="0:00")

        # Đặt lại thời gian tổng về 0:00 hoặc --:-- (Tùy theo format bạn muốn)
        self.lbl_time_total.configure(text="0:00")

        # Đặt thanh tìm kiếm về 0 và chuyển sang trạng thái disabled
        self.seek_slider.set(0)
        self.seek_slider.configure(to=100, state="disabled")  # Đặt lại 'to' và disable

        # 3. Xóa lựa chọn Treeview
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

        self._update_now_playing(None)

    def on_volume(self, v):
        """Điều chỉnh âm lượng."""
        player.set_volume(v / 100)

    def _fmt(self, s):
        """Định dạng thời gian từ giây sang 'm:ss'."""
        s = int(s)
        return f"{s // 60}:{s % 60:02d}"

    def _update_cover_image(self, img):
        """Cập nhật đối tượng CTkImage và gán vào label."""
        CORNER_RADIUS_DISC = 32

        if self.cover_img is None:
            self.cover_img = ctk.CTkImage(img, size=(64, 64))

        self.cover_img.configure(light_image=img, dark_image=img)
        self.cover_label.configure(image=self.cover_img, text="", corner_radius=CORNER_RADIUS_DISC)
        self.img_cache = img

        if self.is_playing and self.original_cover is not None:
            self.rotation_angle = 0
            self.after(50, self.rotate_cover)

    def rotate_cover(self):
        """Thực hiện xoay ảnh đĩa khi đang phát nhạc."""
        if not self.is_playing or self.original_cover is None or self.cover_img is None:
            return

        self.rotation_angle = (self.rotation_angle + 1) % 360
        rotated = self.original_cover.rotate(-self.rotation_angle, resample=Image.BICUBIC)

        mask = Image.new('L', (64, 64), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 64, 64), fill=255)
        rotated.putalpha(mask)

        self.cover_img.configure(light_image=rotated, dark_image=rotated)

        self.after(50, self.rotate_cover)

    def _update_now_playing(self, song):
        """
        Cập nhật thông tin và ảnh bìa của bài hát đang phát.
        Đảm bảo sử dụng ảnh mặc định nếu không có ảnh bìa hợp lệ.
        """
        print(f"--- DEBUG: Bắt đầu _update_now_playing ---")

        # 1. Xử lý trường hợp không có bài hát
        if song is None:
            print("DEBUG: song is None. Đặt trạng thái 'Chưa phát'.")
            self.lbl_song_title.configure(text="Chưa phát")
            self.lbl_song_artist.configure(text="--")
            self.original_cover = self.DEFAULT_COVER
            self._update_cover_image(self.original_cover)
            self.add_to_playlist_btn.configure(state="disabled", text_color="#636363")
            self.favorite_btn.configure(text=self.favorite_btn_img_empty)
            print(f"--- DEBUG: Kết thúc _update_now_playing (None) ---")
            return

        # 2. Cập nhật thông tin cơ bản
        title = song.get("title", "Không rõ tiêu đề")
        artist = song.get("artist", "Nghệ sĩ ẩn danh")
        print(f"DEBUG: Cập nhật thông tin: {title} - {artist}")

        self.lbl_song_title.configure(text=title)
        self.lbl_song_artist.configure(text=artist)
        self.add_to_playlist_btn.configure(state="normal", text_color="#B3B3B3")

        # 3. Xử lý Ảnh Bìa (Đã được xử lý lỗi an toàn)
        cover_name = song.get("cover", None)
        cover_path = None

        if cover_name and isinstance(cover_name, str) and cover_name.strip():
            try:
                cover_path = COVERS_DIR / cover_name
                print(f"DEBUG: Tên cover tìm thấy: {cover_name}")
            except Exception:
                cover_path = None
                print("DEBUG: Lỗi khi tạo cover_path từ COVERS_DIR.")

        loaded_cover = None

        if cover_path and cover_path.exists():
            print(f"DEBUG: Bắt đầu tải cover từ: {cover_path}")
            try:
                with Image.open(cover_path) as img_file:
                    loaded_cover = img_file.resize((64, 64)).copy()

                # Áp dụng mask (làm tròn)
                mask = Image.new('L', (64, 64), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 64, 64), fill=255)
                loaded_cover.putalpha(mask)
                print("DEBUG: Tải và xử lý cover thành công.")

            except Exception as e:
                print(f"DEBUG: LỖI KHI TẢI/XỬ LÝ COVER {cover_path}: {e}")
                pass
        else:
            print("DEBUG: Không tìm thấy file cover hoặc cover_name rỗng. Dùng mặc định.")

        # Gán ảnh bìa và gọi hàm cập nhật
        self.original_cover = loaded_cover if loaded_cover else self.DEFAULT_COVER
        self._update_cover_image(self.original_cover)
        print("DEBUG: Đã gọi _update_cover_image.")

        # 4. Kiểm tra trạng thái yêu thích (Favorite)
        try:
            song_id = str(song.get("_id")) if song.get("_id") else None
            print(f"DEBUG: Kiểm tra Favorite cho ID: {song_id}")

            if song_id and song_service.is_favorite(song_id):
                self.favorite_btn.configure(text=self.favorite_btn_img_filled)
                print("DEBUG: Đặt nút Favorite: FILLED")
            else:
                self.favorite_btn.configure(text=self.favorite_btn_img_empty)
                print("DEBUG: Đặt nút Favorite: EMPTY")

        except Exception as e:
            print(f"DEBUG: LỖI kiểm tra favorite: {e}")
            self.favorite_btn.configure(text=self.favorite_btn_img_empty)

        print(f"--- DEBUG: Kết thúc _update_now_playing ---")

    def on_double(self, event):
        """Xử lý sự kiện nhấp đúp chuột trên Treeview."""
        self.play_selected()

    def open_playlists(self):
        """Mở cửa sổ quản lý Playlist."""
        PlaylistWindow(self, on_change=self.load_sidebar_playlists)

    def open_add_song(self):
        """Mở cửa sổ thêm bài hát mới vào thư viện."""
        SongForm(self, on_saved=self.refresh_songs)

    def open_add_to_playlist(self):
        """Mở dialog để chọn Playlist và thêm các bài hát ĐÃ CHỌN từ danh sách chính (nút Sidebar)."""

        selected_iids = self.tree.selection()

        if not selected_iids:
            messagebox.showwarning("Chọn Bài Hát",
                                   "Vui lòng chọn ít nhất một bài hát trong danh sách để thêm vào Playlist.")
            return

        SelectPlaylistDialog(
            master=self,
            song_ids_to_add=list(selected_iids),
            on_success_callback=self.load_sidebar_playlists
        )

    def add_current_song_to_playlist(self):
        """Lấy bài hát ĐANG PHÁT và mở cửa sổ chọn playlist (nút + trên thanh điều khiển)."""

        # 1. Kiểm tra trạng thái của danh sách bài hát
        if not self.songs:
            messagebox.showwarning("Lỗi", "Danh sách bài hát hiện tại đang trống.")
            return

        # 2. Kiểm tra chỉ mục hiện tại có hợp lệ không
        # Chỉ mục hợp lệ phải >= 0 VÀ nhỏ hơn tổng số bài hát.
        if self.current_index < 0 or self.current_index >= len(self.songs):
            messagebox.showwarning("Lỗi", "Không có bài hát nào đang được phát hoặc chỉ mục không hợp lệ.")
            # Trường hợp này bao gồm cả self.current_index == -1
            # (nếu bạn không muốn thông báo 'Không có bài hát nào đang được phát' bị lặp lại)
            return

        # 3. Lấy bài hát an toàn
        current_song = self.songs[self.current_index]
        song_id = str(current_song.get("_id"))

        if not song_id:
            messagebox.showerror("Lỗi ID", "Không tìm thấy ID bài hát.")
            return

        # 4. Mở cửa sổ chọn Playlist
        SelectPlaylistDialog(
            master=self,
            song_ids_to_add=[song_id],
            on_success_callback=self.load_sidebar_playlists
        )

    def load_and_play_playlist(self, songs_list, start_index):
        if not songs_list:
            messagebox.showwarning("Cảnh báo", "Playlist trống!")
            return

        self.songs = songs_list
        self.tree.delete(*self.tree.get_children())
        self.main_title.configure(text="PLAYLIST ĐANG PHÁT")

        COVER_SIZE_TREEVIEW = 40
        self.tree_images = {}

        for song_info in self.songs:
            song_id = str(song_info.get("_id"))
            length = song_info.get("duration", 0)

            # --- SỬA LỖI: Kiểm tra cover_name an toàn ---
            cover_name = song_info.get("cover")  # Lấy None nếu key không tồn tại
            cover_path = None

            # Chỉ tạo cover_path nếu cover_name là chuỗi hợp lệ, không rỗng
            if cover_name and isinstance(cover_name, str) and cover_name.strip():
                try:
                    cover_path = COVERS_DIR / cover_name
                except TypeError:
                    cover_path = None

            pil_img = None

            # Logic xử lý ảnh bìa
            if cover_path and cover_path.exists():
                try:
                    pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                    mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                    pil_img.putalpha(mask)

                except Exception:
                    # Ảnh bị lỗi khi đọc/xử lý, dùng ảnh mặc định
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
            else:
                # Không có tên ảnh/ảnh không tồn tại, dùng ảnh mặc định
                pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
            # --- KẾT THÚC KHỐI SỬA LỖI ---

            tk_img = ImageTk.PhotoImage(pil_img)
            self.tree_images[song_id] = tk_img
            img = tk_img

            self.tree.insert("", "end", iid=song_id, image=img, values=(
                "",
                song_info.get("title", "No Title"),
                song_info.get("artist", "Unknown Artist"),
                song_info.get("album", "Unknown Album"),
                self._fmt(length),
                song_info.get("play_count", 0),
                "☰"
            ))

        self.play_by_index(start_index)

    def increment_play_count(self, song):
        """Tăng số lần nghe và LƯU LỊCH SỬ cho bài hát."""
        song_id = str(song.get("_id"))

        if song_id == "0":
            return

        try:
            new_count = song_service.increment_play_count(song_id)
            song['play_count'] = new_count
            song_service.add_to_history(song_id)

            if self.tree.exists(song_id):
                current_values = list(self.tree.item(song_id, 'values'))
                current_values[4] = new_count
                self.tree.item(song_id, values=tuple(current_values))

        except Exception as e:
            print(f"Lỗi khi cập nhật số lần nghe hoặc lịch sử: {e}")

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        if not row_id or col != "#7":
            return


        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Sửa", command=lambda: self.edit_song(row_id))
        menu.add_command(label="Xóa", command=lambda: self.delete_song_by_id(row_id))
        menu.tk_popup(event.x_root, event.y_root)

    def delete_song_by_id(self, song_id):
        self.tree.selection_set(song_id)
        self.delete_selected_song()

    def edit_song(self, song_id):
        song = next((s for s in self.songs if str(s["_id"]) == song_id), None)
        if not song:
            messagebox.showerror("Lỗi", "Bài hát không tồn tại.")
            return

        SongForm(self, song=song, on_saved=self.refresh_songs)

    def create_three_dot_icon(self, size=24, color="white"):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        dot_radius = size // 8
        spacing = size // 4
        y = size // 2
        for i in range(3):
            x = spacing + i * spacing + dot_radius
            draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius), fill=color)
        return ImageTk.PhotoImage(img)

    def reset_treeview_style(self):
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=45)

    def load_favorite_songs(self):
        """Tải và hiển thị các bài hát yêu thích."""
        self.main_title.configure(text="BÀI HÁT YÊU THÍCH")
        self.current_view_is_playlist = True
        self.current_playlist_id = None

        self.tree.delete(*self.tree.get_children())
        self.tree_images = {}
        self.songs = []  # Reset danh sách songs của cửa sổ

        try:
            # Lấy danh sách bài hát yêu thích từ service
            self.songs = song_service.get_favorite_songs()
        except Exception as e:
            messagebox.showerror("Lỗi Database", f"Không thể tải bài hát yêu thích: {e}")
            return

        COVER_SIZE_TREEVIEW = 40

        for song_info in self.songs:
            song_id = str(song_info.get("_id"))

            cover_name = song_info.get("cover")
            cover_path = None

            # 1. Kiểm tra và Tạo đường dẫn Ảnh Bìa
            if cover_name and isinstance(cover_name, str) and cover_name.strip():
                try:
                    # COVERS_DIR là hằng số đã được định nghĩa
                    cover_path = COVERS_DIR / cover_name
                except TypeError:
                    cover_path = None

            pil_img = None

            # 2. Xử lý Ảnh Bìa (Làm tròn)
            if cover_path and cover_path.exists():
                try:
                    # Ảnh bìa tồn tại và hợp lệ
                    pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                    # Áp dụng mask (làm tròn)
                    mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                    pil_img.putalpha(mask)

                except Exception:
                    # Lỗi khi mở/xử lý ảnh: dùng ảnh mặc định
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
            else:
                # Không có tên ảnh hoặc file không tồn tại: dùng ảnh mặc định
                pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

            # 3. Chèn vào Treeview
            tk_img = ImageTk.PhotoImage(pil_img)
            self.tree_images[song_id] = tk_img  # Lưu tk_img để tránh bị garbage collection

            self.tree.insert("", "end", iid=song_id, image=tk_img, values=(
                "",
                song_info.get("title", "No Title"),
                song_info.get("artist", "Unknown Artist"),
                song_info.get("album", "Unknown Album"),
                self._fmt(song_info.get("duration", 0)),
                song_info.get("play_count", 0),
                "☰"  # Hoặc bất kỳ ký tự nào đại diện cho menu
            ))

        # 4. Thiết lập lựa chọn đầu tiên
        if self.songs and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

    # --- HÀM MỚI: TOGGLE FAVORITE ---

    def toggle_favorite_current_song(self):
        """Đánh dấu/Bỏ đánh dấu yêu thích cho bài hát đang phát và cập nhật UI."""

        # Đảm bảo có bài hát đang được phát (hoặc đang chọn trong danh sách)
        if self.current_index == -1 or not self.songs:
            messagebox.showwarning("Cảnh báo", "Không có bài hát nào được chọn/phát.")
            return

        current_song = self.songs[self.current_index]
        song_id = str(current_song.get("_id"))

        # Không thể thao tác với các bài hát chưa lưu DB
        if song_id.startswith("FILE_"):
            messagebox.showwarning("Cảnh báo", "Không thể đánh dấu bài hát chưa được lưu vào Database là Yêu thích.")
            return

        try:
            # Gọi service để thay đổi trạng thái yêu thích trong DB
            new_status = song_service.toggle_favorite(song_id)

            if new_status is None:
                messagebox.showerror("Lỗi", "Không tìm thấy bài hát trong cơ sở dữ liệu để cập nhật.")
                return

            # 1. Cập nhật nút Yêu thích (trên thanh player)
            # Giả định bạn có self.favorite_btn_img_filled và self.favorite_btn_img_empty
            if new_status:
                self.favorite_btn.configure(text=self.favorite_btn_img_filled)
            else:
                self.favorite_btn.configure(text=self.favorite_btn_img_empty)

            # 2. Cập nhật trạng thái trong danh sách songs hiện tại (self.songs)
            current_song["favorite"] = new_status
            # Nếu đang ở view Yêu thích (phải reload để loại bỏ bài vừa bỏ yêu thích)
            if self.main_title.cget("text") == "BÀI HÁT YÊU THÍCH":
                self.load_favorite_songs()  # Tải lại toàn bộ danh sách yêu thích

            # Có thể thêm logic cập nhật lại chỉ một hàng trong Treeview nếu đang ở view All Songs
            # Nhưng để đơn giản, ta sẽ chỉ reload toàn bộ view khi cần thiết

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể cập nhật yêu thích: {e}")

    def play_random_song(self):
        """Phát ngẫu nhiên 1 bài trong danh sách hiện tại."""
        if not self.songs:
            messagebox.showwarning("Danh sách trống", "Không có bài hát nào để phát.")
            return

        index = random.randint(0, len(self.songs) - 1)
        self.play_by_index(index)

    def filter_songs(self, songs_list):
        """Lọc bài hát dựa trên thanh tìm kiếm và plays."""

        # 1. XỬ LÝ THANH TÌM KIẾM (SEARCH QUERY)
        query = self.search_var.get().lower().strip()
        DEFAULT_SEARCH_TEXT = "tìm bài hát, album, nghệ sĩ..."

        if query == DEFAULT_SEARCH_TEXT:
            query = ""

        # 2. XỬ LÝ BỘ LỌC SỐ LẦN NGHE (PLAYS)
        min_plays_str = ""
        try:
            # Lấy giá trị chuỗi, đảm bảo strip() hoạt động
            min_plays_str = self.plays_var.get().strip()
        except Exception:
            pass

        # 🌟 ĐẢM BẢO CHUYỂN ĐỔI SANG SỐ NGUYÊN (INT) 🌟
        # Xử lý chuỗi rỗng ("") và lỗi nhập liệu:
        try:
            # Nếu chuỗi rỗng ("") -> 0
            min_plays = int(min_plays_str) if min_plays_str else 0
        except ValueError:
            # Nếu người dùng nhập ký tự không phải số -> 0
            min_plays = 0

        filtered = []
        for s in songs_list:
            title = s.get("title", "").lower()
            artist = s.get("artist", "").lower()
            album = s.get("album", "").lower()
            plays = s.get("play_count", 0)  # plays là INT

            # Lọc 1: Tìm kiếm theo chuỗi (Query)
            if query:
                if query not in title and query not in artist and query not in album:
                    continue

            # Lọc 2: Theo số lần nghe tối thiểu (Plays)
            # So sánh INT < INT
            if plays < min_plays:
                continue

            filtered.append(s)

        return filtered

    def on_search_filter_change(self, event=None):
        """Lọc danh sách bài hát hiển thị trong Treeview dựa trên từ khóa tìm kiếm và số lần nghe tối thiểu."""

        # 1. Lấy giá trị từ các bộ lọc và CHUYỂN ĐỔI AN TOÀN SANG SỐ

        search_term = self.search_var.get().lower().strip()

        # --- Xử lý min_plays: Chuyển đổi từ STRING (từ StringVar) sang INT an toàn ---
        min_plays_str = self.plays_var.get().strip()

        try:
            # Nếu chuỗi rỗng ("") -> 0, nếu là số hợp lệ -> INT
            min_plays = int(min_plays_str) if min_plays_str else 0
        except ValueError:
            # Nếu người dùng nhập ký tự không phải số
            min_plays = 0
        # --- Kết thúc xử lý min_plays ---

        self.tree.delete(*self.tree.get_children())
        self.tree_images = {}

        COVER_SIZE_TREEVIEW = 40

        for song_info in self.songs:

            title = song_info.get("title", "").lower()
            artist = song_info.get("artist", "").lower()
            album = song_info.get("album", "").lower()
            plays = song_info.get("play_count", 0)  # plays là INT

            # 2. Logic Lọc

            # Lọc theo văn bản
            is_matching_text = (
                    search_term == "" or
                    search_term in title or
                    search_term in artist or
                    search_term in album
            )

            # Lọc theo số lần nghe (Bây giờ: INT >= INT)
            is_matching_plays = plays >= min_plays

            if is_matching_text and is_matching_plays:

                song_id = str(song_info.get("_id"))
                length = song_info.get("duration", 0)

                # SỬA LỖI TẠI ĐÂY: Đảm bảo cover_name là một chuỗi không rỗng
                # Giá trị mặc định là "" đã an toàn hơn None, nhưng ta cần kiểm tra lại
                cover_name = song_info.get("cover", "")

                pil_img = None

                # --- LOGIC XỬ LÝ COVER MỚI ---

                # CHỈ TẠO cover_path NẾU cover_name KHÔNG RỖNG VÀ KIỂM TRA TỒN TẠI
                if cover_name and isinstance(cover_name, str) and cover_name.strip():
                    cover_path = COVERS_DIR / cover_name
                    if cover_path.exists():
                        try:
                            # Tải và xử lý ảnh cover thực
                            pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                            # Áp dụng mask hình tròn
                            mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                            draw = ImageDraw.Draw(mask)
                            draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                            pil_img.putalpha(mask)

                        except Exception:
                            # Nếu xảy ra lỗi khi mở/xử lý ảnh (dù file tồn tại)
                            pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

                # Nếu cover_name rỗng hoặc không phải string, HOẶC file không tồn tại, sử dụng DEFAULT_COVER
                if pil_img is None:
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

                # --- KẾT THÚC LOGIC XỬ LÝ COVER MỚI ---

                tk_img = ImageTk.PhotoImage(pil_img)
                self.tree_images[song_id] = tk_img

                self.tree.insert("", "end", iid=song_id, image=tk_img, values=(
                    "",
                    song_info.get("title", "No Title"),
                    song_info.get("artist", "Unknown Artist"),
                    song_info.get("album", "Unknown Album"),
                    self._fmt(length),
                    plays,
                    "☰"
                ))

    def open_ranking_chart(self):
        """Tải và hiển thị bảng xếp hạng 20 bài hát được nghe nhiều nhất."""

        self.main_title.configure(text="BẢNG XẾP HẠNG")

        # Dọn dẹp Treeview và cache ảnh
        self.tree.delete(*self.tree.get_children())
        self.tree_images = {}

        try:
            # 1. Lấy và xếp hạng bài hát
            songs = song_service.get_songs()
            # Xếp hạng dựa trên play_count (mặc định là 0 nếu thiếu)
            ranked = sorted(songs, key=lambda x: x.get("play_count", 0), reverse=True)[:20]
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải dữ liệu xếp hạng: {e}")
            return

        self.songs = ranked  # Cập nhật danh sách bài hát hiện tại (quan trọng cho các thao tác khác)
        COVER_SIZE = 40

        # 2. Xử lý và chèn từng bài hát vào Treeview
        for idx, song in enumerate(ranked, start=1):
            song_id = str(song["_id"])

            # --- SỬA LỖI: Xử lý cover_name an toàn ---
            cover_name = song.get("cover")  # Mặc định là None nếu key không tồn tại
            cover_path = None

            # Chỉ tạo cover_path nếu cover_name là chuỗi hợp lệ và không rỗng
            if cover_name and isinstance(cover_name, str) and cover_name.strip():
                try:
                    cover_path = COVERS_DIR / cover_name
                except TypeError:
                    cover_path = None
            # --- Kết thúc SỬA LỖI ---

            pil_img = None

            # 3. Logic Xử lý Ảnh Bìa
            if cover_path and cover_path.exists():
                try:
                    pil_img = Image.open(cover_path).resize((COVER_SIZE, COVER_SIZE)).copy()

                    # Áp dụng mask (làm tròn)
                    mask = Image.new('L', (COVER_SIZE, COVER_SIZE), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, COVER_SIZE, COVER_SIZE), fill=255)
                    pil_img.putalpha(mask)

                except Exception:
                    # Ảnh bị lỗi khi đọc/xử lý, dùng ảnh mặc định
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE, COVER_SIZE))
            else:
                # Không có tên ảnh/ảnh không tồn tại, dùng ảnh mặc định
                pil_img = self.DEFAULT_COVER.resize((COVER_SIZE, COVER_SIZE))

            # 4. Tạo và Chèn vào Treeview
            tk_img = ImageTk.PhotoImage(pil_img)
            self.tree_images[song_id] = tk_img  # Lưu cache ảnh

            # Tạo huy chương
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx}"

            self.tree.insert(
                "",
                "end",
                iid=song_id,
                image=tk_img,
                values=(
                    "",
                    f"{medal}  {song.get('title', 'No Title')}",
                    song.get("artist", "Unknown Artist"),
                    song.get("album", "Unknown Album"),
                    self._fmt(song.get("duration", 0)),
                    song.get("play_count", 0),
                    "☰"
                )
            )

        # Thiết lập lựa chọn cho bài hát đầu tiên
        if self.songs and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

    def load_song_history(self):
        """Tải và hiển thị danh sách các bài hát duy nhất đã nghe gần đây lên Treeview chính."""

        self.main_title.configure(text="LỊCH SỬ NGHE NHẠC")
        self.current_view_is_playlist = True
        self.current_playlist_id = "HISTORY"

        # 1. Xóa sạch Treeview trước khi tải mới
        self.tree.delete(*self.tree.get_children())
        self.songs = []
        self.tree_images = {}

        try:
            # Lấy toàn bộ lịch sử nghe (Giả định history_records được sắp xếp từ mới nhất đến cũ nhất)
            history_records = song_service.get_song_history()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải Lịch sử nghe nhạc: {e}")
            return

        # LỌC: Chỉ giữ lại một bản sao duy nhất cho mỗi bài hát (bản ghi mới nhất)
        unique_songs_list = []
        seen_song_ids = set()

        for song_record in history_records:
            song_id = str(song_record.get("_id"))

            if song_id not in seen_song_ids:
                seen_song_ids.add(song_id)
                unique_songs_list.append(song_record)

        self.songs = unique_songs_list

        self.reset_treeview_style()
        COVER_SIZE_TREEVIEW = 40

        # 2. Chèn các bài hát đã lọc vào Treeview
        for song_info in self.songs:
            song_id = str(song_info.get("_id"))
            length = song_info.get("duration", 0)

            # --- SỬA LỖI: Kiểm tra cover_name trước khi tạo đường dẫn (Lỗi dòng 1466) ---
            cover_name = song_info.get("cover")
            cover_path = None

            # Chỉ tạo cover_path nếu cover_name là chuỗi hợp lệ
            if cover_name and isinstance(cover_name, str) and cover_name.strip():
                try:
                    cover_path = COVERS_DIR / cover_name
                except TypeError:
                    cover_path = None

            pil_img = None

            # Logic xử lý ảnh bìa
            if cover_path and cover_path.exists():
                try:
                    pil_img = Image.open(cover_path).resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW)).copy()

                    # Áp dụng mask
                    mask = Image.new('L', (COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0, COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW), fill=255)
                    pil_img.putalpha(mask)

                except Exception:
                    # Dùng ảnh mặc định nếu ảnh bị lỗi
                    pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))
            else:
                # Dùng ảnh mặc định nếu không có tên ảnh hoặc file không tồn tại
                pil_img = self.DEFAULT_COVER.resize((COVER_SIZE_TREEVIEW, COVER_SIZE_TREEVIEW))

            # Chuyển đổi và lưu trữ ảnh
            tk_img = ImageTk.PhotoImage(pil_img)
            img = tk_img
            self.tree_images[song_id] = img

            # 3. Chèn vào Treeview
            self.tree.insert("", "end", iid=song_id, image=img, values=(
                "",
                song_info.get("title", "No Title"),
                song_info.get("artist", "Unknown Artist"),
                song_info.get("album", "Unknown Album"),
                self._fmt(length),
                song_info.get("play_count", 0),
                "☰"
            ))

        # 4. Chọn bài hát đầu tiên nếu có
        if self.songs and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()