import customtkinter as ctk
from tkinter import ttk, messagebox
from services.playlist_service import get_playlists, add_songs_to_playlist

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

COLOR_BACKGROUND = "#121212"
COLOR_SIDEBAR = "#000000"
COLOR_PLAYER_BAR = "#181818"
COLOR_ACCENT = "#1DB954"

class SelectPlaylistDialog(ctk.CTkToplevel):
    """
    Cửa sổ Dialog cho phép người dùng chọn một Playlist để thêm các bài hát đã chọn.
    """

    def __init__(self, master, song_ids_to_add, on_success_callback=None):
        super().__init__(master)
        self.title("Chọn Playlist Đích")
        self.transient(master)
        self.geometry("350x300")
        self.resizable(False, False)

        self.song_ids_to_add = song_ids_to_add
        self.on_success_callback = on_success_callback

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._apply_treeview_style()
        self.build()
        self.load_playlists()

        self.configure(fg_color=COLOR_BACKGROUND)

    def _apply_treeview_style(self):
        s = ttk.Style()
        s.theme_use("default")

        # ===== STYLE RIÊNG CHO SELECT PLAYLIST DIALOG =====
        s.configure(
            "SelectPlaylist.Treeview",
            background="#121212",
            foreground="white",
            rowheight=45,
            fieldbackground="#121212",
            font=('Segoe UI', 10)
        )

        s.map(
            "SelectPlaylist.Treeview",
            background=[('selected', '#2A2A2A')],
            foreground=[('selected', '#1DB954')]
        )

        s.configure(
            "SelectPlaylist.Treeview.Heading",
            background="#121212",
            foreground="#B3B3B3",
            font=('Segoe UI', 11, 'bold')
        )

    def build(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame,
                     text="Chọn Playlist để thêm bài hát:",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, sticky="w", padx=5, pady=(0, 10))

        self.tree = ttk.Treeview(
            main_frame,
            columns=("name",),
            show="headings",
            selectmode="browse"
        )
        self.tree.heading("name", text="Tên Playlist")
        self.tree.column("name", width=250, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=5)
        self.tree.bind("<Double-1>", self._confirm_selection)

        btn_fr = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_fr.grid(row=2, column=0, pady=(15, 5))

        ctk.CTkButton(
            btn_fr,
            text="Thêm vào Playlist Đã Chọn",
            command=self._confirm_selection,
            fg_color="#1DB954",
            hover_color="#1ed760"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_fr,
            text="Hủy",
            command=self.destroy
        ).pack(side="left", padx=10)

    def load_playlists(self):
        """Tải danh sách playlists từ service và hiển thị lên treeview."""
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            for p in get_playlists():
                songs_count = len(p.get('songs', []))
                self.tree.insert('', 'end',
                                 iid=str(p.get('_id')),
                                 values=(p.get('name'), songs_count))

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải danh sách Playlist: {e}")

    def _confirm_selection(self, event=None):
        """Xác nhận Playlist được chọn và tiến hành thêm bài hát."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Chọn Playlist", "Vui lòng chọn một Playlist.")
            return

        if not self.song_ids_to_add:
            messagebox.showwarning("Bài hát", "Không có bài hát nào được chọn để thêm.")
            return

        playlist_id = sel[0]
        playlist_name = self.tree.item(playlist_id, 'values')[0]

        try:
            count = add_songs_to_playlist(playlist_id, self.song_ids_to_add)

            messagebox.showinfo(
                "Thành công",
                f"Đã thêm thành công {count} bài hát vào Playlist '{playlist_name}'."
            )

            if self.on_success_callback:
                self.on_success_callback()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi thêm nhạc: {e}")