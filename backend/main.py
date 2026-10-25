import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.system import SystemController

if __name__ == "__main__":
    app = SystemController()
    app.run()
