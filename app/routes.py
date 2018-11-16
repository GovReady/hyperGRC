# This Python file uses the following encoding: utf-8

from flask import render_template, request, redirect, url_for
from app import app
from app.forms import LoginForm

import collections
import glob
import os.path
import os
import rtyaml
import sys

import re
from jinja2 import evalcontextfilter, Markup, escape

#############################
# Find available repos
#############################
REPO_FILE = ".hypergrc_repos"
if not os.path.isfile(REPO_FILE):
  raise ValueError('You must set ".hypergrc_repos" file')

REPO_LIST = []
with open(REPO_FILE, 'r') as f:
  for line in f:
    REPO_LIST.append(line.strip())

print(REPO_LIST)

# Digest .govready files from repos
cfgs = []
for govready_file in REPO_LIST:

  if not os.path.isfile(govready_file):
    raise ValueError("Could not find indicated file {} locally.".format(govready_file))

  with open(govready_file, 'r') as f:
    gr_cfg = rtyaml.load(f)

  cfgs.append({"organization": gr_cfg["organization"]["name"],
               "project": gr_cfg["system"]["name"],
               "src_repo": gr_cfg["system"]["src_repo"]
              })
  print(cfgs)


#############################
# Read in congfig files
#############################
GOVREADY_FILE = app.config['GOVREADY_FILE']
if not GOVREADY_FILE:
  raise ValueError('You must set "GOVREADY_FILE" environment variable')

if not os.path.isfile(GOVREADY_FILE):
  raise ValueError('You must have ".govready" file and "GOVREADY_FILE" environment variable')

with open(GOVREADY_FILE, 'r') as f:
    gr_cfg = rtyaml.load(f)

cfg = {"organization": gr_cfg["organization"]["name"],
       "project": gr_cfg["system"]["name"],
       "standard": gr_cfg["system"]["primary_standard"],
       "standard_file": "nist-800-53-rev4.yaml",
       "standard_controls_dir": os.path.join(os.path.dirname(os.path.abspath(GOVREADY_FILE)), gr_cfg["standard_controls_dir"]),
       "src_repo": gr_cfg["system"]["src_repo"],
       "mode": gr_cfg["mode"],
       "hgrc_version": gr_cfg["hgrc_version"],
       "user_name": gr_cfg["team"]["user"]["name"],
       "components_dir": os.path.join(os.path.dirname(os.path.abspath(GOVREADY_FILE)), gr_cfg["components_dir"]),
       "document_dirs": ""
}


# Set path info in local workstation mode
if cfg['mode'] == "local workstation":
  pass

# Check components and standards directories exist
if not os.path.isdir(cfg["components_dir"]):
    print("Can't find directory:", cfg["components_dir"])
    sys.exit()

if not os.path.isdir(cfg["standard_controls_dir"]):
    print("Can't find directory:", cfg["standard_controls_dir"])
    sys.exit()

# To Do: Check standard file exists
primary_standard = gr_cfg["system"]["primary_standard"]
standards = {}
for item in gr_cfg["standards"]:
  standards[item["standard"]] = item["standard_file"]
print(standards)
standard_file = standards[primary_standard]
cfg["standard_file"] = standard_file

# Get document directories
document_dirs = {}
for item in gr_cfg["documents"]:
  document_dirs[item["name"]] = {"directory": item["directory"],
                                  "description": item["description"]}
print("document_dirs ", document_dirs)
cfg["document_dirs"] = document_dirs

# Get certification
# Let's hardcode to FedRAMP Low for feature MVP
cfg["certification_file"] = "ref/certifications/fisma-low-impact.yaml"
# Set components ordered dict
_component_names = collections.OrderedDict([(None, None)])
for cn in gr_cfg["components"]:
  _component_names[cn["name"]] = cn["directory"]

cfg["component_names"] = _component_names


#############################
# Helpers
#############################
def get_standard_controls_data():
  # Read in all the controls
  with open(os.path.join(cfg["standard_controls_dir"], cfg["standard_file"])) as f:
    standard_controls_data = rtyaml.load(f)
  return standard_controls_data

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

def nl2br(value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value))
                         )
    return result
app.jinja_env.filters['nl2br'] = nl2br

def plain_text_to_markdown(s):
  # Paragraphs need two newlines in Markdown.
  s = s.replace("\n", "\n\n")
  s = s.replace(unicode("•", "utf8"), "*")
  return s
app.jinja_env.filters['text2md'] = plain_text_to_markdown

