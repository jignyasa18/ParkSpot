import webbrowser
import os
import sys

def main():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "parkspot-react.html"))
    print(f"Launching ParkSpot Frontend at: {file_path}")
    webbrowser.open(f"file:///{file_path}")
    print("Application opened in your default browser!")

if __name__ == "__main__":
    main()
