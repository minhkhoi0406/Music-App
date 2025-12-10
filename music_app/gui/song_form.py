import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from services.song_service import create_song, get_song, update_song


# Đổi từ tk.Toplevel sang ctk.CTkToplevel
class SongForm(ctk.CTkToplevel):
    def __init__(self, master, on_saved, song=None):
        super().__init__(master)
        self.title("Thêm/Sửa Bài Hát")
        self.transient(master)
        self.resizable(False, False)

        self.on_saved = on_saved
        self.song = song

        # Lưu trữ đường dẫn file nhạc và cover
        self.file_path = ""
        self.cover_path = ""

        self.build()
        if song:
            self.load_song()

    def build(self):
        # Sử dụng ctk.CTkFrame thay cho ttk.Frame
        frm = ctk.CTkFrame(self)  # Bỏ padding=20
        # Thêm padx, pady vào grid của frm để tạo khoảng đệm cho frame này so với cửa sổ
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frm.grid_columnconfigure(1, weight=1)

        # Hàng 0: Title
        ctk.CTkLabel(frm, text="Tiêu đề:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.title_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.title_var, width=280).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Hàng 1: Artist
        ctk.CTkLabel(frm, text="Nghệ sĩ:", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.artist_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.artist_var, width=280).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Hàng 2: Album
        ctk.CTkLabel(frm, text="Album:", anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.album_var = ctk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.album_var, width=280).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Hàng 3: File Nhạc
        ctk.CTkLabel(frm, text="File Nhạc:", anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.file_var = ctk.StringVar()
        self.file_entry = ctk.CTkEntry(frm, textvariable=self.file_var, width=200, state="readonly")
        self.file_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkButton(frm, text="Chọn", width=70, command=self.browse_file).grid(row=3, column=2, padx=5, pady=5)

        # Hàng 4: Cover
        ctk.CTkLabel(frm, text="Ảnh Bìa:", anchor="w").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.cover_var = ctk.StringVar()
        self.cover_entry = ctk.CTkEntry(frm, textvariable=self.cover_var, width=200, state="readonly")
        self.cover_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkButton(frm, text="Chọn", width=70, command=self.browse_cover).grid(row=4, column=2, padx=5, pady=5)

        # Hàng 5: Nút
        btn_fr = ctk.CTkFrame(frm, fg_color="transparent")
        btn_fr.grid(row=5, column=0, columnspan=3, pady=15)

        # Nút Save/Update
        ctk.CTkButton(btn_fr, text="Lưu", command=self.save, fg_color="#1DB954", hover_color="#1ed760").pack(
            side="left", padx=10)
        # Nút Cancel
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

    def browse_cover(self):
        p = filedialog.askopenfilename(
            parent=self,
            title="Chọn ảnh bìa",
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if p:
            self.cover_path = p
            self.cover_var.set(Path(p).name)

    def load_song(self):
        # Logic này chỉ load dữ liệu, không load path file nhạc gốc
        self.title_var.set(self.song.get("title", ""))
        self.artist_var.set(self.song.get("artist", ""))
        self.album_var.set(self.song.get("album", ""))

        # Hiển thị tên file nhạc và cover (nếu có)
        self.file_path = ""
        self.cover_path = ""
        # Gán path để update biết file nào được copy (chỉ cần thiết cho update)
        self.file_path = self.song.get("path", "")
        self.cover_path = self.song.get("cover", "")

    def save(self):
        # ... (Phần lấy dữ liệu)
        title = self.title_var.get().strip()
        artist = self.artist_var.get().strip()
        album = self.album_var.get().strip()

        # Dùng đường dẫn tuyệt đối đã chọn trong browse_file()
        file_to_copy = self.file_path
        cover_to_copy = self.cover_path

        # ... (Phần kiểm tra validation)

        try:
            if self.song:
                # Logic Update
                data = {"title": title, "artist": artist, "album": album}
                # Thêm logic update cover nếu cover_to_copy là đường dẫn mới
                update_song(str(self.song.get("_id")), data)
                messagebox.showinfo("Thành công", "Bài hát đã được cập nhật")
            else:
                # Logic Create (Gọi service để sao chép từ file_to_copy sang thư mục music/)
                create_song(title, artist, album, file_to_copy, cover_to_copy)
                messagebox.showinfo("Thành công", "Bài hát đã được thêm")

            self.on_saved()
            self.destroy()
        except Exception as e:
            # LỖI WIEROR 32 XẢY RA Ở ĐÂY
            messagebox.showerror("Lỗi", f"Lỗi xảy ra trong quá trình lưu: {e}")