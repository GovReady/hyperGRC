# This is the main entry point for hyperGRC. This module
# starts the hyperGRC HTTP server and runs until CTRL+C
# is pressed.

# Check that we are running in Python 3.5+. A common error
# is invoking this application with Python 2. For this to
# work, everything in this part must be valid Python 2
# *and* valid Python 3.
import sys
def fatal_error(message):
  sys.stderr.write("hyperGRC failed to start:\n")
  sys.stderr.write(message)
  sys.stderr.write('\n')
  sys.exit(1)
if (sys.version_info.major < 3) or (sys.version_info.major == 3 and sys.version_info.minor < 5):
  fatal_error("hyperGRC requires Python 3.5 or higher.")

###########################################################

import os
import argparse
import http.server
import socketserver

from .routes import PROJECT_LIST, ROUTES

# Read command-line arguments.

parser = argparse.ArgumentParser(description='hyperGRC')
parser.add_argument('--bind', default="localhost:8000", help='[host:]port to bind to')
parser.add_argument('project', nargs="*", default=["@.hypergrc_repos"], help='Path to a directory containing an opencontrol.yaml file for a system. Specify more than once to edit multiple system projects. Precede with an @-sign to read a list of directories from a newline-delimited text file.')
args = parser.parse_args()

# Get the host and port to bind to, which are in '[host:]port' format.
# If a host is not given, default to localhost.
if ":" in args.bind:
  BIND_HOST = args.bind.split(":", 1)[0]
  BIND_PORT = args.bind.split(":", 1)[1]
else:
  BIND_HOST = "localhost"
  BIND_PORT = args.bind

# Read list of projects from the command-line and any @-prefixed listing files.
# '@' prefixes are the Unixy-way of saying read a list from a file and use
# the contents of the listing file as if they were command-line arguments.
for project in args.project:
  if project.startswith("@"):
    # Read the listing file.
    if not os.path.isfile(project[1:]):
      fatal_error("File `{}` listing Compliance as Code repositories was not found.".format(project[1:]))
    with open(project[1:], 'r') as f:
      for line in f:
        line = line.strip()
        if line:
          PROJECT_LIST.append(line)
  else:
    # Append this argument.
    PROJECT_LIST.append(project)

# Validate that each project path is valid.
for project in PROJECT_LIST:
  if not os.path.isdir(project):
    fatal_error("Path `{}` to Compliance as Code repository was not found.".format(project))
  if not os.path.isfile(os.path.join(project, 'opencontrol.yaml')):
    fatal_error("Path `{}` to Compliance as Code repository does not contain a file named opencontrol.yaml.".format(project))

# Define the basic HTTP server request handler which is called
# on each HTTP request.
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

  # For POST requests, parse the request body which contains POST form fields.
  # Returns True on success and sets self.form (like Flask does) to a dictionary
  # holding form field name/value pairs.
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

  # Handle a request (for something other than a static file).
  def do_request(self, method):
    # Add the method as an attribute on 'self'. Some route functions
    # will look at it to see if this is a GET or POST request, etc.
    self.method = method

    # Find the (first) route that can handle this request. On a match,
    # we get back a dict holding parsed parameters from the request path.
    # See routes.py's parse_route_path_string.
    for methods, path, route_function in ROUTES:
      if method in methods:
        m = path_matches(path, self.path)
        if m is not False:
          break
    else:
      # No route matched.
      self.send_error(404, "Page not found.")
      return

    # A route matched. Call the route's function passing it this request
    # and the parsed path parameters as keyword arguments.
    # See routes.py's parse_route_path_string.
    try:
      resp = route_function(self, **m)
    except Exception as e:
      # Handle errors.
      self.send_error(500, "Internal error. Check the application console for details.")
      raise

    # Most routes don't return anything --- they have already sent a
    # HTTP response via render.py's render_template function. However
    # if the route returns a string, send that as the HTTP response
    # as text/plain.
    if isinstance(resp, str):
      # Send string return values as plain text.
      self.send_response(200)
      self.send_header("Content-Type", "text/plain; charset=UTF-8")
      self.end_headers()
      self.wfile.write(resp.encode("utf8"))

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

# Start the HTTP server.
try:
  socketserver.TCPServer.allow_reuse_address = True
  httpd = socketserver.TCPServer((BIND_HOST, int(BIND_PORT)), Handler)
  print("hyperGRC started...")
  print("Listening at http://{}:{}...".format(BIND_HOST, BIND_PORT))
  httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
