# Construct govready-q compliance app.yaml file 

import os.path
import pathlib
import shutil
from . import opencontrol
import rtyaml
import re

def create_app_dirs(component, dir_path):
  '''Create directories to hold app files'''
  # print(component)

  component_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", component['id'])))
  print("\npreparing system component dir: {}".format(os.path.join(dir_path, component_id)))

  # remove existing directory if it exists
  if os.path.exists(os.path.join(dir_path, component_id)):
    shutil.rmtree(os.path.join(dir_path, component_id))

  # create various directories
  if not os.path.exists(os.path.join(dir_path, component_id, "templates")):
    os.makedirs(os.path.join(dir_path, component_id, "templates"))
  if not os.path.exists(os.path.join(dir_path, component_id, "assets")):
    os.makedirs(os.path.join(dir_path, component_id, "assets"))

  pathlib.Path(os.path.join(dir_path, component_id, "templates", 'README.md')).touch()

def create_app_implementation_files(controlimpls, dir_path):
  '''Create a template file for each control implementation narrative'''

  template_file_names = ""
  for ci in controlimpls:
    print(ci['narrative'])
    component_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", ci['component']['id'])))
    control_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", ci['control']['id'])))

    # Append to template_file_names
    template_file_names += "- {}".format(os.path.join("templates", 'nist_80053rev4_ssp_'+control_id+ ".md\n"))
    # Prepare template content
    content = """id: nist_80053rev4_ssp_{}
title: NIST 800-53 rev4 SSP {}
format: markdown
...

{}

""".format(control_id, control_id, ci['narrative'])
    # print("Content: ", content)
    print("template_file_names", template_file_names)
    # Write content into each file
    with open(os.path.join(dir_path, component_id, "templates", 'nist_80053rev4_ssp_'+control_id+'.md'), 'w') as outfile:
      outfile.write(content)

    # Prepare app.yaml file content
    content = """id: app
title: {}
type: project
version: 0.5
icon: app.png
catalog:
  category: TBD
  vendor: {}
  vendor_url: TBD
  status: stub
  version: 0.2
  source_url: {}
  description:
    short: |
      {} {}
  recommended_for:
  - key_short: Org
    value: Small
  - key_short: Tech
    value: Sophisticated
  - key_short: Role
    value: PM
introduction:
  format: markdown
  template: |
    Compliance app for {} {}
questions:
- id: overview
  title: Overview
  prompt: |
    Compliance app for {} {}
  type: interstitial

output:
{}
""".format(ci["component"]["id"],
           ci["component"]["project"]["organization"]["name"],
           ci["component"]["project"]["source_repository"],
           ci["component"]["project"]["organization"]["name"],
           ci["component"]["id"],
           ci["component"]["project"]["organization"]["name"],
           ci["component"]["id"],
           ci["component"]["project"]["organization"]["name"],
           ci["component"]["id"],
           template_file_names,
          )

    print("writing app.yaml file")

    # Write app.yaml file content
    with open(os.path.join(dir_path, component_id, "app.yaml"), 'w') as outfile:
      outfile.write(content)

def build_app(component, options):

  # create buffer for output
  from io import StringIO
  buf = StringIO()

  # Load the standards in use by this project.
  # standards = opencontrol.load_project_standards(project)

  # Collect all of the control narratives.
  # narratives = []
  # for component in opencontrol.load_project_components(project):
  #   # Iterate over its controls...
  #   for controlimpl in opencontrol.load_project_component_controls(component, standards):
  #     # If only one control family is requested, then skip others.
  #     if options.get("only-family"):
  #       if controlimpl["family"]["abbrev"] != options["only-family"]:
  #         continue

  #     # Add the narrative to the list of narratives to output.
  #     narratives.append(controlimpl)

  # # Sort the narratives by standard, family, control, part, and then by component.
  # narratives.sort(key = lambda narrative : (
  #   narrative["standard"]["name"],
  #   narrative["family"]["sort_key"],
  #   narrative["control"]["sort_key"],
  #   narrative["control_part"] is not None, # narratives for the null part go first
  #   narrative["control_part"],
  #   narrative["component"]["name"] )
  # )

  # Dump the component information to app.yaml
#   import csv
#   csvwriter = csv.writer(buf, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
#   csvwriter.writerow(["Control", "Control Part", "Standard Name", "Component Name", "Control Narrative"])
#   for narrative in narratives:
# #    if narrative["control_part"] is not None:
#       csvwriter.writerow([narrative["control"]["id"],
#                           narrative["control_part"],
#                           narrative["standard"]["name"],
#                           narrative["component"]["name"],
#                           narrative["narrative"].strip()
#                           ])
  # buf.write(component)
  # return buf.getvalue()
  # print("componenyaml\n", rtyaml.dump(component))
  return rtyaml.dump(component)