def blockquote(s):
  return "\n".join((" " + line) for line in s.strip().split("\n")) + "\n"
app.jinja_env.filters['blockquote'] = blockquote

#############################
# Model
#############################


def load_components(cfg):
    # Get the set of components by reading all of the controls,
    # so we keep the code simple and don't repeat logic, although
    # it might be faster if we didn't have to read all of the
    # control narrative data files.
    component_names = { entry[5] for entry in load_component_controls(cfg) }
    components = [
      { "name": component_name }
      for component_name in component_names ]
    components.sort(key = lambda component : component['name'])
    return components

def load_component_controls(cfg, filter_control_number=None, filter_component_name=None):
    # Read in all of the components and their control narratives.
    # Return a generator that iterates over control narrative records.
    components_glob = os.path.join(cfg["components_dir"], "*")
    for component_dir in glob.glob(components_glob):
        if not os.path.isdir(component_dir):
          continue

        component_name = os.path.basename(component_dir)
        component_order = None

        # Apply the control name filter.
        if filter_component_name and component_name.lower() != filter_component_name.lower():
          continue

        for control_family_fn in glob.glob(os.path.join(component_dir, "*.yaml")):
          with open(control_family_fn) as f:
            data = rtyaml.load(f)

            # Read out each control and store it in memory as a tuple
            # that holds the information we need to sort all of the
            # items into the right order for the SSP.

            # If the data file has a "satisfies" key, then it is in
            # an OpenControl-like format.
            for control in data.get("satisfies", []):
              # Prepare control description text and fix spacing before parenthesis for subcontrols
              # TODO: clean up this regex, but it works.
              control_id = control["control_key"].replace("-0", "-")

              # Apply the control number filter.
              if filter_control_number and control_id != filter_control_number:
                continue

              yield (
                control["control_key"].split("-", 1)[0], # extract control family from control number
                control["control_key"],
                control.get("control_key_part") or "",
                control.get("control_name"),
                component_order,
                component_name,
                control.get("security_control_type"),
                control.get("implementation_status"),
                control.get("summary", None),
                control.get("narrative", None)
                # control["control_description"],
              )

            # If the data file has a "controls" key, then it is in
            # a GovReady-parsed SSP format.
            for control in data.get("controls", []):
              # Apply the control number filter.
              if filter_control_number and control["control"] != filter_control_number:
                continue

              yield (
                control["control"].split("-", 1)[0], # extract control family from control number
                control["control"],
                None, # TODO, no part
                control["control-name"],
                component_order,
                component_name,
                control.get("security_control_type"),
                control.get("implementation_status") or "Unknown",
                control.get("summary", None),
                control.get("control-narrative", None)
                # control["control_description"],
              )

#############################
# Routes
#############################
@app.route('/')
def index():
    repo_list = REPO_LIST
    organization = cfg["organization"]
    project =  cfg["project"]
    return render_template('index.html',
                            cfg=cfg,
                            repo_list=repo_list,
                            cfgs=cfgs
                          )

@app.route('/login')
def login():
    form = LoginForm()
    return render_template('login.html', title='Sign In', form=form)

@app.route('/<organization>/<project>/documents')
def documents(organization, project):
    """Read and list documents in documents directory"""
    docs = []
    message = ""
    for doc_dir in cfg["document_dirs"].keys():
      print("doc_dir: ", doc_dir)
      doc_dir_path = os.path.join(os.path.dirname(os.path.abspath(GOVREADY_FILE)), doc_dir)

      if not os.path.isdir(doc_dir_path):
        message += "<br /> Directory {} not found in repository files".format(doc_dir_path)
      else:
        docs_glob = doc_dir_path.rstrip('/') + "/*"
        for doc in glob.glob(docs_glob):
          if os.path.isfile(doc):
            docs.append({'name': os.path.basename(doc)})
      docs.sort()
    return render_template('documents.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            src_repo=cfg["src_repo"],
                            message=message,
                            documents=docs
                          )

@app.route('/<organization>/<project>/assessments')
def assessments(organization, project):
    return render_template('assessments.html',
                            cfg=cfg,
                            organization=organization,
                            project=project
                          )

@app.route('/<organization>/<project>/settings')
def settings(organization, project):
    return render_template('settings.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            govready_file=GOVREADY_FILE
                          )

