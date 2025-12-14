import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from services.song_service import create_song, get_song, update_song
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
# Import này cần thiết để xử lý metadata từ tags
from mutagen.id3 import ID3NoHeaderError
from PIL import Image, ImageTk
from services.song_service import COVERS_DIR  # Đảm bảo COVERS_DIR được import đúng


class SongForm(ctk.CTkToplevel):
    def __init__(self, master, on_saved, song=None):
        super().__init__(master)
        self.title("Thêm/Sửa Bài Hát")
        self.transient(master)
        self.resizable(False, False)

        self.on_saved = on_saved
        self.song = song

        self.file_path = ""
        self.cover_path = ""
        self.duration = 0

        self.build()
        if song:
            self.load_song()

    def show_cover_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((100, 100))
            self.cover_img = ImageTk.PhotoImage(img)
            self.cover_preview.configure(image=self.cover_img)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể hiển thị ảnh: {e}")

    def _get_media_duration(self, file_path):
        """Tính thời lượng (giây) từ file audio."""
        try:
            p = Path(file_path)
            if p.suffix.lower() == '.mp3':
                audio = MP3(file_path)
                return int(audio.info.length)
            elif p.suffix.lower() == '.wav':
                audio = WAVE(file_path)
                return int(audio.info.length)
            return 0
        except Exception:
            return 0

    # --- HÀM MỚI: TRÍCH XUẤT METADATA TỰ ĐỘNG ---
    def _get_metadata(self, file_path):
        """Trích xuất Title, Artist, Album từ file audio và cập nhật form."""
        p = Path(file_path)
        default_title = p.stem

        try:
            if p.suffix.lower() == '.mp3':
                # Dùng EasyMP3 để dễ đọc tag hơn, nếu không có ID3 header sẽ báo lỗi
                audio = MP3(file_path)
            elif p.suffix.lower() == '.wav':
                audio = WAVE(file_path)
            else:
                return

                # Hàm trợ giúp để lấy giá trị tag an toàn

            def get_tag_value(tag_key, audio_obj):
                tag = audio_obj.get(tag_key)
                if tag:
                    # Đối với MP3 ID3 Tag (TIT2, TPE1, TALB)
                    if isinstance(tag, list):
                        return str(tag[0]).strip() if tag else None
                    # Đối với EasyMP3 hoặc các tag khác
                    return str(tag).strip()
                return None

            # TIT2/title: Tiêu đề; TPE1/artist: Nghệ sĩ; TALB/album: Album
            title = get_tag_value('TIT2', audio) or get_tag_value('title', audio)
            artist = get_tag_value('TPE1', audio) or get_tag_value('artist', audio)
            album = get_tag_value('TALB', audio) or get_tag_value('album', audio)

            # Cập nhật các biến StringVar
            self.title_var.set(title or default_title)
            self.artist_var.set(artist or "")
            self.album_var.set(album or "")

        except ID3NoHeaderError:
            # Xử lý trường hợp file MP3 không có ID3 tag, chỉ điền tên file
            self.title_var.set(default_title)
            self.artist_var.set("")
            self.album_var.set("")
        except Exception as e:
            # Xử lý các lỗi khác, điền tên file
            self.title_var.set(default_title)
            self.artist_var.set("")
            self.album_var.set("")
            print(f"Cảnh báo: Không thể đọc metadata từ file {file_path}. {e}")

    # --- END HÀM MỚI ---

    def build(self):
        frm = ctk.CTkFrame(self)
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frm.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="Tiêu đề:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.title_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.title_var, width=280).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(frm, text="Nghệ sĩ:", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.artist_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.artist_var, width=280).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(frm, text="Album:", anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.album_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.album_var, width=280).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(frm, text="File Nhạc:", anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.file_var = ctk.StringVar()
        self.file_entry = ctk.CTkEntry(frm, textvariable=self.file_var, width=200, state="readonly")
        self.file_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkButton(frm, text="Chọn", width=70, command=self.browse_file).grid(row=3, column=2, padx=5, pady=5)

        ctk.CTkLabel(frm, text="Ảnh Bìa:", anchor="w").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.cover_var = ctk.StringVar()
        self.cover_entry = ctk.CTkEntry(frm, textvariable=self.cover_var, width=200, state="readonly")
        self.cover_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkButton(frm, text="Chọn", width=70, command=self.browse_cover).grid(row=4, column=2, padx=5, pady=5)

        self.cover_preview = ctk.CTkLabel(frm, text="", width=100, height=100)
        self.cover_preview.grid(row=4, column=3, padx=10, pady=5)

        btn_fr = ctk.CTkFrame(frm, fg_color="transparent")
        btn_fr.grid(row=5, column=0, columnspan=3, pady=15)

        ctk.CTkButton(btn_fr, text="Lưu", command=self.save, fg_color="#1DB954", hover_color="#1ed760").pack(
            side="left", padx=10)
        ctk.CTkButton(btn_fr, text="Hủy", command=self.destroy).pack(side="left", padx=10)

    def browse_file(self):
        p = filedialog.askopenfilename(
            parent=self,
            title="Chọn file nhạc",
            filetypes=[("Audio files", "*.mp3 *.wav")]
        )
        if p:
            self.file_path = p
            self.file_var.set(Path(p).name)

            # --- CẬP NHẬT: Tự động điền metadata và thời lượng ---
            self.duration = self._get_media_duration(p)
            self._get_metadata(p)  # <-- Gọi hàm trích xuất metadata
            # ----------------------------------------------------

    def browse_cover(self):
        p = filedialog.askopenfilename(
            parent=self,
            title="Chọn ảnh bìa",
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if p:
            self.cover_path = p
            self.cover_var.set(Path(p).name)
            self.show_cover_preview(p)

    def load_song(self):
        self.title_var.set(self.song.get("title", ""))
        self.artist_var.set(self.song.get("artist", ""))
        self.album_var.set(self.song.get("album", ""))

        # LƯU Ý QUAN TRỌNG: Các bản ghi cũ sử dụng 'path' (tên file), bản ghi mới/migrate sử dụng 'file_path' (tuyệt đối)
        self.file_path = self.song.get("file_path", "")  # Ưu tiên file_path tuyệt đối
        if not self.file_path:
            # Nếu không có file_path, tái tạo lại từ path cũ và thư mục nhạc gốc (nếu có)
            if self.song.get("path"):
                # Giả sử bạn có thể truy cập SONGS_DIR từ đâu đó hoặc tái tạo nó
                # Ở đây ta chỉ lấy tên file để hiển thị
                self.file_path = self.song.get("path")

        self.cover_path = self.song.get("cover", "")
        self.duration = self.song.get("duration", 0)

        self.file_var.set(Path(self.file_path).name)
        self.cover_var.set(Path(self.cover_path).name if self.cover_path else "")

        if self.cover_path:
            # Dùng COVERS_DIR đã được import từ services.song_service
            full_path = COVERS_DIR / self.cover_path
            if full_path.exists():
                self.show_cover_preview(full_path)

    def save(self):
        title = self.title_var.get().strip()
        artist = self.artist_var.get().strip()
        album = self.album_var.get().strip()

        file_to_copy = self.file_path
        cover_to_copy = self.cover_path

        if not title or not artist or not file_to_copy:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Tiêu đề, Nghệ sĩ và chọn File Nhạc.")
            return

        try:
            if self.song:
                data = {
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": self.duration
                }
                # update_song cần ID, data, file_path tuyệt đối, cover_path tuyệt đối (hoặc tên)
                update_song(str(self.song.get("_id")), data, file_to_copy, cover_to_copy)
                messagebox.showinfo("Thành công", "Bài hát đã được cập nhật")
            else:
                if self.duration == 0:
                    self.duration = self._get_media_duration(file_to_copy)

                # create_song cần file_path tuyệt đối
                create_song(title, artist, album, file_to_copy, cover_to_copy, self.duration)
                messagebox.showinfo("Thành công", "Bài hát đã được thêm")

            self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi xảy ra trong quá trình lưu: {e}")