from PyQt6.QtWidgets import (QMainWindow, QToolBar, QLineEdit, QPushButton, 
                            QVBoxLayout, QWidget, QProgressBar, QMessageBox,
                            QTabWidget, QMenu, QStatusBar, QCompleter, QSystemTrayIcon, 
                            QDialog, QLabel)
from PyQt6.QtCore import QUrl, Qt, pyqtSlot, QTimer, QPoint, QDateTime
from PyQt6.QtGui import QIcon, QAction, QKeySequence
from .webview import WebView
from .cache import BrowserCache
import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omega Browser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize browser history and popular sites first
        self.history_file = 'browser_history.json'
        self.history = self.load_history()
        self.popular_sites = self.load_popular_sites()
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(2)
        self.progress_bar.setTextVisible(False)
        self.setup_loading_indicator()

        # Initialize thread pool executor
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Set up the central widget with tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)  # Allow tab reordering
        self.tabs.setDocumentMode(True)  # Clean modern look
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)  # Handle long titles
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        
        # Style the tabs
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #1a1a2e;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background: #1a1a2e;
            }
            QTabBar::tab {
                background: #242444;
                color: #ffffff;
                min-width: 150px;
                max-width: 200px;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #4a90e2;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover:!selected {
                background: #353555;
            }
            QTabBar::close-button {
                image: url(close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
        """)
        
        self.setCentralWidget(self.tabs)

        # Create main toolbar
        self.setup_toolbar()
        
        # Create status bar and add progress bar to it
        self.status_bar = QStatusBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.setStatusBar(self.status_bar)
        
        # Add initial tab
        self.add_new_tab()
        
        # Setup shortcuts
        self.setup_shortcuts()

        # Initialize cache
        self.cache = BrowserCache()
        self.setup_status_messages()
        
        # Add loading timer
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.loading_frame_index = 0

        # Add URL suggestions
        self.setup_url_completer()
        
        # Add system tray icon
        self.setup_tray_icon()
        
        # Add welcome dialog
        self.show_welcome_dialog()

    def setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setStyleSheet("""
            QToolBar { 
                background: #1a1a2e; 
                border: none; 
                padding: 8px;
            }
            QPushButton { 
                background: rgba(255,255,255,0.1);
                border: none; 
                padding: 8px 15px; 
                border-radius: 4px;
                margin: 0 2px;
                font-size: 14px;
                color: #fff;
            }
            QPushButton:hover { 
                background: rgba(255,255,255,0.2);
            }
            QLineEdit { 
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 20px; 
                padding: 8px 15px; 
                margin: 0 10px;
                font-size: 14px;
                color: #fff;
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.15);
                border: 1px solid rgba(255,255,255,0.3);
            }
        """)
        self.addToolBar(toolbar)

        # Add navigation buttons
        self.add_toolbar_button(toolbar, "◀", "Back", self.go_back)
        self.add_toolbar_button(toolbar, "▶", "Forward", self.go_forward)
        self.add_toolbar_button(toolbar, "↻", "Refresh", self.refresh_page)
        self.add_toolbar_button(toolbar, "🏠", "Home", self.load_homepage)
        
        # Add URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.url_bar)
        
        # Add feature buttons
        self.add_toolbar_button(toolbar, "⭐", "Bookmarks", self.show_bookmarks)
        self.add_toolbar_button(toolbar, "⚡", "Downloads", self.show_downloads)
        self.add_toolbar_button(toolbar, "⚙️", "Settings", self.show_settings)
        self.add_toolbar_button(toolbar, "+", "New Tab", self.add_new_tab)

    def add_toolbar_button(self, toolbar, text, tooltip, callback):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        toolbar.addWidget(btn)
        return btn

    def setup_shortcuts(self):
        # Fix shortcuts with proper Qt key sequences
        shortcuts = [
            ("Ctrl+T", self.add_new_tab),
            ("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex())),
            ("Ctrl+F", self.show_find_dialog),
            ("Ctrl+S", self.save_page),
            ("Ctrl+H", self.show_history),
            ("Ctrl+Shift+P", self.new_private_tab)
        ]
        
        for key, callback in shortcuts:
            shortcut = QAction(self)
            shortcut.setShortcut(key)
            shortcut.triggered.connect(callback)
            self.addAction(shortcut)

    @pyqtSlot(int)
    def tab_changed(self, index):
        if index != -1:
            webview = self.tabs.currentWidget()
            self.url_bar.setText(webview.url().toString())
            self.update_window_title(webview.page().title())

    def update_tab_status(self, index, status):
        """Update tab appearance based on status"""
        if 0 <= index < self.tabs.count():  # Check valid index
            if status == "loading":
                self.tabs.setTabText(index, "Loading...")
                self.tabs.setTabIcon(index, QIcon("🔄"))
                self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.gray)
            else:
                title = self.tabs.widget(index).page().title() or "New Tab"
                self.tabs.setTabText(index, title)
                self.tabs.setTabIcon(index, QIcon("🌐"))
                self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.white)

    def add_new_tab(self, url=None):
        """Create a new tab with improved visuals"""
        webview = WebView()
        webview.urlChanged.connect(lambda u: self.update_url(u))
        webview.loadFinished.connect(lambda: self.update_window_title(webview.page().title()))
        
        # Add tab first to get correct index
        index = self.tabs.addTab(webview, "New Tab")
        
        # Connect loading signals with correct tab index
        webview.loadStarted.connect(lambda: self.update_tab_status(index, "loading"))
        webview.loadFinished.connect(lambda: self.update_tab_status(index, "done"))
        
        self.tabs.setCurrentIndex(index)
        
        # Add initial tab icon
        self.tabs.setTabIcon(index, QIcon("🌐"))
        
        if url:
            webview.load_url(url)
        else:
            self.load_homepage_in_view(webview)

    def load_homepage_in_view(self, webview):
        """Load homepage in the specified webview"""
        homepage_html = self.get_homepage_html()
        webview.setHtml(homepage_html)

    def update_url(self, url):
        # If the URL is a data URI (our local homepage), clear the address bar.
        if url.scheme() == 'data':
            self.url_bar.clear()
            return
        
        if self.tabs.currentWidget() == self.sender():
            self.url_bar.setText(url.toString())
            self.add_to_history(url.toString())

    def update_window_title(self, title):
        if title:
            self.tabs.setTabText(self.tabs.currentIndex(), title)

    def add_to_history(self, url):
        from datetime import datetime
        self.history.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'title': self.tabs.currentWidget().page().title()
        })
        self.save_history()

    def load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
        return []

    def save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history[-1000:], f)  # Keep last 1000 entries
        except Exception as e:
            print(f"Error saving history: {e}")

    def close_tab(self, index):
        """Improved tab closing with animation"""
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.close()
            self.tabs.removeTab(index)
        else:
            # Don't close the last tab, just clear it
            self.tabs.widget(index).setUrl(QUrl("about:blank"))
            self.tabs.setTabText(index, "New Tab")
            self.tabs.setTabIcon(index, QIcon("🌐"))
            self.add_new_tab()

    def show_bookmarks(self):
        """Show bookmarks dialog"""
        try:
            with open('bookmarks.txt', 'r') as f:
                bookmarks = f.readlines()
            
            if not bookmarks:
                QMessageBox.information(self, "Bookmarks", "No bookmarks yet!")
                return

            menu = QMenu(self)
            for bookmark in bookmarks:
                try:
                    title, url = bookmark.strip().split(" | ")
                    action = menu.addAction(title)
                    action.triggered.connect(lambda _, url=url: self.load_url(url))
                except ValueError:
                    continue

            menu.exec(self.bookmark_btn.mapToGlobal(self.bookmark_btn.rect().bottomLeft()))
        except FileNotFoundError:
            QMessageBox.information(self, "Bookmarks", "No bookmarks yet!")

    def load_url(self, url):
        """Load URL in current tab"""
        self.tabs.currentWidget().load_url(url)

    def show_find_dialog(self):
        """Show find in page dialog"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, 'Find in Page', 'Enter text to find:')
        if ok and text:
            self.tabs.currentWidget().findText(text)

    def show_downloads(self):
        """Show downloads manager"""
        QMessageBox.information(self, "Downloads", "Downloads feature coming soon!")

    def show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(self, "Settings", "Settings feature coming soon!")

    def save_page(self):
        """Save current page"""
        from PyQt6.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Page",
            "",
            "HTML Files (*.html);;All Files (*.*)"
        )
        if file_name:
            self.tabs.currentWidget().page().save(file_name, QWebEnginePage.SavePageFormat.CompleteHtmlSaveFormat)

    def show_history(self):
        """Show browsing history"""
        if not self.history:
            QMessageBox.information(self, "History", "No browsing history yet!")
            return

        menu = QMenu(self)
        for entry in reversed(self.history[-20:]):  # Show last 20 entries
            action = menu.addAction(entry.get('title', entry['url']))
            action.triggered.connect(lambda _, url=entry['url']: self.load_url(url))

        menu.exec(self.sender().mapToGlobal(self.sender().rect().bottomLeft()))

    def new_private_tab(self):
        """Open new private browsing tab with distinct styling"""
        webview = WebView()
        webview.page().profile().setOffTheRecord(True)
        webview.urlChanged.connect(lambda u: self.update_url(u))
        webview.loadFinished.connect(lambda: self.update_window_title(webview.page().title()))
        
        index = self.tabs.addTab(webview, "Private Tab")
        self.tabs.setCurrentIndex(index)
        
        # Add private browsing indicator and styling
        self.tabs.setTabIcon(index, QIcon("🕵️"))
        self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.gray)
        self.tabs.setTabToolTip(index, "Private Browsing Mode")
        
        self.load_homepage_in_view(webview)

    def load_homepage(self):
        """Load the homepage in the current tab"""
        current_webview = self.tabs.currentWidget()
        if (current_webview):
            self.load_homepage_in_view(current_webview)

    def get_homepage_html(self):
        """Get enhanced homepage HTML content"""
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Omega Browser</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: #ffffff;
                }}
                .search-container {{
                    text-align: center;
                    padding: 50px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 24px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    width: 90%;
                    max-width: 1000px;
                }}
                .omega-logo {{
                    font-size: 72px;
                    font-weight: bold;
                    color: #4a90e2;
                    margin-bottom: 20px;
                    text-shadow: 0 0 20px rgba(74, 144, 226, 0.3);
                }}
                h1 {{
                    font-size: 32px;
                    font-weight: 300;
                    margin-bottom: 40px;
                    color: #ffffff;
                }}
                .quick-access {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 24px;
                    margin-top: 50px;
                    padding: 0 20px;
                }}
                .quick-link {{
                    background: rgba(255, 255, 255, 0.08);
                    padding: 20px;
                    border-radius: 16px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    color: white;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100px;
                }}
                .quick-link:hover {{
                    background: rgba(255, 255, 255, 0.12);
                    transform: translateY(-4px);
                    box-shadow: 0 6px 20px rgba(0,0,0,0.2);
                }}
                .site-icon {{
                    font-size: 32px;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 60px;
                    height: 60px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 50%;
                }}
                .site-title {{
                    font-size: 14px;
                    font-weight: 500;
                    opacity: 0.9;
                    margin-top: 8px;
                }}
            </style>
        </head>
        <body>
            <div class="search-container">
                <div class="omega-logo">Ω</div>
                <h1>Omega Search</h1>
                <div class="search-wrapper">
                    <!-- ...existing search box... -->
                </div>
                <div class="quick-access">
                    {self.generate_quick_links()}
                </div>
            </div>
        </body>
        </html>
        '''

    def generate_quick_links(self):
        """Generate HTML for quick access links"""
        links = []
        try:
            for site in (self.popular_sites or []):
                links.append(f'''
                    <a href="{site['url']}" class="quick-link">
                        <div class="site-icon">{site['icon']}</div>
                        <div class="site-title">{site['title']}</div>
                    </a>
                ''')
        except Exception as e:
            print(f"Error generating quick links: {e}")
        return ''.join(links)

    def load_started(self):
        """Handle page load start with animation"""
        self.progress_bar.show()
        if webview := self.get_current_webview():
            self.refresh_btn.setText("✕")
        self.loading_timer.start(100)
        self.show_status_message("Loading page...")

    def load_progress(self, progress):
        """Handle page load progress"""
        if webview := self.get_current_webview():
            self.progress_bar.setValue(progress)

    def load_finished(self, success):
        """Handle page load completion with status"""
        self.progress_bar.hide()
        self.refresh_btn.setText("↻")
        if not success:
            QMessageBox.warning(self, "Error", "Failed to load the page.")
        self.loading_timer.stop()
        if success:
            self.show_status_message("Page loaded successfully")
        else:
            self.show_status_message("Failed to load page", 5000)

    def url_changed(self, url):
        """Handle URL changes"""
        if webview := self.get_current_webview():
            self.url_bar.setText(url.toString())

    def get_current_webview(self):
        """Get the webview of the current tab"""
        return self.tabs.currentWidget()

    def is_valid_url(self, text):
        # Check 1: Does it start with a common scheme?
        if text.startswith(('http://', 'https://')):
            return True
        
        # Check 2: If not, does it look like a domain? (e.g., 'google.com')
        if ' ' not in text and '.' in text:
            return True
        
        # If neither check passes, it's not a URL for our purposes.
        return False
    
    def navigate_to_url(self):
        """Enhanced URL navigation with parallel loading"""
        query = self.url_bar.text().strip()
        if not query:
            return
        
        # Check if it's a valid URL
        if not self.is_valid_url(query):
            # If it's not a valid URL, treat it as a search query.
            # We transform the query into a Google search URL.
            query = f"https://www.google.com/search?q={query}"

        # Check cache first
        if cached_data := self.cache.get(query):
            self.show_status_message("Loading from cache...")
            self.load_cached_data(cached_data)
            return

        # Show loading animation in URL bar
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background: rgba(74, 144, 226, 0.1);
                border-color: #4a90e2;
            }
        """)

        if webview := self.get_current_webview():
            # Preload DNS and assets in parallel
            self.executor.submit(self.preload_resources, query)
            
            # Load the URL
            webview.load_url(query)
            # Reset URL bar style after loading
            QTimer.singleShot(100, lambda: self.url_bar.setStyleSheet(""))
            self.cache.set(query, {
                'url': query,
                'timestamp': time.time(),
                'accessed': datetime.now().isoformat()
            })

    def preload_resources(self, url):
        """Preload DNS and critical resources"""
        try:
            import socket
            from urllib.parse import urlparse
            
            # Preload DNS
            domain = urlparse(url).netloc
            socket.gethostbyname(domain)
            
            # Prefetch common resources
            common_resources = [
                '/favicon.ico',
                '/styles.css',
                '/main.js'
            ]
            
            for resource in common_resources:
                self.executor.submit(
                    requests.head, 
                    f"https://{domain}{resource}", 
                    timeout=2
                )
        except Exception:
            pass

    def load_cached_data(self, cached_data):
        """Load data from cache"""
        if webview := self.get_current_webview():
            url = cached_data.get('url')
            if url:
                webview.load_url(url)
                self.show_status_message(f"Loading {url} from cache")
            else:
                self.show_status_message("Invalid cached data")

    def go_back(self):
        """Go back in current tab"""
        if webview := self.get_current_webview():
            webview.back()

    def go_forward(self):
        """Go forward in current tab"""
        if webview := self.get_current_webview():
            webview.forward()

    def refresh_page(self):
        """Refresh current tab"""
        if webview := self.get_current_webview():
            webview.refresh()

    def add_bookmark(self):
        """Add current page to bookmarks"""
        if webview := self.get_current_webview():
            current_url = webview.url().toString()
            title = webview.page().title()
            try:
                with open('bookmarks.txt', 'a') as f:
                    f.write(f"{title} | {current_url}\n")
                QMessageBox.information(self, "Success", "Bookmark added successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not add bookmark: {str(e)}")

    def setup_status_messages(self):
        """Setup status bar messages"""
        self.status_message_timer = QTimer()
        self.status_message_timer.setSingleShot(True)
        self.status_message_timer.timeout.connect(self.clear_status_message)

    def show_status_message(self, message, timeout=3000):
        """Show temporary status message"""
        self.status_bar.showMessage(message)
        self.status_message_timer.start(timeout)

    def clear_status_message(self):
        """Clear status bar message"""
        self.status_bar.clearMessage()

    def update_loading_animation(self):
        """Update loading animation frame"""
        if self.loading_frame_index >= len(self.loading_frames):
            self.loading_frame_index = 0
        frame = self.loading_frames[self.loading_frame_index]
        self.status_bar.showMessage(f"Loading {frame}")
        self.loading_frame_index += 1

    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        if event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+L: Focus URL bar
            self.url_bar.selectAll()
            self.url_bar.setFocus()
        elif event.key() == Qt.Key.Key_R and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+R: Refresh
            self.refresh_page()
        elif event.key() == Qt.Key.Key_F5:
            # F5: Refresh
            self.refresh_page()
        elif event.key() == Qt.Key.Key_Escape:
            # Escape: Stop loading
            if webview := self.get_current_webview():
                webview.stop()
        super().keyPressEvent(event)

    def setup_url_completer(self):
        """Setup URL auto-completion"""
        self.completer = QCompleter(self.load_frequent_urls())
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.url_bar.setCompleter(self.completer)

    def load_frequent_urls(self):
        """Load frequently visited URLs for suggestions"""
        try:
            if self.history:
                # Get unique URLs from history, sorted by frequency
                urls = {}
                for entry in self.history:
                    url = entry['url']
                    urls[url] = urls.get(url, 0) + 1
                return sorted(urls.keys(), key=lambda x: urls[x], reverse=True)[:100]
        except Exception:
            pass
        return []

    def setup_tray_icon(self):
        """Setup system tray icon with menu"""
        # Create custom icon
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
        icon_size = 32
        pixmap = QPixmap(icon_size, icon_size)
        pixmap.fill(QColor("#1a1a2e"))
        
        painter = QPainter(pixmap)
        painter.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        painter.setPen(QColor("#4a90e2"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Ω")
        painter.end()
        
        # Set up tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Create tray menu
        tray_menu = QMenu()
        tray_menu.addAction("Show Browser", self.show)
        tray_menu.addAction("New Private Tab", self.new_private_tab)
        tray_menu.addSeparator()
        tray_menu.addAction("Quit", self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_welcome_dialog(self):
        """Show welcome dialog for first-time users"""
        if not os.path.exists('.welcomed'):
            dialog = QDialog(self)
            dialog.setWindowTitle("Welcome to Omega Browser")
            
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Welcome to Omega Browser!"))
            layout.addWidget(QLabel("Quick Tips:"))
            layout.addWidget(QLabel("• Ctrl+T: New Tab"))
            layout.addWidget(QLabel("• Ctrl+L: Focus Address Bar"))
            layout.addWidget(QLabel("• Ctrl+F: Find in Page"))
            
            dont_show = QPushButton("Don't show again")
            dont_show.clicked.connect(lambda: self.mark_welcomed(dialog))
            layout.addWidget(dont_show)
            
            dialog.setLayout(layout)
            dialog.show()

    def mark_welcomed(self, dialog):
        """Mark user as welcomed"""
        with open('.welcomed', 'w') as f:
            f.write('1')
        dialog.close()

    def setup_loading_indicator(self):
        """Add visual loading indicator"""
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: transparent;
                height: 2px;
            }
            QProgressBar::chunk {
                background: #4a90e2;
            }
        """)

    def closeEvent(self, event):
        """Handle application close"""
        self.tray_icon.showMessage(
            "Omega Browser",
            "Browser minimized to tray. Right-click the tray icon to quit.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        self.hide()
        event.ignore()

    def load_popular_sites(self):
        """Load frequently visited and popular sites"""
        sites = [
            {"title": "Google", "url": "https://www.google.com", "icon": "🔍"},
            {"title": "YouTube", "url": "https://www.youtube.com", "icon": "▶️"},
            {"title": "GitHub", "url": "https://github.com", "icon": "📦"},
            {"title": "Wikipedia", "url": "https://wikipedia.org", "icon": "📚"},
            {"title": "Reddit", "url": "https://reddit.com", "icon": "🌐"},
            {"title": "News", "url": "https://news.google.com", "icon": "📰"},
            {"title": "Mail", "url": "https://gmail.com", "icon": "📧"},
            {"title": "Maps", "url": "https://maps.google.com", "icon": "🗺️"},
        ]
        
        try:
            # Add user's most visited sites
            if self.history:
                visited = {}
                for entry in self.history:
                    url = entry['url']
                    title = entry.get('title', url)
                    visited[url] = visited.get(url, 0) + 1
                
                # Add top 4 most visited sites
                most_visited = sorted(visited.items(), key=lambda x: x[1], reverse=True)[:4]
                for url, count in most_visited:
                    sites.append({
                        "title": "Frequently Visited",
                        "url": url,
                        "icon": "⭐"
                    })
        except Exception as e:
            print(f"Error loading popular sites: {e}")
        
        return sites

# End of class BrowserWindow