"""Development entry point for the Flask backend."""

import os
from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")

    print(f"Starting Flask server on http://{host}:{port} (debug={debug})...")
    app.run(host=host, port=port, debug=debug)
