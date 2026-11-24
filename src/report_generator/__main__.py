"""`uv run report-generator`: start the local server and open the browser."""

import threading
import webbrowser

import uvicorn

from report_generator.settings import Settings
from report_generator.web.app import create_app


def main() -> None:
    settings = Settings()
    app = create_app(settings)
    url = f"http://{settings.host}:{settings.port}/"
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
