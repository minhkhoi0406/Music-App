import sys
from gui.main_window import MainWindow
from pathlib import Path

# Ensure music and cover dirs exist
BASE = Path(__file__).parent
(BASE / "music").mkdir(parents=True, exist_ok=True)
(BASE / "assets" / "covers").mkdir(parents=True, exist_ok=True)


def main():
    app = MainWindow()
    app.mainloop()

if __name__ == '__main__':
    main()
