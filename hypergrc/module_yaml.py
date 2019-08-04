# Construct govready-q compliance module.yaml file for a component
# This the component_module.yaml file will be named for component
# There will be no app.yaml file.
# All the outputs will be included in the component_module.yaml `outputs` section

import os.path
import pathlib
import shutil
from . import opencontrol
import rtyaml
import re

# def create_module_dirs(component, dir_path):
#   '''Create directories to hold modules files'''
#   print(component)

#   component_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", "se_{}".format(component['id']))))
#   print("\npreparing system component dir: {}".format(os.path.join(dir_path, component_id)))

#   # remove existing directory if it exists
#   if os.path.exists(os.path.join(dir_path, component_id)):
#     shutil.rmtree(os.path.join(dir_path, component_id))

def create_module_yaml(component, controlimpls, dir_path):
  '''Create and write the module.yaml file'''

  # print(component)
  component_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", "se_{}".format(component['id'].lower()))))
  print("\npreparing system component dir: {}".format(os.path.join(dir_path, component_id)))

  component_yaml = {
    "id": component_id,
    "title": component['name'],
    "questions": [
      {
        "id": "q1",
        "title": "Overview",
        "prompt": "Welcome to the CACE (**C**BP **A**WS **C**loud **E**nvironment).\n\n Let's get some information about your IT System in CACE, and we'll prepare draft controls that you will be inheriting.",
        "type": "interstitial"
      },
      {
        "id": "auditing_option",
        "title": "Auditing",
        "prompt": "UPDATE CONTENT WILL YOU USE {}".format(component['name']),
        "type": "yesno"
      }
    ],
    "output": create_component_implementation_outputs(controlimpls)
  }

  # Write component_module.yaml file content
  print("file: {}".format(os.path.join(dir_path, "se_{}.yaml".format(component_id.lower()))))
  with open(os.path.join(dir_path, "{}.yaml".format(component_id.lower())), 'w') as outfile:
    outfile.write(rtyaml.dump(component_yaml))

  return True

def create_component_implementation_outputs(controlimpls):
  '''Create an array of implementation narratives for output section'''

  output_items = []

  for ci in controlimpls:
    # print(ci['narrative'])
    component_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", ci['component']['id'])))
    control_id = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", ci['control']['id'])))
    control_part = re.sub("__+", "_", re.sub("_+$", "", re.sub("[ \.,\[\]\(\)–-]|\/|\\\\", "_", 'PART')))

    # Append to template_file_names
    output_item = {
      "id": "nist_80053rev4_ssp_{}".format(control_id),
      # "title": "NIST 800-53 rev4 SSP AU-12(b)[2]",
      "title": "NIST 800-53 rev4 SSP {}".format(control_id),
      "format": "markdown",
      "template": "{}".format(ci['narrative']),
    }

    output_items.append(output_item)

  return output_items
