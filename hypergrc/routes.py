# This Python file uses the following encoding: utf-8

from .render import render_template
from . import opencontrol

PROJECT_LIST = []
ROUTES = []

#############################
# Helpers
#############################

def parse_route_path_string(path):
  # path looks something like:
  #   /<organization>/<project>/documents
  # Brackets denote variables holding filename-like characters only.
  # Everything else is a literal character.

  # Convert the route path into a regular expression with named groups, e.g. into:
  # /(?P<organization>\w+)/(?P<project>\w+)/(?P<documents>\w+)$

  import re, string
  ALLOWED_PATH_CHARS = string.ascii_letters + string.digits + '_.~' + '%+' + '-' # put - at the end because of re
  def replacer(m):
    if m.group(0).startswith("<"):
      # Substitute <var> with (?P<var>\w+).
      return r"(?P<{}>[{}]+)".format(m.group(1), ALLOWED_PATH_CHARS)
    else:
      # Substitute other characters with their re-escaped string.
      return re.escape(m.group(0))
  path = re.sub(r"<([a-z_]+?)>|.", replacer, path)
  path = re.compile(path + "$")
  return path

# Define a decorator to build up a routing table.
def route(path, methods=["GET"]):
  def decorator(route_function):
    path1 = parse_route_path_string(path)
    ROUTES.append((methods, path1, route_function))
    return route_function
  return decorator

#############################
# Model
#############################

def load_projects():
    # Yield a dict of information for each project by reading the opencontrol.yaml
    # file in each project directory.
    for project_dir in PROJECT_LIST:
        yield opencontrol.load_project_from_path(project_dir)

def load_project(organization_id, project_id):
    for project in load_projects():
        if project["organization"]["id"] == organization_id and project["id"] == project_id:
            return project
    raise ValueError("Project {} not found.".format(project_id))

#############################
# Routes
#############################

# Home route

@route('/')
def index(request):
    # Read each project's opencontrol.yaml file for a project name
    # and render a list of projects grouped by organization.

    # Read projects and put into organization buckets.
    organizations = { }
    for project in load_projects():
        org = project["organization"]["id"]
        if org not in organizations:
            organizations[org] = {
                "name": project["organization"]["name"],
                "projects": [],
            }
        organizations[org]["projects"].append(project)

    # Sort organizations and the projects within them.
    organizations = list(organizations.values())
    organizations.sort(key = lambda org : org["name"])
    for org in organizations:
        org["projects"].sort(key = lambda project : project["title"])

    return render_template(request, 'index.html',
        organizations=organizations
    )

# Project general routes

@route('/organizations/<organization>/projects/<project>')
def project(request, organization, project):
    """Main project page listing components."""
    project = load_project(organization, project)
    return render_template(request, 'components.html',
                            project=project,
                            components=opencontrol.load_project_components(project))

@route('/organizations/<organization>/projects/<project>/components/<component_name>')
def component(request, organization, project, component_name):
    """Show one component from a project."""
    project = load_project(organization, project)
    component = opencontrol.load_project_component(project, component_name)

    # Each control's metadata, such as control names and control family names,
    # are loaded from standards. Load the standards first.
    standards = dict(opencontrol.load_project_standards(project))

    # Load the component's controls.
    controlimpls = list(opencontrol.load_project_component_controls(component, standards))

    # Group the controls by control family, and sort the families and the controls within them.
    from collections import OrderedDict
    control_families = OrderedDict()
    for controlimpl in controlimpls:
        fam = controlimpl["family"]["sort_key"]
        if fam not in control_families:
            control_families[fam] = dict(controlimpl["family"])
            control_families[fam]["standard"] = controlimpl["standard"]
            control_families[fam]["controls"] = []
        control_families[fam]["controls"].append(controlimpl)
    control_families = list(control_families.values())
    control_families.sort(key = lambda controlfamily : controlfamily["sort_key"])
    for control_family in control_families:
        control_family["controls"].sort(key = lambda controlimpl : controlimpl["sort_key"])

    # Get total count of controls and control parts.
    control_count = len({
        ( controlimpl["standard"]["name"], controlimpl["control"]["number"] )
        for controlimpl in controlimpls
        })
    control_part_counts = len(controlimpls)

    # Word totals statistics.
    import re
    words = []
    for controlimpl in controlimpls:
        wds = len(re.split("\W+", controlimpl["narrative"]))
        words.append(wds)
    total_words = sum(words)
    average_words_per_controlpart = total_words / (len(controlimpls) if len(controlimpls) > 0 else 1) # don't err if no controlimpls

    return render_template(request, 'component.html',
                            project=project,
                            component=component,
                            control_families=control_families,
                            control_count=control_count,
                            control_part_count=control_part_counts,
                            total_words=total_words,
                            average_words_per_controlpart=average_words_per_controlpart,
                          )

