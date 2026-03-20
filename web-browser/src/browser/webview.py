from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSignal, QTimer, Qt
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineProfile
from functools import lru_cache
from PyQt6.QtWidgets import QMenu, QDialog, QVBoxLayout, QLabel
import time

class CustomWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        # Suppress console messages in release mode
        pass

class WebView(QWebEngineView):
    loadingChanged = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setPage(CustomWebPage(self))
        
        # Enable developer tools with F12
        self.page().settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True
        )
        
        # Add loading timeout
        self.loading_timeout = 30000  # 30 seconds
        self.loading_timer = QTimer()
        self.loading_timer.setSingleShot(True)
        self.loading_timer.timeout.connect(self.handle_loading_timeout)
        
        # Add zoom support
        self.zoom_factor = 1.0
        self.page().wheel_event = self.handle_wheel_zoom
        
        # Enable performance optimizations
        settings = self.page().settings()
        
        # Essential settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        
        # Security settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        
        # Set default encoding
        settings.setDefaultTextEncoding('utf-8')
        
        # Set caching preferences
        profile = QWebEngineProfile.defaultProfile()
        profile.setCachePath(".cache")
        profile.setPersistentStoragePath(".storage")
        profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100MB cache
        
        # Enable hardware acceleration
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)

    @lru_cache(maxsize=100)
    def is_valid_url(self, url):
        """Efficiently validate URLs"""
        return any([
            url.startswith(('http://', 'https://')),
            url.endswith(('.com', '.org', '.net', '.edu', '.gov')),
            '.' in url and not ' ' in url
        ])

    def load_url(self, url):
        """Enhanced URL loading with timeout"""
        if not url.strip():
            return
            
        # Start loading timeout
        self.loading_timer.start(self.loading_timeout)
        
        # Handle URL loading
        if self.is_valid_url(url):
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
        else:
            url = f'http://localhost:5000/search?q={url}'
                
        self.setUrl(QUrl(url))
        self.loadingChanged.emit(True)

    def handle_loading_timeout(self):
        """Handle page load timeout"""
        self.stop()
        self.loadingChanged.emit(False)
        print(f"Loading timeout for: {self.url().toString()}")

    def contextMenuEvent(self, event):
        """Enhanced context menu"""
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        
        # Add zoom actions
        zoom_menu = menu.addMenu("Zoom")
        zoom_menu.addAction("Zoom In", self.zoom_in)
        zoom_menu.addAction("Zoom Out", self.zoom_out)
        zoom_menu.addAction("Reset Zoom", lambda: self.setZoomFactor(1.0))
        
        # Add page actions
        menu.addAction("View Page Source", 
            lambda: self.page().toHtml(self.show_source))
        menu.addAction("Take Screenshot", self.take_screenshot)
        
        menu.exec(event.globalPos())

    def show_source(self, html):
        """Show page source in new window"""
        from PyQt6.QtWidgets import QTextEdit, QDialog
        dialog = QDialog()
        dialog.setWindowTitle("Page Source")
        dialog.resize(800, 600)
        
        text_edit = QTextEdit(dialog)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(html)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(text_edit)
        dialog.exec()

    def refresh(self):
        self.reload()

    def handle_wheel_zoom(self, event):
        """Handle Ctrl+Wheel zoom"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        """Zoom in webpage"""
        self.zoom_factor = min(self.zoom_factor + 0.1, 5.0)
        self.setZoomFactor(self.zoom_factor)

    def zoom_out(self):
        """Zoom out webpage"""
        self.zoom_factor = max(self.zoom_factor - 0.1, 0.25)
        self.setZoomFactor(self.zoom_factor)

    def take_screenshot(self):
        """Take webpage screenshot"""
        from PyQt6.QtGui import QPixmap
        screen = self.grab()
        filename = f"screenshot_{int(time.time())}.png"
        screen.save(filename)
        self.parent().show_status_message(f"Screenshot saved as {filename}")