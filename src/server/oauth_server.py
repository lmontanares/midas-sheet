import threading
import webbrowser
from typing import Callable
from urllib.parse import urlparse

from flask import Flask, jsonify, request
from loguru import logger
from werkzeug.serving import make_server

# Define a type hint for the callback function
OAuthCallbackHandler = Callable[[str, str], str | None]  # Accepts state, code; returns user_id or None


class OAuthServer:
    """
    Simple web server to handle the OAuth 2.0 redirect callback.

    Captures the authorization code and state from Google's redirect
    and passes them to a registered handler function.
    """

    def __init__(self, host: str, port: int, callback_handler: OAuthCallbackHandler, redirect_uri: str | None) -> None:
        """
        Initializes the OAuth server with required configuration.

        Args:
            host: Hostname or IP address to bind to.
            port: Port number to listen on.
            callback_handler: Function to call when the /oauth2callback is hit.
                             It receives (state, code) and should return the user_id
                             if successful, or None/raise Exception on failure.
            redirect_uri: The OAuth redirect URI to use. If None, it will be constructed
                         based on host and port.
        """
        self.host = host
        self.port = port
        self.callback_handler = callback_handler
        self.app = Flask(__name__)
        self.server: make_server | None = None
        self.server_thread: threading.Thread | None = None
        self.redirect_uri = redirect_uri

        # Check if redirect URI uses HTTPS if not localhost
        redirect_uri = self.get_redirect_uri()
        parsed_uri = urlparse(redirect_uri)
        if parsed_uri.scheme != "https" and parsed_uri.hostname not in ("localhost", "127.0.0.1"):
            logger.warning(f"OAuth Redirect URI ({redirect_uri}) is not using HTTPS. This is insecure for production environments.")

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configures the Flask server routes for OAuth callback handling."""

        @self.app.route("/oauth2callback")
        def oauth2callback():
            state = request.args.get("state")
            code = request.args.get("code")
            error = request.args.get("error")
            error_description = request.args.get("error_description")

            if error:
                error_msg = f"OAuth Error: {error}. Description: {error_description or 'N/A'}"
                logger.error(error_msg)
                return self._generate_error_page(error_msg)

            if not code or not state:
                error_msg = "Missing 'code' or 'state' parameter in OAuth callback."
                logger.error(error_msg)
                return self._generate_error_page(error_msg)

            try:
                user_id = self.callback_handler(state, code)
                if user_id:
                    logger.info(f"OAuth callback processed successfully for state: {state} (User ID inferred)")
                    return self._generate_success_page()
                else:
                    logger.error(f"OAuth callback handler failed for state: {state}")
                    return self._generate_error_page("Authentication failed. Invalid state or code.")

            except ValueError as ve:
                logger.error(f"OAuth state validation failed: {ve}")
                return self._generate_error_page(f"Authentication failed: {ve}")
            except Exception as e:
                logger.exception(f"Error processing OAuth callback for state {state}: {e}")
                return self._generate_error_page(f"An internal error occurred during authentication: {e}")

        @self.app.route("/health")
        def health():
            return jsonify({"status": "ok"})

        # Shutdown route for controlled server termination
        @self.app.route("/shutdown", methods=["POST"])
        def shutdown():
            logger.info("Shutdown request received.")
            self.stop()
            return jsonify({"message": "Server shutting down..."})

    def start(self) -> None:
        """Starts the server in a separate thread for non-blocking operation."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("OAuth server is already running.")
            return

        # Use werkzeug's make_server for better control
        self.server = make_server(self.host, self.port, self.app, threaded=True)

        def run_server():
            logger.info(f"Starting OAuth callback server on {self.get_base_uri()}")
            try:
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"OAuth server error: {e}")
            finally:
                logger.info("OAuth server has stopped.")

        self.server_thread = threading.Thread(target=run_server, name="OAuthServerThread")
        self.server_thread.daemon = True
        self.server_thread.start()
        logger.info("OAuth server thread started.")

    def stop(self) -> None:
        """Stops the Flask server cleanly to prevent resource leaks."""
        if self.server:
            logger.info("Attempting to shut down OAuth server...")
            try:
                self.server.shutdown()
                self.server = None
                if self.server_thread:
                    self.server_thread.join(timeout=5)
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
        """Gets the base URI for the server to construct callback URLs."""
        scheme = "http"
        parsed_uri = urlparse(self.get_redirect_uri())
        if parsed_uri.scheme == "https":
            scheme = "https"
        elif parsed_uri.hostname not in ("localhost", "127.0.0.1"):
            logger.warning(f"Constructing base URI with http for non-localhost: {parsed_uri.hostname}")

        return f"{scheme}://{self.host}:{self.port}"

    def get_redirect_uri(self) -> str:
        """Gets the full redirect URI for OAuth configuration."""
        if self.redirect_uri:
            return self.redirect_uri

        scheme = "http"
        if self.port == 443:
            scheme = "https"
        return f"{scheme}://{self.host}:{self.port}/oauth2callback"

    def _generate_success_page(self) -> str:
        """Generates a simple HTML success page for user feedback."""
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
        """Generates a simple HTML error page for user feedback."""
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
