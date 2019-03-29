# Construct govready-q compliance app.yaml file 

from . import opencontrol
import rtyaml

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
  print("componenyaml\n", rtyaml.dump(component))
  return rtyaml.dump(component)