# app.py
import sys
import customtkinter as ctk # Cần import CTK để set appearance mode
from gui.main_window import MainWindow
from pathlib import Path

BASE = Path(__file__).parent
# ... (Code tạo thư mục) ...

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == '__main__':
    main()