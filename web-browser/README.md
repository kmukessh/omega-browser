# README.md

# Web Browser Project

This project is a simple web browser built using Python. It provides basic functionalities such as opening, closing, and resizing browser windows, as well as loading and refreshing web pages.

## Project Structure

```
web-browser
├── src
│   ├── main.py          # Entry point of the application
│   ├── browser          # Contains browser-related functionalities
│   │   ├── __init__.py  # Marks the browser directory as a package
│   │   ├── window.py     # Manages the main window of the web browser
│   │   └── webview.py    # Handles the rendering of web pages
│   └── utils            # Contains utility functions
│       └── __init__.py  # Marks the utils directory as a package
├── requirements.txt     # Lists the project dependencies
└── README.md            # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```
   cd web-browser
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the web browser, execute the following command:
```
python src/main.py
```

This will initialize the browser and start the main event loop. You can then use the browser to navigate to different web pages.