@route('/organizations/<organization>/projects/<project>/controls')
def controls(request, organization, project):
    """Show all of the controls for a project."""

    project = load_project(organization, project)

    # Get a list of all controls, by standard, combining both the controls listed
    # in the standards as well as the controls in use by the components, which
    # may be different when the components have non-standard controls.

    # Start with the controls defined by the standards.

    standards = dict(opencontrol.load_project_standards(project))

    # Add in controls defined by the components.

    for component in opencontrol.load_project_components(project):
        for controlimpl in opencontrol.load_project_component_controls(component, standards):
          # If the control implementation is for an unknown standard, make a record for it.
          standard_key = controlimpl["standard"]["id"]
          if standard_key not in standards:
            standards[standard_key] = controlimpl["standard"]
            standards[standard_key].update({ 
              "controls": { }
            })

          # If the control implementation is for an unknown control, make a record for it.
          control_key = controlimpl["control"]["id"]
          if control_key not in standards[standard_key]["controls"]:
            standards[standard_key]["controls"][control_key] = controlimpl["control"]

          # Count up the number of components that have an implementation for the control.
          # Note that we may come here more than once for a component because a component
          # can have multiple "control parts". So we use a set to track the (unique)
          # components.
          control = standards[standard_key]["controls"][control_key]
          control.setdefault("components", set())
          control["components"].add(component["id"])

    # Make the standards a sorted list, and sort the controls within it.
    standards = list(standards.values())
    standards.sort(key = lambda group : group["name"])
    for standard in standards:
      standard["controls"] = list(standard["controls"].values())
      standard["controls"].sort(key = lambda control : control["sort_key"])

    # Not all controls have a URL so far. The ones that have no implementations
    # in components don't. Add a URL field now.
    from urllib.parse import quote_plus
    for standard in standards:
      for control in standard["controls"]:
        if "url" not in control:
          control["url"] = "{}/controls/{}/{}".format(
            project["url"],
            quote_plus(standard["id"]),
            quote_plus(control["id"]),
          )

    return render_template(request, 'controls.html',
                            project=project,
                            standards=standards,
                          )

@route('/organizations/<organization>/projects/<project>/controls/<standard_key>/<control_key>/<format>')
def project_control_grid(request, organization, project, standard_key, control_key, format):
    """Show all of the components that contribute to this control."""

    if format not in ("grid", "combined"):
        raise ValueError()

    # Load the project.
    project = load_project(organization, project)
    standards = dict(opencontrol.load_project_standards(project))

    # Get the control info from the standard.
    try:
      control = standards[standard_key]["controls"][control_key]
    except KeyError:
      control = None

    # Scan all of the components for all contributions to this control.
    components = []
    for component in opencontrol.load_project_components(project):
        # Iterate over its controls.
        controlimpls = []
        for controlimpl in opencontrol.load_project_component_controls(component, standards):
            if controlimpl["control"]["id"] == control_key:
                # This is a matching control --- save the control metadata
                # for the UI if we didn't get it from the standard.
                if not control:
                  control = controlimpl["control"]

                # Put this control narrative implementation into the bucket
                # for this component.
                controlimpls.append(controlimpl)

        # If there were any matched controls, keep this component and the matched
        # controls for output.
        if controlimpls:
            components.append({
              "component": component,
              "controls": controlimpls
            })

    # Sort the components and the controls within each component.
    components.sort(key = lambda component : component["component"]["name"])
    for component in components:
        component["controls"].sort(key = lambda controlimpl : controlimpl["sort_key"])

    # If we're formatting by part, then instead of grouping by components, group by
    # control part. But we use the sorted arrays above because we want to use the
    # ordering we put things in already.
    parts = []
    for component in components:
        for controlimpl in component["controls"]:
            if len(parts) == 0 or parts[-1]["part"] != controlimpl["control_part"]:
                parts.append({
                    "part": controlimpl["control_part"],
                    "components": [],
                })
            if len(parts[-1]["components"]) == 0 or parts[-1]["components"][-1]["id"] != controlimpl["component"]["id"]:
                parts[-1]["components"].append({
                    "component": controlimpl["component"],
                    "controls": [],
                })
            parts[-1]["components"][-1]["controls"].append(controlimpl)

    # Add URL info.
    from urllib.parse import quote_plus
    control["url"] = "{}/controls/{}/{}".format(
        project["url"],
        quote_plus(standard_key),
        quote_plus(control_key),
    )

    return render_template(request, 'control_{}.html'.format(format),
                            project=project,
                            standard=standards[standard_key],
                            control=control,
                            components=components,
                            parts=parts,
                          )

def clean_text(text):
  # Clean text before going into YAML. YAML gets quirky
  # about extra spaces, so get rid of them.
  import re
  text = text.strip()
  text = re.sub(r"\s+\n", "\n", text)
  if not text: # empty
    return None
  return text

@route('/update-control', methods=['POST'])
def update_control(request):
    # Load the project and the component being edited, then iterate through its
    # controls to find a maching record.
    project = load_project(request.form["organization"], request.form["project"])
    component = opencontrol.load_project_component(project, request.form["component"])
    for component in opencontrol.load_project_components(project):
        for controlimpl in opencontrol.load_project_component_controls(component, {}):
          if controlimpl["standard"]["id"] == request.form["standard"] \
           and controlimpl["control"]["id"] == request.form["control"] \
           and controlimpl.get("part") == (request.form.get("control_part")) \
           :

           controlimpl["summary"] = clean_text(request.form.get("summary", ""))
           controlimpl["narrative"] = clean_text(request.form.get("narrative", ""))
           controlimpl["implementation_status"] = clean_text(request.form.get("status", ""))
           opencontrol.update_component_control(controlimpl)
           return "OK"

    # The control was not found in the data files.
    return "NOTFOUND"
