import re

from jinja2 import Environment, FileSystemLoader, evalcontextfilter, Markup, escape

jinja_env = Environment(
	loader=FileSystemLoader(__package__ + '/templates'),
	autoescape=True)

#############################
# Jinja Helpers
#############################

import urllib.parse
jinja_env.filters['urlencode'] = urllib.parse.quote_plus

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

def nl2br(value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value))
                         )
    return result
jinja_env.filters['nl2br'] = nl2br

def plain_text_to_markdown(s):
  # Paragraphs need two newlines in Markdown.
  s = s.replace("\n", "\n\n")
  s = s.replace(unicode("•", "utf8"), "*")
  return s
jinja_env.filters['text2md'] = plain_text_to_markdown

def blockquote(s):
  return "\n".join((" " + line) for line in s.strip().split("\n")) + "\n"
jinja_env.filters['blockquote'] = blockquote

def render_template(request, template_fn, **contextvars):
	try:
		template = jinja_env.get_template(template_fn)
		body = template.render(**contextvars)
	except Exception as e:
		import traceback
		traceback.print_exc()
		request.send_response(500)
		request.send_header("Content-Type", "text/plain; charset=UTF-8")
		request.end_headers()
		request.wfile.write(b"Ooops! Something went wrong.")
		return

	request.send_response(200)
	request.send_header("Content-Type", "text/html; charset=UTF-8")
	request.end_headers()
	request.wfile.write(body.encode("utf8"))
