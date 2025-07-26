# src/__main__.py

from ..app import app

if __name__ == "__main__":
    # Note: debug=True is for development. Turn it off for production.
    app.run(host='0.0.0.0', port=5000, debug=True)