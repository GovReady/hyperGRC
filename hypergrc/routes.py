# This module contains hyperGRC's routes, i.e. handlers for
# virtual paths.

from .render import render_template
from . import opencontrol

PROJECT_LIST = []
ROUTES = []

#############################
# Helpers
#############################

# This is a helper function used by the @route decorator to take a Flask-like
# route pattern and make a compiled regular expression that tests for whether
# an incoming HTTP request path matches the @route's path pattern. It uses
# named groups to pick out parts of the path that become keyword arguments
# to the route function.
def parse_route_path_string(path):
  # path looks something like:
  #   /<organization>/<project>/documents
  # Brackets denote variables holding filename-like characters only.
  # Everything else is a literal character.
  #
  # Convert the route path into a regular expression with named groups, e.g. into:
  # /(?P<organization>\w+)/(?P<project>\w+)/(?P<documents>\w+)$

  # This is a helper function that takes each <varable> or unmached
  # literal character and returns a regular expression for that
  # variable or character.
  import re, string
  ALLOWED_PATH_CHARS = string.ascii_letters + string.digits + '_.~' + '%+' + '-' # put - at the end because of re
  def replacer(m):
    # If we get a <variable>...
    if m.group(0).startswith("<"):
      # Return an equivalent named group like (?P<variable>[ALLOWED_PATH_CHARS]+).
      # ALLOWED_PATH_CHARS contains characters that path variables are allowed to
      # match against. It's important that this list does not contain a slash because
      # we usually separate variables in URL patterns with slashses. Everything
      # else is just to restrict URLs to sane and safe values.
      return r"(?P<{}>[{}]+)".format(m.group(1), ALLOWED_PATH_CHARS)

    # If we get a literal character...
    else:
      # Return it escaped so it can be included in a regular expression literally.
      return re.escape(m.group(0))
  
  # Replace <variable>s with named groups and escape every other character
  # in the path pattern.
  path = re.sub(r"<([a-z_]+?)>|.", replacer, path)

  # Return the compiled regular expression.
  path = re.compile(path + "$")
  return path

# This defines an @route decorator that adds the function to the ROUTES routing
# table with a URL path pattern. methods is the allowed HTTP methods for the
# route.
def route(path, methods=["GET"]):
  def decorator(route_function):
    path1 = parse_route_path_string(path)
    ROUTES.append((methods, path1, route_function))
    return route_function
  return decorator

#############################
# Model helpers
#############################

def load_projects():
    # Yield a dict of information for each project by reading the opencontrol.yaml
    # file in each project directory.
    for project_dir in PROJECT_LIST:
        yield opencontrol.load_project_from_path(project_dir)

def load_project(organization_id, project_id):
    # Load and return a particular project.
    # TODO: This inefficiently scans all projects for one that matches the organization
    # and project ID. Better would be to cache a mapping from org/project IDs to project
    # paths at application startup.
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
    # Iterate through all of the projects and put them into
    # buckets by organization.
    organizations = { }
    for project in load_projects():
        org = project["organization"]["id"]
        if org not in organizations:
            organizations[org] = {
                "name": project["organization"]["name"],
                "projects": [],
            }
        organizations[org]["projects"].append(project)

    # Sort organizations and the projects within them by name.
    organizations = list(organizations.values())
    organizations.sort(key = lambda org : org["name"])
    for org in organizations:
        org["projects"].sort(key = lambda project : project["title"])

    # Render the homepage template.
    return render_template(request, 'index.html',
        organizations=organizations
    )

# Project general routes

@route('/organizations/<organization>/projects/<project>')
def project(request, organization, project):
    """Main project page listing components."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load its components.
    components = opencontrol.load_project_components(project)

    # Show the project's components.
    return render_template(request, 'components.html',
                            project=project,
                            components=components)

@route('/organizations/<organization>/projects/<project>/components/<component_name>')
def component(request, organization, project, component_name):
    """Show one component from a project."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load the component.
    component = opencontrol.load_project_component(project, component_name)

    # Each control's metadata, such as control names and control family names,
    # are loaded from standards. Load the standards first.
    standards = opencontrol.load_project_standards(project)

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

    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Get a list of all controls, by standard, combining both the controls listed
    # in the standards as well as the controls in use by the components, which
    # may be different when the components have non-standard controls.

    # Start with the controls defined by the standards.

    standards = opencontrol.load_project_standards(project)

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
    
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    standards = opencontrol.load_project_standards(project)

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
            if len(parts[-1]["components"]) == 0 or parts[-1]["components"][-1]["component"]["id"] != controlimpl["component"]["id"]:
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
  # about extra spaces before newlines and at the ends of
  # values, so get rid of them so that the output is
  # clean and legible. Single-line strings should not end
  # with a newline, but multi-line strings should have a
  # newline at the end of each line, including the last
  # line.
  import re
  text = text.strip()
  text = re.sub(r"\s+\n", "\n", text)
  if not text: # empty
    return None
  if "\n" in text:
    text += "\n"
  return text

@route('/update-control', methods=['POST'])
def update_control(request):
    # Load the project and the component being edited, then iterate through its
    # controls to find a maching record.
    project = load_project(request.form["organization"], request.form["project"])
    component = opencontrol.load_project_component(project, request.form["component"])
    for controlimpl in opencontrol.load_project_component_controls(component, {}):
      if controlimpl["standard"]["id"] == request.form["standard"] \
       and controlimpl["control"]["id"] == request.form["control"] \
       and controlimpl.get("control_part") == (request.form.get("control_part") or None) \
       :

       #controlimpl["summary"] = clean_text(request.form.get("summary", ""))
       controlimpl["narrative"] = clean_text(request.form.get("narrative", ""))
       controlimpl["implementation_status"] = clean_text(request.form.get("implementation_status", ""))
       opencontrol.update_component_control(controlimpl)
       return "OK"

    # The control was not found in the data files.
    return "NOTFOUND"
