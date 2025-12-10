import customtkinter as ctk
import tkinter as tk  # Vẫn cần cho Treeview
from tkinter import ttk, messagebox, simpledialog  # Cần cho Treeview style và dialog
from services.playlist_service import create_playlist, get_playlists, update_playlist, delete_playlist


# Dùng ctk.CTkToplevel
class PlaylistWindow(ctk.CTkToplevel):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.title("Quản Lý Playlists")
        self.transient(master)
        self.geometry("400x350")

        self.on_change = on_change
        self.build()
        self.refresh()

        # Áp dụng lại style ttk nếu cần
        self._apply_treeview_style()

    def _apply_treeview_style(self):
        # Đây là đoạn code style Treeview đã dùng trong main_window
        s = ttk.Style()
        s.theme_use("default")
        s.configure("Treeview",
                    background="#121212",
                    foreground="white",
                    rowheight=30,
                    fieldbackground="#121212",
                    font=('Segoe UI', 11))
        s.map('Treeview',
              background=[('selected', '#2A2A2A')],
              foreground=[('selected', '#1DB954')])
        s.configure("Treeview.Heading",
                    background="#121212",
                    foreground="#B3B3B3",
                    font=('Segoe UI', 12, 'bold'))
        s.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

    def build(self):
        # Dùng ctk.CTkFrame thay cho ttk.Frame
        frm = ctk.CTkFrame(self)  # Bỏ padding=12
        # Thêm padx, pady vào grid của frm
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frm.grid_rowconfigure(0, weight=1)
        frm.grid_columnconfigure(0, weight=1)

        # Vẫn dùng ttk.Treeview vì ctk chưa có widget thay thế
        self.tree = ttk.Treeview(frm, columns=("name",), show="headings", height=8)
        self.tree.heading("name", text="Tên Playlist")
        self.tree.column("name", width=350, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=3, sticky="nsew")

        # Khung nút
        btn_fr = ctk.CTkFrame(frm, fg_color="transparent")
        btn_fr.grid(row=1, column=0, columnspan=3, pady=10)

        # Dùng ctk.CTkButton
        ctk.CTkButton(btn_fr, text="Thêm", command=self.add, fg_color="#1DB954", hover_color="#1ed760").pack(
            side="left", padx=5)
        ctk.CTkButton(btn_fr, text="Sửa", command=self.edit).pack(side="left", padx=5)
        ctk.CTkButton(btn_fr, text="Xóa", command=self.delete, fg_color="red", hover_color="#cc0000").pack(side="left",
                                                                                                           padx=5)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in get_playlists():
            # Sử dụng str(p.get('_id')) làm iid
            self.tree.insert('', 'end', iid=str(p.get('_id')), values=(p.get('name'),))

    def add(self):
        # Sử dụng ctk.CTkInputDialog
        dialog = ctk.CTkInputDialog(text="Nhập tên Playlist:", title="Tạo Playlist Mới")
        name = dialog.get_input()

        if name:
            create_playlist(name)
            messagebox.showinfo("Thành công", "Playlist đã được tạo")
            self.refresh()
            self.on_change()

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Chọn Playlist", "Vui lòng chọn một Playlist để sửa")
            return
        pid = sel[0]
        p_name = self.tree.item(pid, 'values')[0]

        # Sử dụng ctk.CTkInputDialog
        dialog = ctk.CTkInputDialog(text="Tên Playlist mới:", title="Sửa Playlist", initial_value=p_name)
        name = dialog.get_input()

        if name:
            update_playlist(pid, {"name": name})
            messagebox.showinfo("Thành công", "Playlist đã được cập nhật")
            self.refresh()
            self.on_change()

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Chọn Playlist", "Vui lòng chọn một Playlist")
            return
        pid = sel[0]
        p_name = self.tree.item(pid, 'values')[0]

        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa Playlist '{p_name}'?"):
            delete_playlist(pid)
            messagebox.showinfo("Thành công", "Playlist đã được xóa")
            self.refresh()
            self.on_change()