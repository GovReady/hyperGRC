# This module contains hyperGRC's routes, i.e. handlers for
# virtual paths.

from .render import render_template, redirect, send_file, send_json_response
from . import opencontrol
import os
import glob
import rtyaml

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

# Helper to retrive all document directories, included nested sub-directories
def get_document_directories(project):

  # Temporarily hardcode the documents directory to "outputs".
  # We are hardcoding the directory until we modify the opencontrol.yaml
  # file to include a list of directories.
  dir_list = [x[0] for x in os.walk(os.path.join(project["path"], "outputs"))]
  return dir_list

#######################
# Routes for Main Pages
#######################

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

    # Prepare modify page message
    edit_file = os.path.join(os.getcwd(), "repos.conf")
    modify_msg = "To modify listed projects, change hyperGRC launch params or edit file: `{}`".format(edit_file)

    # Render the homepage template.
    return render_template(request, 'index.html',
        organizations=organizations,
        modify_msg=modify_msg
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

    # Load its components and sort them.
    components = list(opencontrol.load_project_components(project))
    components.sort(key = lambda component : component["name"])

    # Prepare modify page message
    edit_dir = os.path.join(project["path"], "components")
    edit_file = "opencontrol.yaml"
    modify_msg = "To modify listed components (1) Add/remove components from directory: `{}` and (2) Update components in file: `{}`".format(edit_dir, edit_file)

    # Show the project's components.
    return render_template(request, 'components.html',
                            project=project,
                            components=components,
                            modify_msg=modify_msg)

@route('/organizations/<organization>/projects/<project>/documents')
def documents(request, organization, project):
    """Read and list documents"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Prepare modify page message
    # Use our assumed hardcoded 'outputs' directory as repo's top level document directory
    edit_dir = os.path.join(project["path"], "outputs")
    modify_msg = "To modify listed documents, change files in document directories of `{}`".format(edit_dir)

    # Create variables for documents and message
    docs = []
    message = ""

    # We want to be able to store documents in our repo.
    # If document directories exists, read all the documents and append
    # information on each document to the list of doc objects to pass to
    # the page to be rendered.
    document_dirs = get_document_directories(project)
    for doc_dir_path in document_dirs:
      # Skip anything that is not really a directory
      if not os.path.isdir(doc_dir_path):
        continue
      else:
        # Get the files from within the directory
        docs_glob = doc_dir_path.rstrip('/') + "/*"
        for doc in glob.glob(docs_glob):
          # Skip any commonly found files that are MS Word document temp files 
          if "~$" in os.path.basename(doc):
            continue
          if os.path.isfile(doc):
            # Append found document file paths to our list of documents
            docs.append({'name': os.path.basename(doc),
                         'file_path': doc,
                         'rel_file_path': doc.replace(os.path.join(project["path"], "outputs/"), "")
                        })

    # What? No documents found? Generate a message to display.
    if len(docs) == 0:
      message += "No documents are listed in your repository."

    return render_template(request, 'documents.html',
                            project=project,
                            organization=organization,
                            message=message,
                            documents=docs,
                            modify_msg=modify_msg
                          )

@route('/organizations/<organization>/projects/<project>/documents/?f=<doc_file_path>')
def document(request, organization, project, doc_file_path):
    """Retrieve document from project document directory"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Compute file path to file within project directory
    # Currently, assume documents directory is 'outputs'
    project_doc_dir = "outputs"
    doc = os.path.join(project["path"], project_doc_dir, *doc_file_path.split(">"))

    # TODO: Make sure this file exists and has no relative paths or goes to system directory
    # We aren't too worried about security when user is running on their own workstation.
    if os.path.isfile(doc):
      fn, fe = os.path.splitext(doc)
      if fe.lower() not in [".txt", ".conf", ".csv", ".md",
                            ".xls", ".xlsx", ".doc", ".docx", ".jpeg", ".jpg", ".png", "gif", ".pdf"]:
        message="Document type '{}'' of computed file request '{}' not supported.".format(fe, doc)
        return message
      else:
        send_file(request, doc)
    else:
      message="Computed file request '{}' not found or is not a file.".format(doc)
      return message

@route('/organizations/<organization>/projects/<project>/team')
def team(request, organization, project):
    """Show settings for the project"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Read the team file
    try:
      with open(os.path.join(project["path"], "team", "team.yaml"), encoding="utf8") as f:
        team_data = rtyaml.load(f)
        team = team_data["team"]
      message = None
    except:
      team = []
      message = ("Capture your team information in the file: `{}`.".format(os.path.join(project["path"], "team", "team.yaml")))

    # Prepare modify page message
    edit_file = os.path.join(project["path"], "team", "team.yaml")
    modify_msg = "To modify team information, update file: `{}`".format(edit_file)

    return render_template(request, 'team.html',
                          project=project,
                          message=message,
                          modify_msg=modify_msg,
                          team=team
                          )

@route('/settings')
def settings(request):
    """Show settings"""

    # Read the version file
    try:
      with open("VERSION", encoding="utf8") as f:
        HYPERGRC_VERSION=f.read().replace('\n', '')
    except:
      fatal_error("hyperGRC requires a VERSION file.")

    # Prepare modify page message
    modify_msg = "View this page within a project for modification details."

    return render_template(request, 'settings.html',
                          modify_msg=modify_msg,
                          hypergrc_version=HYPERGRC_VERSION
                          )

@route('/organizations/<organization>/projects/<project>/settings')
def project_settings(request, organization, project):
    """Show settings, including project settings"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Read the version file
    try:
      with open("VERSION", encoding="utf8") as f:
        HYPERGRC_VERSION=f.read().replace('\n', '')
    except:
      fatal_error("hyperGRC requires a VERSION file.")

    # Prepare modify page message
    edit_dir = os.path.join(project["path"], "opencontrol.yaml")
    modify_msg = "To modify settings, update file: `{}`".format(edit_dir)

    return render_template(request, 'settings.html',
                          project=project,
                          modify_msg=modify_msg,
                          hypergrc_version=HYPERGRC_VERSION
                          )

@route('/organizations/<organization>/projects/<project>/assessments')
def assessments(request, organization, project):
    """Create dummy static page showing assessments"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Prepare modify page message
    modify_msg = "This page is a feature mockup, does not yet work and cannot currently be modified."

    return render_template(request, 'assessments.html',
                            project=project,
                            modify_msg=modify_msg
                          )

@route('/organizations/<organization>/projects/<project>/poams')
def poams(request, organization, project):
    """Create dummy static page showing POA&Ms"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Prepare modify page message
    modify_msg = "This page is a feature mockup, does not yet work and cannot currently be modified."

    return render_template(request, 'poams.html',
                            project=project,
                            modify_msg=modify_msg
                          )

# Components and controls within a project

@route('/organizations/<organization>/projects/<project>/components/<component_name>')
def component(request, organization, project, component_name):
    """Show one component from a project."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load the component.
    try:
      component = opencontrol.load_project_component(project, component_name)
    except ValueError:
      return "Component `{}` in URL not found in project.".format(component_name)

    # Each control's metadata, such as control names and control family names,
    # is loaded from standards. Load the standards first.
    standards = opencontrol.load_project_standards(project)

    # Load the component's controls.
    controlimpls = list(opencontrol.load_project_component_controls(component, standards))

    # Group the controls by control family, and sort the families and the controls within them.
    # Iterate over the controls....
    from collections import OrderedDict
    control_families = OrderedDict()
    for controlimpl in controlimpls:
        # If this is the first time we're seeing this control family, make a new
        # bucket for the control family.
        fam_id = (controlimpl["standard"]["id"], controlimpl["family"]["id"])
        if fam_id not in control_families:
            control_families[fam_id] = {
              "id": controlimpl["family"]["id"],
              "name": controlimpl["family"]["name"],
              "abbrev": controlimpl["family"]["abbrev"],
              "sort_key": (controlimpl["standard"]["name"], controlimpl["family"]["sort_key"]),
              "standard": controlimpl["standard"],
              "controls": [],
            }

        # Put this control into the bucket for its family.
        control_families[fam_id]["controls"].append(controlimpl)

    # Sort the families and then the controls within them.
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

    # Compute some statistics about how many words are in the controls.
    import re
    words = []
    for controlimpl in controlimpls:
        wds = len(re.split(r"\W+", controlimpl["narrative"]))
        words.append(wds)
    total_words = sum(words)
    average_words_per_controlpart = total_words / (len(controlimpls) if len(controlimpls) > 0 else 1) # don't err if no controlimpls

    # For editing controls, we offer a list of evidence to attach to each control.
    evidence =  list(opencontrol.load_project_component_evidence(component))
    
    # Make a sorted list of controls --- the control catalog --- that the user can
    # draw from when adding new control implementations to the component.
    control_catalog = []
    for standard in standards.values():
      for control in standard["controls"].values():
          control = dict(control) # clone
          control['standard'] = {
            "id": standard["id"],
            "name": standard["name"],
          }
          control['family'] = standard['families'].get(control['family'])
          control_catalog.append(control)
    control_catalog.sort(key = lambda control : control['sort_key'])

    # Also make a sorted list of source files containing control implementation text.
    # In OpenControl, all controls are in component.yaml. But we support breaking the
    # controls out into separate files, and when adding a new control the user can
    # choose which file to put it in. In case no controls are in the component.yaml
    # file, ensure it is in the list, and make sure it comes first.
    import os.path
    source_files = set()
    source_files.add(os.path.join(component['path'], 'component.yaml'))
    for controlimpl in controlimpls:
      source_files.add(controlimpl['source_file'])
    source_files = sorted(source_files, key = lambda s : (not s.endswith("component.yaml"), s))

    # Done.
    return render_template(request, 'component.html',
                            project=project,
                            component=component,
                            control_families=control_families,
                            control_count=control_count,
                            control_part_count=control_part_counts,
                            total_words=total_words,
                            average_words_per_controlpart=average_words_per_controlpart,
                            evidence=evidence,
                            control_catalog=control_catalog, # used for creating a new control in the component
                            source_files=source_files, # used for creating a new control in the component
                          )

@route('/organizations/<organization>/projects/<project>/components/<component_name>/guide')
def component_guide(request, organization, project, component_name):
    """Show a component's guide."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load the component.
    try:
      component = opencontrol.load_project_component(project, component_name)
    except ValueError:
      return "Component `{}` in URL not found in project.".format(component_name)

    # Done.
    return render_template(request, 'component_guide.html',
                            project=project,
                            component=component,
                          )
                          
@route('/organizations/<organization>/projects/<project>/controls')
def controls(request, organization, project):
    """Show all of the controls for a project."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Get a list of all controls, by standard, combining both the controls listed
    # in the standards (and if listed in a certification, if present) as well as the
    # controls in use by the components, which may be different when the components
    # have non-standard controls or controls that are outside the control selection
    # specified by the certifications.

    # Load all of the standards used by this project so we have metadata for
    # controls that might be found.

    all_standards = opencontrol.load_project_standards(project)
    certified_controls = opencontrol.load_project_certified_controls(project)

    # Add in controls defined by the components and group them by standard.
    # Iterate through all components in the project...
    standards = { }
    for component in opencontrol.load_project_components(project):

        # Iterate through all control implementations across all components...
        for controlimpl in opencontrol.load_project_component_controls(component, all_standards):
            # The first time we see a standard, make a record for it.
            # If the control implementation is for an unknown standard, make a record for it
            # by using the "standard" information attached to this control. Otherwise pull
            # the name from the standards metadata.
            standard_key = controlimpl["standard"]["id"]
            if standard_key not in standards:
              standards.setdefault(standard_key, {
                  "name": all_standards[standard_key]["name"] # This is a standard we know about.
                          if standard_key in all_standards
                          else controlimpl["standard"]["name"],
              })

            # Make a "controls" dict to hold control implementations.
            control_key = controlimpl["control"]["id"]
            standards[standard_key].setdefault("controls", {})
            standards[standard_key]["controls"].setdefault(control_key, controlimpl["control"])

            # Count up the number of components that have an implementation for the control.
            # Note that we may come here more than once for a component because a component
            # can have multiple "control parts". So we use a set to track the (unique)
            # components.
            standards[standard_key]["controls"][control_key].setdefault("components", set())
            standards[standard_key]["controls"][control_key]["components"].add(component["id"])

    # Add in controls that don't have an implementation from standards we have
    # data for. If a certification is present for the standard, only include
    # controls in the certification. These controls won't have a 'url' field
    # so add it. Since the standards are loaded independently of projects, these
    # controls don't know what project we're doing right now and so could not pre-generate a URL.
    # Add a URL field now so that the template can generate links.
    from urllib.parse import quote_plus
    certified_standards = { standard_key for (standard_key, control_id) in certified_controls }
    for standard_key, standard in all_standards.items():
      for control in standard["controls"].values():
        # Include this control in the table if the standard does not have a certification
        # or if the control is in the certification.
        if standard_key not in certified_standards or (standard_key, control["id"]) in certified_controls:
          # Make a standard if we haven't seen it yet.
          standards.setdefault(standard_key, {
              "name": standard["name"],
              "controls": {},
          })

          # Add this control.
          standards[standard_key]["controls"].setdefault(control["id"], control)

          # Set its URL.
          control["url"] = "{}/controls/{}/{}".format(
            project["url"],
            quote_plus(standard["id"]),
            quote_plus(control["id"]),
          )

    # Make the standards a sorted list, and sort the controls within it. 'standards'
    # is a dict mapping standard IDs to dicts holding information about it. Going
    # forward we just need the dicts in order --- we no longer need a mapping. Same
    # for the list of controls within each standard.
    standards = list(standards.values())
    standards.sort(key = lambda standard : standard["name"])
    for standard in standards:
      standard["controls"] = list(standard["controls"].values())
      standard["controls"].sort(key = lambda control : control["sort_key"])

    # Prepare modify page message
    edit_dir = os.path.join(project["path"])
    print("edit_dir ", edit_dir)
    modify_msg = "To modify listed controls, edit content in the standards and certifications directories of project path: `{}`".format(edit_dir)

    # Done.
    return render_template(request, 'controls.html',
                            project=project,
                            standards=standards,
                            modify_msg=modify_msg
                          )

@route('/organizations/<organization>/projects/<project>/controls/<standard_key>/<control_key>/<format>')
def project_control_grid(request, organization, project, standard_key, control_key, format):
    """Show all of the components that contribute to this control."""

    # This route has two modes --- grid and combined --- which go off to separate templates.
    # But the data the two templates are showing is largely the same. So we have them
    # in a single route.
    if format not in ("grid", "combined"):
        raise ValueError()

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load the standards in use by this project.
    standards = opencontrol.load_project_standards(project)

    # Get the control metadata from the standard. Sometimes we're loading
    # a page for a control not mentioned in the standard but mentioned in
    # components. In that case, it will be missing from the standard and
    # we'll get its metadata later.
    try:
      control = standards[standard_key]["controls"][control_key]
    except KeyError:
      control = None

    # Scan all of the components for all contributions to this control.
    # Build up a list of relevant components and relevant control implementations
    # within that component.
    components = []
    for component in opencontrol.load_project_components(project):
        # Iterate over its controls...
        controlimpls = []
        for controlimpl in opencontrol.load_project_component_controls(component, standards):
            # Only look at control implementations for the control specified in the URL.
            # Even though we're looking at a single control, multiple control implementations
            # may match because there may be implementations for different *parts* of the
            # same control.
            if controlimpl["control"]["id"] == control_key:
                # This is a matching control --- save the control metadata
                # if we didn't get it from the standard.
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

    # For the 'grid' view...
    # Sort the components and the controls within each component so that we can display
    # them in columns for each component.
    components.sort(key = lambda component : component["component"]["name"])
    for component in components:
        component["controls"].sort(key = lambda controlimpl : controlimpl["sort_key"])

    # For the 'combined' view...
    # Sort the narratives by part first, then by component. We will have a single text area
    # that shows what this control will look like in a system security plan. Flatten the
    # list of control narratives and then sort.
    narratives = []
    for component in components:
        for controlimpl in component["controls"]:
          narratives.append({
            "part": controlimpl["control_part"],
            "component": component["component"],
            "text": controlimpl["narrative"],
          })
    narratives.sort(key = lambda narrative : ( narrative["part"] is None, narrative["part"], narrative["component"]["name"] ))

    # Add URL info to the control --- it might be missing if the metadata
    # came from the standard.
    from urllib.parse import quote_plus
    control["url"] = "{}/controls/{}/{}".format(
        project["url"],
        quote_plus(standard_key),
        quote_plus(control_key),
    )

    # Done.
    return render_template(request, 'control_{}.html'.format(format),
                            project=project,
                            standard=standards[standard_key],
                            control=control,
                            components=components,
                            narratives=narratives,
                          )

@route('/organizations/<organization>/projects/<project>/evidence')
def evidence(request, organization, project):
    """List evidence in the entire project."""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Load its components and sort them.
    components = list(opencontrol.load_project_components(project))
    components.sort(key = lambda component : component["name"])

    # Load all evidence.
    evidence = sum([
      list(opencontrol.load_project_component_evidence(component))
      for component in components
    ], [])

    # Show the project's components.
    return render_template(request, 'evidence_list.html',
                            project=project,
                            evidence=evidence)

@route('/organizations/<organization>/projects/<project>/ssp.<format>')
def ssp(request, organization, project, format):
    """Output the complete system security plan."""

    # Validate format.
    if format not in ("md",):
      raise ValueError()

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    # Construct the SSP.
    from .ssp import build_ssp
    return build_ssp(project, {})

#####################################################
# Routes for Creating and Updating Compliance Content
#####################################################

@route('/add-system', methods=["GET", "POST"])
def add_system(request):
    """Display and process form to create a system repository directory"""

    if request.method == "GET":
        # Get the default organization, system, and repo path for a new system.
        organization_name, system_name, description, repo_path =  opencontrol.get_new_system_defaults()
        error = None
    else:
        # Read the component name and path from the form fields.
        organization_name = request.form.get("organization-name", "").strip()
        system_name = request.form.get("system-name", "").strip()
        description = request.form.get("description", "").strip()
        repo_path = request.form.get("repo-path", "").strip()

        # Validate.
        if not organization_name:
            error = "The organization name cannot be empty."
        if not system_name:
            error = "The system name cannot be empty."
        if not description:
            error = "The description cannot be empty."
        elif not repo_path:
            error = "The repository path cannot be empty."
        # elif not opencontrol.validate_component_path(project, component_path):
        #     error = "Component path already exists or is not valid."
        else:
            # Validation OK. Create the system.
            created_repo_path = opencontrol.create_system(organization_name, system_name, description, repo_path)
            print(created_repo_path)
            return render_template(request, 'system_new.html',
                  system_name=system_name,
                  repo_path=created_repo_path,
                )

    # Show the form.
    return render_template(request, 'system_new.html',
                  default_organization_name=organization_name,
                  default_system_name=system_name,
                  default_description=description,
                  default_repo_path=repo_path,
                  error=error,
                )

@route('/organizations/<organization>/projects/<project>/add-component', methods=["GET", "POST"])
def add_component(request, organization, project):
    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    if request.method == "GET":
        # Get the default name and path for a new component.
        component_name, component_path = opencontrol.get_new_component_defaults(project)
        error = None
    else:
        # Read the component name and path from the form fields.
        component_name = request.form.get("component-name", "").strip()
        component_path = request.form.get("component-path", "").strip()

        # Validate.
        if not component_name:
            error = "The name cannot be empty."
        elif not component_path:
            error = "The path cannot be empty."
        elif not opencontrol.validate_component_path(project, component_path):
            error = "Component path already exists or is not valid."
        else:
            # Validation OK. Create the component.
            component = opencontrol.create_component(project, component_path, component_name)
            print(component)
            return redirect(request, component["url"])

    # Show the form.
    return render_template(request, 'component_new.html',
                  project=project,
                  default_component_name=component_name,
                  default_component_path=component_path,
                  error=error,
                )

@route('/update-control', methods=['POST'])
def update_control(request):
    """Update a control narrative or other user-editable compliance data."""

    # Load the project and the component being edited.
    project = load_project(request.form["organization"], request.form["project"])
    component = opencontrol.load_project_component(project, request.form["component"])

    # Validate.
    if not request.form.get("narrative", "").strip():
      return "Narrative cannot be empty."

    # Is this an update or the addition of a new control?
    mode = request.form["mode"] # "update" or "new"

    # Iterate through the controls until a matching one is found.
    # We need the existing control so we can update it and then pass it back to
    # update_component_control.
    for controlimpl in opencontrol.load_project_component_controls(component, {}):
      if controlimpl["standard"]["id"] == request.form["standard"] \
       and controlimpl["control"]["id"] == request.form["control"] \
       and controlimpl.get("control_part") == (request.form.get("control_part") or None) \
       :
       # We found a match.
       if mode == "new":
         # Don't obliterate an existing record when the user is trying to create a new one.
         return "This control already exists."

       # Update the control's metadata.
       #controlimpl["summary"] = request.form.get("summary", "")
       controlimpl["narrative"] = request.form.get("narrative", "")
       controlimpl["implementation_status"] = request.form.get("implementation_status", "")
       if opencontrol.update_component_control(controlimpl):
         # If the control was updated, return it back to the user
         # as JSON.
         return send_json_response(request, controlimpl)

    # The control was not found in the data files.
    if mode == "update":
      return "Control being updated is missing from the project."

    # Construct a new controlimpl data structure.
    controlimpl = {
      "standard": {
        "id": request.form["standard"],
      },
      "control": {
        "id": request.form["control"],
      },
      "control_part": request.form.get("control_part"),
      "narrative": request.form.get("narrative", ""),
      "implementation_status": request.form.get("implementation_status", ""),
      "source_file": request.form.get("source_file", ""),
    }

    # Save it.
    opencontrol.add_component_control(component, controlimpl)

    # Return it back to the client.
    return send_json_response(request, controlimpl)

#####################################################
# Routes for Customization
#####################################################

@route('/organizations/<organization>/projects/<project>/_extensions/hypergrc/static/css/repo.css')
def custom_css(request, organization, project):
    """Set custom css settings"""

    # Load the project.
    try:
      project = load_project(organization, project)
    except ValueError:
      return "Organization `{}` project `{}` in URL not found.".format(organization, project)

    doc = os.path.join(project["path"], "_extensions", "hypergrc","static", "css", "repo.css")

    # Make sure this file exists and TODO: has no relative paths or goes to system directory
    # We aren't too worried about security when user is running on their own workstation.
    if os.path.isfile(doc):
      try:
        with open(doc, 'r') as f:
          data = f.read()
          return data
      except Exception as e:
        import traceback
        traceback.print_exc()
        request.send_response(500)
        request.send_header("Content-Type", "text/plain; charset=UTF-8")
        request.end_headers()
        request.wfile.write(b"Ooops! Something went wrong.")
        return
    else:
      print("file not found {}".format(doc))
      request.send_response(404)
      request.send_header("Content-Type", "text/plain; charset=UTF-8")
      request.end_headers()
      request.wfile.write(b"file not found")
      return
