import sys
import os

# Force Python to add the current folder to its path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import SimphStudioWindow

if __name__ == "__main__":
    app = SimphStudioWindow()
    app.mainloop()