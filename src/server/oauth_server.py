import signal  # For basic shutdown
import threading
import webbrowser
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import urlparse  # To check scheme

from flask import Flask, jsonify, request  # Added jsonify
from loguru import logger
from werkzeug.serving import make_server  # For potentially better shutdown control

# Define a type hint for the callback function
OAuthCallbackHandler = Callable[[str, str], Optional[str]]  # Accepts state, code; returns Optional[user_id]


class OAuthServer:
    """
    Simple web server to handle the OAuth 2.0 redirect callback.

    Captures the authorization code and state from Google's redirect
    and passes them to a registered handler function.
    """

    def __init__(self, host: str, port: int, callback_handler: OAuthCallbackHandler) -> None:
        """
        Initializes the OAuth server.

        Args:
            host: Hostname or IP address to bind to.
            port: Port number to listen on.
            callback_handler: Function to call when the /oauth2callback is hit.
                              It receives (state, code) and should return the user_id
                              if successful, or None/raise Exception on failure.
        """
        self.host = host
        self.port = port
        self.callback_handler = callback_handler
        self.app = Flask(__name__)
        self.server: Optional[make_server] = None
        self.server_thread: Optional[threading.Thread] = None

        # Check if redirect URI uses HTTPS if not localhost
        redirect_uri = self.get_redirect_uri()
        parsed_uri = urlparse(redirect_uri)
        if parsed_uri.scheme != "https" and parsed_uri.hostname not in ("localhost", "127.0.0.1"):
            logger.warning(f"OAuth Redirect URI ({redirect_uri}) is not using HTTPS. This is insecure for production environments.")

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configures the Flask server routes."""

        @self.app.route("/oauth2callback")
        def oauth2callback():
            state = request.args.get("state")
            code = request.args.get("code")
            error = request.args.get("error")
            error_description = request.args.get("error_description")

            if error:
                error_msg = f"OAuth Error: {error}. Description: {error_description or 'N/A'}"
                logger.error(error_msg)
                # Potentially notify the user via the bot if state is known? Complex.
                return self._generate_error_page(error_msg)

            if not code or not state:
                error_msg = "Missing 'code' or 'state' parameter in OAuth callback."
                logger.error(error_msg)
                return self._generate_error_page(error_msg)

            try:
                # Call the provided handler function directly
                user_id = self.callback_handler(state, code)
                if user_id:
                    logger.info(f"OAuth callback processed successfully for state: {state} (User ID inferred)")
                    # User ID might not be directly available here, depends on handler impl.
                    return self._generate_success_page()
                else:
                    # Handler indicated failure without raising an exception (e.g., invalid state)
                    logger.error(f"OAuth callback handler failed for state: {state}")
                    return self._generate_error_page("Authentication failed. Invalid state or code.")

            except ValueError as ve:  # Specific error for invalid state from OAuthManager
                logger.error(f"OAuth state validation failed: {ve}")
                return self._generate_error_page(f"Authentication failed: {ve}")
            except Exception as e:
                logger.exception(f"Error processing OAuth callback for state {state}: {e}")  # Log traceback
                return self._generate_error_page(f"An internal error occurred during authentication: {e}")

        @self.app.route("/health")
        def health():
            return jsonify({"status": "ok"})

        # Basic shutdown route (for controlled environments)
        @self.app.route("/shutdown", methods=["POST"])
        def shutdown():
            logger.info("Shutdown request received.")
            self.stop()
            return jsonify({"message": "Server shutting down..."})

    def start(self) -> None:
        """Starts the server in a separate thread."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("OAuth server is already running.")
            return

        # Use werkzeug's make_server for better control potentially
        self.server = make_server(self.host, self.port, self.app, threaded=True)

        def run_server():
            logger.info(f"Starting OAuth callback server on {self.get_base_uri()}")
            try:
                self.server.serve_forever()
            except Exception as e:
                # Log exceptions that occur during serve_forever, e.g., address in use
                logger.error(f"OAuth server error: {e}")
            finally:
                logger.info("OAuth server has stopped.")

        self.server_thread = threading.Thread(target=run_server, name="OAuthServerThread")
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.info("OAuth server thread started.")

    def stop(self) -> None:
        """Stops the Flask server."""
        if self.server:
            logger.info("Attempting to shut down OAuth server...")
            try:
                self.server.shutdown()
                self.server = None  # Clear server instance
                if self.server_thread:
                    self.server_thread.join(timeout=5)  # Wait briefly for thread to exit
                    if self.server_thread.is_alive():
                        logger.warning("OAuth server thread did not exit cleanly.")
                    else:
                        logger.info("OAuth server thread stopped.")
                self.server_thread = None
            except Exception as e:
                logger.error(f"Error during OAuth server shutdown: {e}")
        else:
            logger.info("OAuth server is not running or already stopped.")

    def get_base_uri(self) -> str:
        """Gets the base URI for the server (e.g., http://localhost:8000)."""
        # Infer scheme based on common practice or config (needs improvement)
        scheme = "http"  # Default, needs better handling for HTTPS
        parsed_uri = urlparse(self.get_redirect_uri())  # Use redirect URI as hint
        if parsed_uri.scheme == "https":
            scheme = "https"
        elif parsed_uri.hostname not in ("localhost", "127.0.0.1"):
            # If not localhost and not explicitly https, keep http but warn
            logger.warning(f"Constructing base URI with http for non-localhost: {parsed_uri.hostname}")

        return f"{scheme}://{self.host}:{self.port}"

    def get_redirect_uri(self) -> str:
        """Gets the full redirect URI (e.g., http://localhost:8000/oauth2callback)."""
        # This should ideally come from config to ensure consistency
        # For now, construct it based on host/port
        # WARNING: Assumes http, adjust if HTTPS is configured/required
        scheme = "http"
        if self.port == 443:  # Basic heuristic
            scheme = "https"
        # A more robust way would be to get the configured redirect URI directly
        # return config.oauth_redirect_uri
        return f"{scheme}://{self.host}:{self.port}/oauth2callback"

    def open_browser(self, url: str) -> bool:
        """Opens a web browser to the specified URL (for local development)."""
        logger.info(f"Attempting to open browser to: {url}")
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            return False

    # HTML generation methods remain largely the same
    def _generate_success_page(self) -> str:
        """Generates a simple HTML success page."""
        # (Content is the same as before)
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Autorización Exitosa</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 40px; background-color: #f0f2f5; }
                .container { background-color: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); max-width: 500px; margin: 0 auto; }
                h1 { color: #4CAF50; }
                p { color: #666; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>¡Autorización Exitosa!</h1>
                <p>Has autorizado correctamente el acceso a tus hojas de cálculo de Google.</p>
                <p>Puedes cerrar esta ventana y volver a tu conversación con el bot.</p>
            </div>
        </body>
        </html>
        """

    def _generate_error_page(self, error_message: str) -> str:
        """Generates a simple HTML error page."""
        # (Content is the same as before, maybe escape error_message)
        import html

        escaped_error = html.escape(error_message)
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error de Autorización</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 40px; background-color: #f0f2f5; }}
                .container {{ background-color: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); max-width: 500px; margin: 0 auto; }}
                h1 {{ color: #f44336; }}
                p {{ color: #666; margin: 20px 0; }}
                .error-message {{ color: #f44336; font-weight: bold; white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Error de Autorización</h1>
                <p>Ocurrió un error durante el proceso de autorización:</p>
                <p class="error-message">{escaped_error}</p>
                <p>Por favor, intenta nuevamente con el comando /auth en el bot o contacta al administrador si el problema persiste.</p>
            </div>
        </body>
        </html>
        """
