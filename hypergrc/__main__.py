# Start the hyperGRC HTTP server. Run until CTRL+C is pressed.

import argparse
import http.server
import socketserver
import threading

# Get server settings.
parser = argparse.ArgumentParser(description='hyperGRC')
parser.add_argument('--bind', default="localhost:8000", help='[host:]port to bind to')
args = parser.parse_args()
if ":" in args.bind:
  BIND_HOST = args.bind.split(":", 1)[0]
  BIND_PORT = args.bind.split(":", 1)[1]
else:
  BIND_HOST = "localhost"
  BIND_PORT = args.bind

# Define the basic server.
from .routes import ROUTES
class Handler(http.server.SimpleHTTPRequestHandler):
  current_request_tl = threading.local()

  def do_GET(self):
    if self.path.startswith("/static/"):
      # For /static only, serve static files.
      super().do_GET()
    else:
      # Otherwise, run one of our routes.
      self.do_request("GET")
  def do_POST(self):
    self.do_request("POST")
  def do_request(self, method):
    # Routes use global variables to send the request response,
    # as in Flask. Although this application is single-threaded,
    # use thread-local storage for good measure to store a global
    # variable holding this request instance.
    Handler.current_request_tl.current_request = self

    try:
      # Find the route that can handle this request.
      for methods, path, route_function in ROUTES:
        if method in methods:
          m = path_matches(path, self.path)
          if m is not False:
            route_function(**m)
            return
      self.send_error(404)
    finally:
      # Reset the global variable.
      Handler.current_request_tl.current_request = None

def path_matches(route_path, path):
  # Does path match the route path specification in route_path?
  # If so, return a dict mapping path components to parts of
  # the input path. Un-URL-encode the values.
  from urllib.parse import unquote_plus
  m = route_path.match(path)
  if m:
    return {
      k: unquote_plus(v)
      for k, v
      in m.groupdict().items()
    }
  return False

def get_current_request():
  return Handler.current_request_tl.current_request

# Start server.
try:
  socketserver.TCPServer.allow_reuse_address = True
  httpd = socketserver.TCPServer((BIND_HOST, int(BIND_PORT)), Handler)
  print("Listening at http://{}:{}...".format(BIND_HOST, BIND_PORT))
  httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
