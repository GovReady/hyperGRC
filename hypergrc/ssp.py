# Construct system security plans from project data.

from . import opencontrol

def blockquote(s):
  # Prepend "> " to the start of each line in s.
  return "".join(("> " + line + "\n") for line in s.strip().split("\n"))

def build_ssp(project, options):
  # Create the introduction of the SSP.

  from io import StringIO
  buf = StringIO()
  buf.write("# " + project['title'] + " System Security Plan\n\n")

  # Load the standards in use by this project.
  standards = opencontrol.load_project_standards(project)

  # Collect all of the control narratives.
  narratives = []
  for component in opencontrol.load_project_components(project):
    # Iterate over its controls...
    for controlimpl in opencontrol.load_project_component_controls(component, standards):
      # If only one control family is requested, then skip others.
      if options.get("only-family"):
        if controlimpl["family"]["abbrev"] != options["only-family"]:
          continue

      # Add the narrative to the list of narratives to output.
      narratives.append(controlimpl)

  # Sort the narratives by standard, family, control, part, and then by component.
  narratives.sort(key = lambda narrative : (
    narrative["standard"]["name"],
    narrative["family"]["sort_key"],
    narrative["control"]["sort_key"],
    narrative["control_part"] is not None, # narratives for the null part go first
    narrative["control_part"],
    narrative["component"]["name"] )
  )

  # Concatenate the narratives.
  current_section = []
  for narrative in narratives:
    # Get the section names at the levels of hierarchy above this control.
    section = [
      narrative["standard"]["name"],
      narrative["family"]["abbrev"] + ": " + narrative["family"]["name"],
      narrative["control"]["number"] + ": " + narrative["control"]["name"],
      narrative["control_part"],
      narrative["component"]["name"],
    ]

    # Pop out of the current section until we reach a common parent.
    while len(current_section) > len(section) \
     or repr(current_section) != repr(section[:len(current_section)]):
     current_section.pop(-1)

    # Drill down into the right section. As we drill down, output
    # section headings. Except some levels can be None, which represents
    # a level with no heading.
    while len(current_section) < len(section):
      next_level = section[len(current_section)]
      if next_level:
        buf.write("#" * (len(current_section)+1) + " " + next_level + "\n\n")
      current_section.append(next_level)

      # If we just opened a section for a control, output the control
      # description.
      if options.get("include-control-descriptions"):
        if len(current_section) == 3 and narrative["control"].get("description"):
          buf.write(blockquote(narrative["control"]["description"]).strip() + "\n\n")


    # Output the narrative text. We assume the narrative text is formatted
    # as Markdown --- we don't escape anything.
    buf.write(narrative['narrative'] + "\n\n")

  return buf.getvalue()

if __name__ == "__main__":
  # Parse for optionally including control description from standard
  from argparse import ArgumentParser
  parser = ArgumentParser(description="Combine component controls into a simple SSP.")
  parser.add_argument("-d", "--description", action="store_true", dest="include_descriptions", default=False,
                      help="include control descriptions")
  parser.add_argument("projectdir", help="path to a directory containing an opencontrol.yaml file")
  parser.add_argument("-f", "--family", dest="family",
                      help="include only controls for the given family (e.g. AC, SI)")
  #parser.add_argument("-s", "--separate", dest="separate",
  #                    help="output each control family to separate files in the given directory")
  args = parser.parse_args()

  # Load project.
  project = opencontrol.load_project_from_path(args.projectdir)

  # Generate the SSP and print it out.
  print(build_ssp(project, {
    "include-control-descriptions": args.include_descriptions,
    "only-family": args.family,
  }))