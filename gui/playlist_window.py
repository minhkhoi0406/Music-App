import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
# 1. CẬP NHẬT IMPORT: Dùng update_playlist_name thay cho update_playlist
from services.playlist_service import create_playlist, get_playlists, update_playlist_name, delete_playlist, \
    get_songs_in_playlist, remove_song_from_playlist
from gui.select_playlist_dialog import SelectPlaylistDialog

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

COLOR_BACKGROUND = "#121212"
COLOR_SIDEBAR = "#000000"
COLOR_PLAYER_BAR = "#181818"
COLOR_ACCENT = "#1DB954"


class PlaylistWindow(ctk.CTkToplevel):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.title("Quản Lý Playlists")
        self.transient(master)
        self.geometry("850x550")
        self.minsize(800, 500)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.master = master
        self.on_change = on_change

        self.playlists = []
        self.selected_playlist_id = None
        self.playlist_songs = []

        # === BỔ SUNG: KHAI BÁO FONT ĐỂ ĐỒNG BỘ VỚI MAIN WINDOW ===
        self.APP_FONT_FAMILY = "Arial"
        self.TITLE_FONT = ctk.CTkFont(family=self.APP_FONT_FAMILY, size=18, weight="bold")
        self.BUTTON_FONT = ctk.CTkFont(family=self.APP_FONT_FAMILY, size=14, weight="bold")
        self.LABEL_FONT = ctk.CTkFont(family=self.APP_FONT_FAMILY, size=14)
        self.TREEVIEW_FONT_SIZE = 12
        self.TREEVIEW_FONT_STYLE = (self.APP_FONT_FAMILY, self.TREEVIEW_FONT_SIZE)
        self.TREEVIEW_HEADING_FONT_STYLE = (self.APP_FONT_FAMILY, self.TREEVIEW_FONT_SIZE, 'bold')

        self._apply_treeview_style()
        self.build()
        self.refresh()

        self.configure(fg_color=COLOR_BACKGROUND)

    # --- CÁC HÀM KHÁC (GIỮ NGUYÊN) ---

    def on_closing(self):
        """Xử lý khi đóng cửa sổ."""
        self.grab_release()
        self.destroy()

    def _fmt(self, s):
        """Định dạng thời gian từ giây sang 'm:ss'."""
        s = int(s)
        return f"{s // 60}:{s % 60:02d}"

    def _apply_treeview_style(self):
        s = ttk.Style()
        s.theme_use("default")

        # ===== STYLE RIÊNG CHO PLAYLIST WINDOW (Đã giữ lại) =====
        s.configure(
            "Playlist.Treeview",
            background="#121212",
            foreground="white",
            rowheight=50,
            fieldbackground="#121212",
            font=self.TREEVIEW_FONT_STYLE
        )

        s.map(
            "Playlist.Treeview",
            background=[('selected', '#2A2A2A')],
            foreground=[('selected', '#1DB954')]
        )

        s.configure(
            "Playlist.Treeview.Heading",
            background="#121212",
            foreground="#B3B3B3",
            font=self.TREEVIEW_HEADING_FONT_STYLE
        )

    def build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        playlist_container = ctk.CTkFrame(self, fg_color="transparent")
        playlist_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        playlist_container.grid_rowconfigure(1, weight=1)
        playlist_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(playlist_container,
                     text="DANH SÁCH PLAYLIST",
                     font=self.TITLE_FONT
                     ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Treeview cho Playlist
        self.tree = ttk.Treeview(playlist_container, columns=("name", "count"), show="headings", selectmode="browse",
                                 style="Playlist.Treeview")
        self.tree.heading("name", text="Tên Playlist")
        self.tree.column("name", width=200, anchor="w")
        self.tree.heading("count", text="Bài", anchor="center")
        self.tree.column("count", width=40, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")

        self.tree.bind("<<TreeviewSelect>>", self.on_playlist_select)

        btn_fr = ctk.CTkFrame(playlist_container, fg_color="transparent")
        btn_fr.grid(row=2, column=0, pady=(10, 0))

        ctk.CTkButton(btn_fr, text=" Thêm", command=self.add, fg_color="#1DB954", hover_color="#1ed760",
                      font=self.BUTTON_FONT).pack(
            side="left", padx=5)
        ctk.CTkButton(btn_fr, text=" Sửa", command=self.edit, font=self.BUTTON_FONT).pack(side="left", padx=5)
        ctk.CTkButton(btn_fr, text=" Xóa", command=self.delete, fg_color="red", hover_color="#cc0000",
                      font=self.BUTTON_FONT).pack(
            side="left",
            padx=5)

        songs_container = ctk.CTkFrame(self, fg_color="#181818", corner_radius=10)
        songs_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        songs_container.grid_rowconfigure(1, weight=1)
        songs_container.grid_columnconfigure(0, weight=1)

        self.songs_title_label = ctk.CTkLabel(
            songs_container,
            text="BÀI HÁT TRONG PLAYLIST (Chọn một Playlist)",
            font=self.TITLE_FONT
        )
        self.songs_title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # Treeview cho Bài hát
        self.song_tree = ttk.Treeview(
            songs_container,
            columns=("title", "artist", "duration"),
            show="headings",
            selectmode="browse",
            style="Playlist.Treeview"  # Áp dụng style Treeview
        )
        self.song_tree.heading("title", text="TITLE")
        self.song_tree.column("title", width=300, anchor="w")
        self.song_tree.heading("artist", text="ARTIST")
        self.song_tree.column("artist", width=200, anchor="w")
        self.song_tree.heading("duration", text="TIME")
        self.song_tree.column("duration", width=80, anchor="w")

        self.song_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.song_tree.bind("<Double-1>", self.play_selected_playlist_song)

        ctk.CTkButton(
            songs_container,
            text="➖ Xóa khỏi Playlist",
            command=self.remove_song_from_playlist,
            fg_color="#CC0000",
            hover_color="#FF3333",
            font=self.BUTTON_FONT
        ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")

    # --- HÀM ADD ĐÃ SỬA FONT CHO WIDGET BÊN TRONG ---
    def add(self):
        """Tạo Playlist mới."""
        dialog = ctk.CTkInputDialog(text="Nhập tên Playlist:", title="Tạo Playlist Mới")

        # *** GHI ĐÈ FONT CỦA WIDGET BÊN TRONG ***
        try:
            dialog.label.configure(font=self.LABEL_FONT)
            dialog.button_ok.configure(font=self.BUTTON_FONT)
            dialog.button_cancel.configure(font=self.BUTTON_FONT)
        except AttributeError:
            pass

        name = dialog.get_input()

        if name:
            try:
                create_playlist(name)
                messagebox.showinfo("Thành công", "Playlist đã được tạo")
                self.refresh()
            except Exception as e:
                # Bắt lỗi ValueError (Lỗi trùng tên) từ service và hiển thị rõ ràng
                if isinstance(e, ValueError):
                    messagebox.showerror("Lỗi Tạo Playlist", str(e))
                else:
                    messagebox.showerror("Lỗi Database", f"Không thể tạo Playlist: {e}")

    # --- HÀM EDIT ĐÃ SỬA LỖI default_text VÀ FONT CHO WIDGET BÊN TRONG ---
    def edit(self):
        """Sửa tên Playlist đã chọn."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một Playlist để sửa tên.")
            return

        playlist_id = sel[0]
        current_playlist = next((p for p in self.playlists if str(p.get('_id')) == playlist_id), None)
        if not current_playlist:
            messagebox.showerror("Lỗi", "Playlist không tồn tại trong bộ nhớ.")
            return

        # SỬA LỖI: BỎ default_text. CTkInputDialog chỉ nhận title và text.
        dialog = ctk.CTkInputDialog(text="Nhập tên mới cho Playlist:", title="Sửa Tên Playlist")

        # *** CAN THIỆP ĐỂ THIẾT LẬP GIÁ TRỊ MẶC ĐỊNH VÀ SỬA FONT ***
        try:
            # 1. Thiết lập giá trị mặc định (Tên Playlist cũ)
            entry = dialog._entry  # Truy cập vào CTkEntry nội bộ
            entry.delete(0, tk.END)
            entry.insert(0, current_playlist.get('name'))

            # 2. Sửa font
            dialog.label.configure(font=self.LABEL_FONT)
            dialog.button_ok.configure(font=self.BUTTON_FONT)
            dialog.button_cancel.configure(font=self.BUTTON_FONT)
        except AttributeError:
            pass  # Bỏ qua nếu cấu trúc nội bộ CTK không cho phép truy cập _entry

        new_name = dialog.get_input()

        if new_name and new_name != current_playlist.get('name'):
            try:
                # 2. THAY THẾ HÀM GỌI: Gọi update_playlist_name
                update_playlist_name(playlist_id, new_name)
                messagebox.showinfo("Thành công", "Tên Playlist đã được cập nhật")
                self.refresh()
            except ValueError as ve:
                # Bắt lỗi ValueError (Lỗi ID hoặc trùng tên) từ service
                messagebox.showerror("Lỗi Cập nhật", str(ve))
            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể sửa tên Playlist: {e}")

    # --- CÁC HÀM KHÁC (GIỮ NGUYÊN) ---
    def refresh(self):
        """Tải lại danh sách Playlist và cập nhật UI (Treeview Playlist và Sidebar MainWindow)."""
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            self.playlists = get_playlists()

            for p in self.playlists:
                # Lưu ý: 'songs' không còn là list trong DB, mà là 'song_ids'.
                # Tuy nhiên, nếu service get_playlists trả về dict chứa 'songs' count, thì giữ nguyên.
                # Giả định: Service trả về {'songs': [...]} (thông tin cũ) hoặc songs_count được tính toán ở đâu đó.
                # Nếu không, cần sửa thành len(p.get('song_ids', []))
                songs_count = len(p.get('songs', []))
                self.tree.insert('', 'end', iid=str(p.get('_id')), values=(p.get('name'), songs_count))

        except Exception as e:
            messagebox.showerror("Lỗi Database", f"Không thể tải danh sách Playlist: {e}")
            self.playlists = []

        self.on_change()

    def delete(self):
        """Xóa Playlist đã chọn."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một Playlist để xóa.")
            return

        playlist_id = sel[0]
        current_playlist = next((p for p in self.playlists if str(p.get('_id')) == playlist_id), None)
        if not current_playlist: return

        confirm = messagebox.askyesno(
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa Playlist '{current_playlist.get('name')}'?"
        )

        if confirm:
            try:
                delete_playlist(playlist_id)
                messagebox.showinfo("Thành công", "Playlist đã được xóa")

                for i in self.song_tree.get_children():
                    self.song_tree.delete(i)
                self.songs_title_label.configure(text="BÀI HÁT TRONG PLAYLIST (Chọn một Playlist)")
                self.selected_playlist_id = None
                self.playlist_songs = []

                self.refresh()
            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể xóa Playlist: {e}")

    def on_playlist_select(self, event):
        """Tải danh sách bài hát của playlist được chọn."""
        sel = self.tree.selection()
        if not sel:
            self.songs_title_label.configure(text="BÀI HÁT TRONG PLAYLIST (Chọn một Playlist)")
            for i in self.song_tree.get_children():
                self.song_tree.delete(i)
            self.selected_playlist_id = None
            self.playlist_songs = []
            return

        playlist_id = sel[0]
        self.selected_playlist_id = playlist_id

        current_playlist = next((p for p in self.playlists if str(p.get('_id')) == playlist_id), None)
        playlist_name = current_playlist.get('name') if current_playlist else "Playlist không tồn tại"

        try:
            self.playlist_songs = get_songs_in_playlist(playlist_id)
        except Exception as e:
            messagebox.showerror("Lỗi tải", f"Không thể tải bài hát trong Playlist: {e}")
            self.playlist_songs = []

        for i in self.song_tree.get_children():
            self.song_tree.delete(i)

        self.songs_title_label.configure(text=f"PlayList: {playlist_name}")

        for song_info in self.playlist_songs:
            song_id = str(song_info.get("_id"))
            duration_formatted = self._fmt(song_info.get("duration", 0))

            self.song_tree.insert(
                "", "end", iid=f"{playlist_id}_{song_id}",
                values=(
                    song_info.get("title", "No Title"),
                    song_info.get("artist", "Unknown Artist"),
                    duration_formatted
                )
            )

    def play_selected_playlist_song(self, event):
        """Phát bài hát được chọn trong danh sách Playlist."""
        sel = self.song_tree.selection()
        if not sel:
            return

        selected_iid = sel[0]
        index = -1

        try:
            song_id_in_playlist = selected_iid.split('_')[-1]

            index = next((i for i, s in enumerate(self.playlist_songs)
                          if str(s.get("_id")) == song_id_in_playlist), -1)

        except Exception:
            index = -1

        if index != -1:
            self.master.load_and_play_playlist(self.playlist_songs, index)
            self.destroy()
        else:
            messagebox.showerror("Lỗi Phát", "Không tìm thấy bài hát trong danh sách Playlist.")

    def remove_song_from_playlist(self):
        """Xóa bài hát đã chọn khỏi Playlist hiện tại."""
        sel = self.song_tree.selection()
        if not sel:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bài hát để xóa khỏi Playlist.")
            return

        selected_iid = sel[0]
        playlist_id = self.selected_playlist_id

        if not playlist_id:
            messagebox.showwarning("Lỗi", "Vui lòng chọn một Playlist trước.")
            return

        song_id_to_remove = selected_iid.split('_')[-1]

        try:
            current_song = next((s for s in self.playlist_songs if str(s.get('_id')) == song_id_to_remove), None)
            song_title = current_song.get('title', 'Bài hát này') if current_song else 'Bài hát này'
        except:
            song_title = 'Bài hát này'

        confirm = messagebox.askyesno(
            "Xác nhận Xóa",
            f"Bạn có chắc chắn muốn xóa '{song_title}' khỏi Playlist này?"
        )

        if confirm:
            try:
                modified_count = remove_song_from_playlist(playlist_id, song_id_to_remove)

                if modified_count > 0:
                    messagebox.showinfo("Thành công", f"'{song_title}' đã được xóa khỏi Playlist.")
                    self.on_playlist_select(None)
                    self.refresh()
                else:
                    messagebox.showwarning("Cảnh báo",
                                           "Không tìm thấy bài hát trong Playlist hoặc thao tác không thành công.")
                    self.on_playlist_select(None)
                    self.refresh()

            except Exception as e:
                messagebox.showerror("Lỗi Database", f"Không thể xóa bài hát khỏi Playlist: {e}")