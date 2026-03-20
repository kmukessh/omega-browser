import sys
import threading
from PyQt6.QtWidgets import QApplication
from browser.window import BrowserWindow
from search_engine.app import app

def run_flask():
    app.run(port=5000)

def main():
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Initialize Qt Application
    qt_app = QApplication(sys.argv)
    
    # Initialize the browser window
    browser = BrowserWindow()
    browser.show()
    
    # Start the main event loop
    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()