# Start the hyperGRC HTTP server. Run until CTRL+C is pressed.

import argparse
import http.server
import socketserver

from .routes import REPOSITORY_LIST, ROUTES

# Get server settings.
parser = argparse.ArgumentParser(description='hyperGRC')
parser.add_argument('--bind', default="localhost:8000", help='[host:]port to bind to')
parser.add_argument('project', nargs="*", default=["@.hypergrc_repos"], help='Paths to project configuration files. Reads list from .hypergrc_repos by default.')
args = parser.parse_args()
if ":" in args.bind:
  BIND_HOST = args.bind.split(":", 1)[0]
  BIND_PORT = args.bind.split(":", 1)[1]
else:
  BIND_HOST = "localhost"
  BIND_PORT = args.bind

# Get other settings.
for project in args.project:
  if project.startswith("@"):
    # '@' prefixes are the Unixy-way of saying read a list from
    # a file.
    with open(project[1:], 'r') as f:
      for line in f:
        line = line.strip()
        if line:
          REPOSITORY_LIST.append(line)
  else:
    # Append this argument.
    REPOSITORY_LIST.append(project)

# Define the basic server.
class Handler(http.server.SimpleHTTPRequestHandler):
  def do_GET(self):
    if self.path.startswith("/static/"):
      # For /static only, serve static files.
      super().do_GET()
    else:
      # Otherwise, run one of our routes.
      self.do_request("GET")

  def do_POST(self):
    # Parse POST body.
    if not self.parse_request_body():
      self.send_error(404, "Invalid request body.")
      return
    self.do_request("POST")

  def parse_request_body(self):
    # We need the Content-Type header to know what format the body is in.
    if "Content-Type" not in self.headers:
      return

    # We need the Content-Length header to know how much data to read, otherwise
    # reading blocks indefinitely.
    if "Content-Length" not in self.headers:
      return

    # Parse the content type.
    import cgi, urllib.parse
    content_length = int(self.headers["Content-Length"])
    content_type = cgi.parse_header(self.headers["Content-Type"])
    if content_type[0] == "application/x-www-form-urlencoded":
      # Read the body stream, decode it, and parse it like a query string.
      body = self.rfile.read(content_length)
      body = body.decode(content_type[1].get("charset", "utf-8"))
      self.form = urllib.parse.parse_qs(body)

      # parse_qs yields { key: [value1, value2] } but multi-valued keys
      # aren't typically used, so simplify to { key: value }.
      self.form = { key: value[0] for key, value in self.form.items() }
      return True

  def do_request(self, method):
    # Find the route that can handle this request. On a match,
    # we get back a dict holding parsed parameters from the
    # request path.
    for methods, path, route_function in ROUTES:
      if method in methods:
        m = path_matches(path, self.path)
        if m is not False:
          break
    else:
      # No route_function was found.
      self.send_error(404, "Page not found.")
      return

    # Call the route function.
    #print(route_function, m, getattr(self, 'form', None))
    route_function(self, **m)

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

# Start server.
try:
  socketserver.TCPServer.allow_reuse_address = True
  httpd = socketserver.TCPServer((BIND_HOST, int(BIND_PORT)), Handler)
  print("Listening at http://{}:{}...".format(BIND_HOST, BIND_PORT))
  httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