@app.route('/<organization>/<project>/poams')
def poams(organization, project):
    components_dir = cfg["components_dir"]
    return render_template('poams.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            poams=poams)

@app.route('/<organization>/<project>/components')
def components(organization, project):
    return render_template('components.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            components=load_components(cfg))

@app.route('/<organization>/<project>/team')
def team(organization, project):
    components_dir = cfg["components_dir"]

    components = []
    components_glob = components_dir.rstrip('/') + "/*"
    # Read in all of the components' control implementation texts.
    for component_dir in glob.glob(components_glob):
        if os.path.isdir(component_dir):
          components.append({'name': os.path.basename(component_dir)})

    return render_template('team.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            components=components)

# 800-53
@app.route('/<organization>/<project>/controls')
@app.route('/<organization>/<project>/800-53-r4/controls')
def controls(organization, project):
    # Read in control list from certification file
    certification_file = cfg["certification_file"]
    if not os.path.isfile(certification_file):
      raise ValueError('Certification file {} not found.'.format(certification_file))

    with open(certification_file) as f:
      certification_controls = rtyaml.load(f)

    standard_controls = get_standard_controls_data()

    # if certification['']

    return render_template('controls.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            certification_controls=certification_controls,
                            standard_controls=standard_controls
                          )

@app.route('/<organization>/<project>/800-53r4/control/<control_number>/combined')
def control_legacy(organization, project, control_number):
    control_number = control_number.upper()
    standard_controls_data = get_standard_controls_data()

    # Pass along key values
    control_name = standard_controls_data[control_number]["name"]
    control_description = standard_controls_data[control_number]["description"]

    components_dir = cfg["components_dir"]

    # The map component directory names back to long names. Use an
    # OrderedDict to maintain a preferred component order.
    component_names = cfg["component_names"]
    component_order = { component: i for i, component in enumerate(component_names) }
    ssp = []
    control_components = {}

    ssp = list(load_component_controls(cfg, filter_control_number=control_number))
    ssp.sort()

    return render_template('control.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            control_number=control_number,
                            control_name=control_name,
                            control_description=control_description,
                            components=components,
                            ssp=ssp
                          )

@app.route('/<organization>/<project>/800-53r4/control/<control_number>')
def control(organization, project, control_number):
    control_number = control_number.upper().replace("-0", "-")
    standard_controls_data = get_standard_controls_data()

    # Pass along key values
    control_name = standard_controls_data[control_number]["name"]
    control_description = standard_controls_data[control_number]["description"]

    # Load control narratives.
    ssp = list(load_component_controls(cfg, filter_control_number=control_number))
    ssp.sort()

    # Make set of components.
    components_involved = set()
    for entry in ssp:
      components_involved.add(entry[5])
    components_involved = sorted(components_involved)

    return render_template('control2.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            component_names=components_involved,
                            control_number=control_number,
                            control_name=control_name,
                            control_description=control_description,
                            components=components,
                            ssp=ssp
                          )

@app.route('/<organization>/<project>/800-53r4/component/<component_name>')
def component(organization, project, component_name):
    # Load control narratives.
    component_name = component_name.lower()
    ssp = list(load_component_controls(cfg, filter_component_name=component_name))
    ssp.sort()

    # Make set of control families.
    control_families = set()
    for entry in ssp:
      control_families.add(entry[0])
    control_families = sorted(control_families)

    return render_template('component2.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            component_name=component_name,
                            control_families=control_families,
                            ssp=ssp,
                          )

# HIPAA
@app.route('/<organization>/<project>/hipaa/controls')
def hipaa_controls(organization, project):

    return render_template('controls_hipaa.html',
                            cfg=cfg,
                            organization=organization,
                            project=project
                          )

@app.route('/<organization>/<project>/hipaa/control/<control_number>')
def hipaa_control(organization, project, control_number):
    # control_number = control_number.upper().replace("-0", "-")

    standard_file = "hipaa-draft.yaml"
    standard_controls_data = get_standard_controls_data()

    # Pass along key values
    control_name = standard_controls_data[control_number]["name"]
    control_description = standard_controls_data[control_number]["description"]

    components_dir = cfg["components_dir"]

    # The map component directory names back to long names. Use an
    # OrderedDict to maintain a preferred component order.
    component_names = collections.OrderedDict([
      (None, None),
      ("CivicActions",  "CivicActions"),
      ("Drupal",        "Drupal"),
      ("DNFSB",         "DNFSB"),
      ("Acquia-ACE",    "Acquia-ACE"),
      ("AWS",           "AWS"),
      ("MacOS", "MacOS")
    ])
    component_order = { component: i for i, component in enumerate(component_names) }
    ssp = []

    components_involved = []
    control_components = {}

    components = []
    components_glob = components_dir.rstrip('/') + "/*"
    # Read in all of the components' control implementation texts.
    for component_dir in glob.glob(components_glob):
        if os.path.isdir(component_dir):
          components.append({'name': os.path.basename(component_dir)})
        component_controls = []

        for control_family_fn in glob.glob(os.path.join(component_dir, "*.yaml")):
          with open(control_family_fn) as f:
            component_controlfam_data = rtyaml.load(f)

            # Read out each control and store it in memory as a tuple
            # that holds the information we need to sort all of the
            # items into the right order for the SSP.
            for control in component_controlfam_data["satisfies"]:
              # Prepare control description text and fix spacing before parenthesis for subcontrols
              # TODO: clean up this regex, but it works.
              control_id = control["control_key"].replace("-0", "-")
        
              if control_id != control_number:
                continue

              ssp.append((
                component_order[component_controlfam_data["name"]],
                component_names[component_controlfam_data["name"]],
                component_controlfam_data["family"],
                control.get("control_key"),
                control.get("control_name"),
                control.get("control_key_part") or "",
                control.get("security_control_type"),
                control.get("implementation_status"),
                control.get("summary", None),
                control.get("narrative", None)
                # control["control_description"],
              ))

              if component_controlfam_data["name"] not in components_involved:
                components_involved.append(component_controlfam_data["name"])

    ssp.sort()
    return render_template('control2.html',
                            cfg=cfg,
                            organization=organization,
                            project=project,
                            component_names=components_involved,
                            control_number=control_number,
                            control_name=control_name,
                            control_description=control_description,
                            components=components,
                            ssp=ssp
                          )

    
@app.route('/update-control', methods=['POST'])
def update_control():
    # Split the 'path' variable to get the component, control, and control path.
    # TODO: The front-end should pass these as separate parameters.
    component, control, part = request.form["path"].split("/")

    # Get the control narrative user input.
    summary = request.form["summary"]
    narrative = request.form["narrative"]

    # Update the component's control.

    # Get the component directory.
    # TODO: SECURITY: User input is currently trusted and assumed to be a safe, valid
    # directory name.
    component_dir = os.path.join('..', 'components', component)

    # Scan all of the YAML files in matching component's directory looking for one that
    # contains the control. We are helpfully not assuming that controls are in their
    # proper control family file.
    # GREG: Could this helpfulness ever overwrite wrong information b/c we assume only
    # one file in component directory has control?
    for control_file in os.listdir(component_dir):
      if control_file.endswith(".yaml"):
        # Open the control family file for read/write.
        with open(os.path.join(component_dir, control_file), "r+") as f:
          # Parse the content.
          data = rtyaml.load(f)

          # Look for a matching control entry.
          for controldata in data["satisfies"]:
            if controldata["control_key"] == control and (controldata.get("control_key_part") or "") == part:
              # Found the right entry. Update the fields.

              def clean_text(text):
                # Clean text before going into YAML. YAML gets quirky
                # about extra spaces, so get rid of them.
                text = text.strip()
                text = re.sub(r"\s+\n", "\n", text)
                if not text: # empty
                  return None
                return text

              controldata["summary"] = clean_text(summary)
              controldata["narrative"] = clean_text(narrative)

              # Write back out to the data files.
              f.seek(0);
              f.truncate()
              rtyaml.dump(data, f)

              # Return OK, we're good.
              return "OK"

    # The control was not found in the data files.
    return "NOTFOUND"

@app.route('/update-govready-file', methods=['POST'])
def update_govready_file():
    # Change the repo files we are seeing by reading a different govready file
    # Get the .govready file path user input.
    govready_file_new = request.form["govready_file_new"]
    print("processing update_govready_file ", govready_file_new)

    message = ""
    if not os.path.isfile(govready_file_new):
      message = "{} file not found.".format(govready_file_new)
    else:
      os.environ['GOVREADY_FILE'] = govready_file_new
      app.config['GOVREADY_FILE'] = os.environ['GOVREADY_FILE']

      GOVREADY_FILE = app.config['GOVREADY_FILE']
      print("env GOVREADY_FILE now ", os.environ.get('GOVREADY_FILE'))
      message = "GOVREADY_FILE changed to {}.".format(GOVREADY_FILE)
      # Return OK, we're good.
      # redirect(url_for('settings', organization="DNFSB", project="project"))
      redirect(url_for('index'))
      return "OK"

    # The control was not found in the data files.
    return "NOTFOUND {}".format(message)