import customtkinter as ctk
from tkinter import ttk, messagebox
from services.playlist_service import add_songs_to_playlist
from services import song_service
import tkinter as tk


class AddSongsToPlaylistWindow(ctk.CTkToplevel):
    def __init__(self, master, playlist_id, playlist_name, on_success):
        super().__init__(master)
        self.title(f"Thêm nhạc vào: {playlist_name}")
        self.transient(master)
        self.geometry("650x450")

        self.playlist_id = playlist_id
        self.playlist_name = playlist_name
        self.on_success = on_success
        self.songs_data = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._apply_treeview_style()
        self.build()
        self.load_songs()

    def _apply_treeview_style(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("Treeview",
                    background="#121212",
                    foreground="white",
                    rowheight=25,
                    fieldbackground="#121212",
                    font=('Segoe UI', 10))
        s.map('Treeview',
              background=[('selected', '#2A2A2A')],
              foreground=[('selected', '#1DB954')])
        s.configure("Treeview.Heading",
                    background="#121212",
                    foreground="#B3B3B3",
                    font=('Segoe UI', 11, 'bold'))
        s.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

    def build(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame,
                     text="Chọn các bài hát để thêm:",
                     font=ctk.CTkFont(size=14, weight="bold")
                     ).grid(row=0, column=0, sticky="w", padx=5, pady=(0, 10))

        self.tree = ttk.Treeview(
            main_frame,
            columns=("title", "artist"),
            show="headings",
            selectmode="extended"
        )
        self.tree.heading("title", text="Tên Bài Hát")
        self.tree.column("title", width=300, anchor="w")
        self.tree.heading("artist", text="Nghệ Sĩ")
        self.tree.column("artist", width=250, anchor="w")

        self.tree.grid(row=1, column=0, sticky="nsew", columnspan=2, padx=5)

        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky='ns', padx=(0, 5))
        self.tree.configure(yscrollcommand=vsb.set)

        btn_fr = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_fr.grid(row=2, column=0, columnspan=2, pady=(15, 5))

        ctk.CTkButton(
            btn_fr,
            text="Thêm vào Playlist",
            command=self.confirm_add,
            fg_color="#1DB954",
            hover_color="#1ed760"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_fr,
            text="Hủy",
            command=self.destroy
        ).pack(side="left", padx=10)

    def load_songs(self):
        try:
            self.songs_data = song_service.get_songs()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tải danh sách bài hát: {e}")
            return

        for song in self.songs_data:
            song_id = str(song.get("_id"))
            self.tree.insert("", "end", iid=song_id, values=(
                song.get("title", "No Title"),
                song.get("artist", "Unknown Artist")
            ))

    def confirm_add(self):
        selected_ids = self.tree.selection()

        if not selected_ids:
            messagebox.showwarning("Chọn Bài Hát", "Vui lòng chọn ít nhất một bài hát để thêm.")
            return

        try:
            count = add_songs_to_playlist(self.playlist_id, list(selected_ids))

            messagebox.showinfo("Thành công",
                                f"Đã thêm thành công {count} bài hát vào Playlist '{self.playlist_name}'. (Lưu ý: Các bài đã có sẽ được bỏ qua)")

            if self.on_success:
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Lỗi Database", f"Không thể thêm bài hát vào playlist: {e}")