# Routines for loading OpenControl data.

import os.path
import re
import shutil
from urllib.parse import quote_plus
from collections import OrderedDict

import rtyaml

def load_opencontrol_yaml(fn, schema_type, expected_schema_versions):
    # Load a YAML file holding a mapping, and check that its schema_version is recognized.
    # Specify the encoding explicitly because YAML files are always(?) UTF-8 encoded and
    # that may not be the system default encoding (e.g. on Windows the default is based on
    # the system locale). schema_type holds e.g. "system", "standards", or "component," a
    # string to display to the user describing the type of file expected in error messages.
    try:
        with open(fn, encoding="utf8") as f:
            try:
                opencontrol = rtyaml.load(f)
            except Exception as e:
                raise ValueError("OpenControl {} file {} has invalid data (is not valid YAML: {}).".format(
                    schema_type,
                    fn,
                    str(e) ))
            if not isinstance(opencontrol, dict):
                raise ValueError("OpenControl {} file {} has invalid data (should be a mapping, is a {}).".format(
                    schema_type,
                    fn,
                    type(opencontrol) ))
            if expected_schema_versions and opencontrol.get("schema_version") not in expected_schema_versions:
                raise ValueError("Don't know how to read OpenControl {} file {} which has unsupported schema_version {}.".format(
                    schema_type,
                    fn,
                    repr(opencontrol.get("schema_version"))))
            return opencontrol
    except IOError as e:
        raise ValueError("OpenControl {} file {} could not be loaded: {}.".format(
            schema_type,
            fn,
            str(e) ))

# This is a utility function to generate a short hex hash for
# text.
def short_hash(s, len=6):
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(s.encode("utf8"))
    return hasher.hexdigest()[:len]

def load_project_from_path(project_dir):
    # Open a project at the given directory. An "opencontrol.yaml" file must
    # exist in the directory.

    # Read the opencontrol file for the system name, description, etc.
    # Check that the schema_version is recognized.
    fn = os.path.join(project_dir, "opencontrol.yaml")
    opencontrol = load_opencontrol_yaml(fn, "system", ("1.0.0",))

    # Read OpenControl system metadata.
    # If there is no name, fall back to the project directory name.
    name = opencontrol.get("name") or os.path.splitext(os.path.basename(os.path.normpath(project_dir)))[0]
    description = opencontrol.get("metadata", {}).get("description")

    # Read hyperGRC extensions to the metadata.
    # Create an "organization_id" that we can put into URLs. Use the organization's abbreviation,
    # but add to it a hash of the full organization name so that in the unlikely case that
    # two organizations share the same abbreviation, we still assign unique IDs to them.
    organization_name = opencontrol.get("metadata", {}).get("organization", {}).get("name", "No Organization")
    organization_abbrev = opencontrol.get("metadata", {}).get("organization", {}).get("abbreviation", organization_name)
    organization_id = organization_abbrev[0:12] + "-" + short_hash(organization_name)
    source_repository = opencontrol.get("metadata", {}).get("repository")

    # Create a "project_id" that we can put into URLs. Since we don't have a database or
    # primary keys, we have to make something up. Start with the project's name, but
    # truncated so that we don't have unnecessarily long URLs. Add to it a hash of the
    # directory path containing the project so that in the unlikely case that two
    # projects share the same first 12 characters of the project name, we still assign
    # unique IDs to them.
    project_id = name[0:12] + "-" + short_hash(fn)

    # Read the "authorization_id" that an organization assigns to the project for
    # enterprise tracking purposes.
    authorization_id = opencontrol.get("metadata", {}).get("authorization_id", "Unassigned")

    # This is the data structure that we use throughout the application to represent projects.
    return {
        # An identifier for the project, unique within an organization. This is used to
        # map URLs to projects --- it's placed in URLs like a slug.
        "id": project_id,

        # The organization the project is a part of.
        "organization": {
            # A unique identifier for the organization, which is placed in URLs like a slug.
            "id": organization_id,

            # Organization name and abbreviation.
            "name": organization_name,
            "abbreviation": organization_abbrev,
        },

        # Title, description, and other user-visible metadata for the project.
        "title": name,
        "description": description,
        "source_repository": source_repository,
        "authorization_id": authorization_id,

        # Local disk path to the OpenControl root directory.
        "path": project_dir,

        # URL for the project in hyperGRC.
        "url": "/organizations/{}/projects/{}".format(
            quote_plus(organization_id),
            quote_plus(project_id)
        ),
    }

def load_project_components(project):
    # Get a project's components, returning a generator that yields a data
    # structure for each component holding its metadata.

    # Read the project's opencontrol.yaml file for paths to components.
    fn1 = os.path.join(project["path"], "opencontrol.yaml")
    opencontrol = load_opencontrol_yaml(fn1, "system", ("1.0.0",))
    component_paths = opencontrol.get("components", [])

    # Typically all components are stored in a 'components' directory. Find
    # that directory.
    try:
        basepath = os.path.commonpath(component_paths)
    except:
        basepath = None

    # Read each component's component.yaml file, and return a generator over
    # components.
    for component_path in component_paths:
        # Load the component.yaml file and check that the schema_version of each component is recognized.
        fn2 = os.path.join(project["path"], component_path, "component.yaml")
        component = load_opencontrol_yaml(fn2, "component", ("3.0.0",))

        # Get the component name. If there is no name, fall back to the directory name.
        name = component.get("name") or os.path.splitext(os.path.basename(os.path.normpath(component_path)))[0]

        # Create a "component_id" that we can put into URLs. Since we don't have a database or
        # primary keys, we have to make something up. It must be unique within the project and
        # should be short and human readable.
        #
        # The only guaranteed way to be unique is to use the local path to the component, but this
        # is often components/ComponentName, so chop off the basepath if one exists so we just
        # have ComponentName. Note that this means the id isn't stable --- if components are added
        # or removed, the basepath may change, changing all of the component IDs.
        component_id = component_path
        if basepath:
            component_id = os.path.relpath(component_id, start=basepath)

        if not component_id or not component_id.strip("./\\"):
            # The component directory is the only one or there is no relative path to the base
            # path (i.e. component_id was empty or only dots and slashes), so try again with a
            # different strategy. 
            # Start with the component's name, but
            # truncated so that we don't have unnecessarily long URLs. Add to it a hash of the
            # directory path containing the component so that in the unlikely case that two
            # components share the same first 12 characters of their names, we still assign
            # unique IDs to them.
            component_id = name[0:12] + "-" + short_hash(component_path)

        # This is the data structure that we use throughout the application to represent
        # a component.
        yield {
            # An identifier for the component, unique within the project it is contained in.
            # This is used to  map URLs to components --- it's placed in URLs like a slug.
            "id": component_id,

            # The project the component is contained in.
            "project": project,

            # User-visible metadata for the component.
            "name": name,

            # Local disk path to the directory containing the component.yaml file.
            "path": os.path.normpath(os.path.join(project["path"], component_path)),

            # URL for the component in hyperGRC.
            "url": project["url"] + "/components/" + quote_plus(component_id),
        }

def load_project_component(project, component_id):
    # Load a particular component in the project by its id.
    # TODO: We currently scan all components until we find the
    # matching one. We should add some caching to speed this up.
    for component in load_project_components(project):
        if component["id"] == component_id:
            return component
    raise ValueError("Component {} does not exist in project {}.".format(component_id, project["id"]))

# Helper routines for sorting controls correctly. i.e. AC-2 precedes AC-10.
def intify(s):
    # If s looks like an integer, return it as an integer. Otherwise return
    # it as a string.
    try:
        return int(s)
    except ValueError:
        return s
def make_control_number_sort_key(s):
    # Split up s into parts that look like integers and parts that don't,
    # and parse the integers. Return a tuple of the parts. Tuples are
    # ordered by ordering their corresponding elements, so if corresponding
    # elements are integers, they'll be ordered numerically, which will
    # put e.g. 2 before 10, even though 10 precedes 2 lexicographically.
    import re
    return tuple(intify(part) for part in re.split(r"(\d+)", s or ""))

def load_project_standards(project):
    # Return a mapping from standard_keys to parsed standard data.

    standards = { }

    # Open the OpenControl system file (the project) and check that its schema_version
    # is something we recognize...
    fn1 = os.path.join(project["path"], "opencontrol.yaml")
    system_opencontrol = load_opencontrol_yaml(fn1, "system", ("1.0.0",))

    # The system has a list of standards. Load all of them.
    for standard_fn in system_opencontrol["standards"]:
        # The path is relative to the opencontrol.yaml directory.
        standard_fn = os.path.join(project["path"], standard_fn)
        
        # Each standard file contains a standard. The schema version for the
        # standard isn't specified, so we'll assume it's the current schema
        # version.
        load_standard(standard_fn, "1.0.0", standards)

    return standards

def load_standard(fn, schema_version, standards):
    # Read the file..
    standard_opencontrol = load_opencontrol_yaml(fn, "standard", None) # no schema_version is present in this file

    # The 'key' of a standard is set in its 'name' field, which is weird, but so it is.
    # If there's no name --- it's probably required, but just in case --- fall back to
    # the filename without its extension.
    standard_key = standard_opencontrol.get('name') \
        or os.path.splitext(os.path.basename(os.path.normpath(fn3)))[0]

    # Create a dict holding information about the standard and the controls
    # within the standard.
    standards[standard_key] = {
        # A unique identifier for the standard. This is used to map URLs to standards --- it's placed in URLs like a slug.
        "id": standard_key,

        # The display name of the standard.
        "name": standard_opencontrol["name"],

        # A mapping of control IDs to controls defined by this standard.
        "controls": {
            control_number: {
                # This data structure must match control structure in load_project_component_controls, except the URL,
                # which is project-specific, so we can't generate it here. See load_project_component_controls for details.
                "id": control_number,
                "sort_key": (standard_key, make_control_number_sort_key(control_number)),
                "number": control_number,
                "name": control_data["name"],
                "family": control_data["family"],
                "description": control_data["description"],
            }
            for control_number, control_data in standard_opencontrol.items()
            if isinstance(control_data, dict) # not the "name: " key
               and control_data.get('type') is None # skip the family names that we put in the file but aren't in the OpenControl standard
        },

        # A mapping of family IDs to metadata about control families. This is non-conformant with OpenControl
        # but it is useful!
        "families": {
            family_id: {
                # This is the data structure we use throughout the application for control families.

                # A unique identifier for the control family, unique within the standard.
                # These IDs
                "id": family_id,

                # A string that helps with ordering control families logically for display purposes.
                "sort_key": family_id,

                # The control family's display strings.
                "number": family_id,
                "name": family_data["name"],
                "abbrev": family_id,
            }
            for family_id, family_data in standard_opencontrol.items()
            if isinstance(family_data, dict) # not the "name: " key
               and family_data.get('type') == 'family' # not in OpenControl --- we've added family names to the standard
        },
    }
                
def load_project_certified_controls(project):
    # Return a set of (standard_id, control_id) tuples for controls that are included
    # in any "certification" attached to the system. A certification is a list of controls
    # the user cares about for the system, i.e. a control selection.

    certified_controls = set()

    # Open the OpenControl system file (the project) and check that its schema_version
    # is something we recognize...
    fn1 = os.path.join(project["path"], "opencontrol.yaml")
    system_opencontrol = load_opencontrol_yaml(fn1, "system", ("1.0.0",))

    # The system optionally has a list of certifications. Load all of them.
    for certification_fn in system_opencontrol.get("certifications", []):
        # Construct the file name.
        fn3 = os.path.join(project["path"], certification_fn)

        # Read the file..
        certification_opencontrol = load_opencontrol_yaml(fn3, "certification", None) # no schema_version is present in this file

        # Iterate over each standard...
        for standard_id, controls in certification_opencontrol.get("standards", {}).items():
            for control_id in controls:
                certified_controls.add( (standard_id, control_id) )

    return certified_controls

def get_matched_control(control_id, standard):
    # Sometimes control IDs refer to subparts of controls, e.g. AC-2 (a)
    # or non-standard supplemental citations, e.g. AC-2 (DHS 1.2.3). If the
    # control isn't in the standard exactly, back off at non-word characters
    # like parens and spaces until we find a matching control.
    control_parts = re.split(r"(\s+|[^\w\s]+)", control_id)
    for i in reversed(range(len(control_parts))):
      test_id = "".join(control_parts[:i+1])
      if test_id in standard["controls"]:
        return test_id
    # Control isn't found at all. Return the original control_id unchanged.
    return control_id

def transform_list(array, source_file, file_loader, transformer):
    # Loop over the elements.
    for item in array:
        # If an entry is a string rather than a dict, then it names a file
        # that we should read that contains more items of the same type.
        if isinstance(item, str):
            # Construct the path to the file, which is relative to the file
            # it is listed in.
            fn = os.path.join(os.path.dirname(source_file), item)

            # Parse it.
            inner_file = file_loader(fn)
            yield from transform_list(inner_file, fn, file_loader, transformer)
        else:
            # This record holds an item to transform.
            yield from transformer(item, source_file)

def load_project_component_controls(component, standards):
    # Return a generator over all of the controls implemented by the component.
    
    # Construct the filename for the component.yaml file. The component already
    # knows what directory it is in.
    fn = os.path.join(component["path"], "component.yaml")
    component_opencontrol = load_opencontrol_yaml(fn, "component", ("3.0.0",))

    # Because the component.yaml file is in a sense recursive --- not actually in OpenControl
    # but in the extended schema that we support --- this function is a helper function
    # that reads component files. It returns a generator that yields the controls implemented
    # by the component listed in a particular source file.
    def file_loader(fn):
        return load_opencontrol_yaml(fn, "component", None).get("satisfies", [])
    def transformer(control, source_file):
        # This record holds a control number and narrative.
        #
        # Actually it holds a list of narratives for one or more control *parts*.
        # A part is like "part a", "part b", etc. We return each separately.
        # So, an implemented "control" actually means a control *part*.

        # Create basic metadata for the control only based on what's in the
        # component. This data structure is used throughout this application
        # to represent control implementations within components.
        control_metadata = {
            # The component implementing the control.
            "component": component,

            # The standard that the control is a part of. See the data structure defined for
            # standards in load_project_standards. This is a stub --- we augment it with
            # data from load_project_standards below.
            "standard": {
                "id": control["standard_key"],
                "name": control["standard_key"],
            },

            # The control family that the control is a part of. See the data structure defined for
            # control families in load_project_standards. This is a stub --- we augment it with
            # data from load_project_standards below.
            "family": {
                "id": control["control_key"].split("-")[0],
                "abbrev": control["control_key"].split("-")[0],
                "name": control["control_key"].split("-")[0],
                "sort_key": control["control_key"].split("-")[0],
            },

            # The control being implemented.  Must match control structure in load_project_standards.
            # This is a stub --- we augment it with data from load_project_standards below if the
            # control is found in a standard.
            #
            # The only difference is that we add a 'url' key here to the page within this *project*
            # for viewing everything related to this control.
            "control": {
                "id": control["control_key"], # matches how the control is put in the URL
                "sort_key": (control["standard_key"], make_control_number_sort_key(control["control_key"])),
                "number": control["control_key"],
                "name": control.get("name", control["control_key"]), # not in OpenControl spec
                "url": "{}/controls/{}/{}".format(
                    component["project"]["url"],
                    quote_plus(control["standard_key"]),
                    quote_plus(control["control_key"]),
                )
            },

            # Evidence keys.
            "evidence": [
                item["verification_key"]
                for item in control.get("covered_by", [])
                if item.get("component_key") is None # skip if evidence is defined elsewhere because we don't support that
            ],

            # The local path to the YAML file containing this data --- which we use for finding
            # the file we need when we want to edit the control implementation.
            "source_file": os.path.normpath(source_file),
        }

        # Augment the control information from the standards if the control is found in the
        # standards. Is the standard one we know?
        if control["standard_key"] in standards:
            standard = standards[control["standard_key"]]
            control_metadata["standard"]["name"] = standard["name"]

            # If the control is in the standard, add its info also.
            if control["control_key"] in standard["controls"]:
                control_metadata["control"].update(standard["controls"][control["control_key"]])

            # If this is a nonstandard citation to a control, add some of the parent control's info.
            elif get_matched_control(control["control_key"], standard) in standard["controls"]:
                matched_control = standard["controls"][get_matched_control(control["control_key"], standard)]
                if not control_metadata["control"].get("name"):
                  control_metadata["control"]["name"] = matched_control["name"]
                if not control_metadata["control"].get("family"):
                  control_metadata["control"]["family"] = matched_control["family"]
                if not control_metadata["control"].get("description"):
                  control_metadata["control"]["description"] = matched_control["description"]
                
            # If the control's family is in the standard, add its info also.
            if control_metadata["control"].get("family") in standard["families"]:
                control_metadata["family"].update(standard["families"][control_metadata["control"]["family"]])
            
        # For each narrative part, make a copy of the control metadata
        # so far, add the control part, and return the combined metadata.
        #
        # Note that we're reading "implementation_status" from the narrative
        # part. This is non-conformant with OpenControl which has a single
        # implementation_statuses field on the *control*, for all control
        # parts, which are are ignoring so far in hyperGRC.
        import copy
        for narrative_part in control.get("narrative", []):
            controlimpl = dict(control_metadata)
            controlimpl.update({
                "control_part": narrative_part.get("key"),
                "sort_key": (controlimpl["control"]["sort_key"], make_control_number_sort_key(narrative_part.get("key"))),
                "narrative": narrative_part["text"],
                "implementation_status": narrative_part.get("implementation_status") or "",
            })
            yield controlimpl

    # Yield the controls in the "satisfies" key.
    yield from transform_list(component_opencontrol.get("satisfies", []), fn, file_loader=file_loader, transformer=transformer)

def load_project_component_evidence(component):
    # Return a generator over all of the evidence available for the component.
    
    # Construct the filename for the component.yaml file. The component already
    # knows what directory it is in.
    fn = os.path.join(component["path"], "component.yaml")
    component_opencontrol = load_opencontrol_yaml(fn, "component", ("3.0.0",))

    # Because the component.yaml file is in a sense recursive --- not actually in OpenControl
    # but in the extended schema that we support --- this function is a helper function
    # that reads component files. It returns a generator that yields the evidence.
    def file_loader(fn):
        return load_opencontrol_yaml(fn, "component", None).get("verifications", [])
    def transformer(verification, source_file):
        # This record holds a "verification," which is what OpenControl calls evidence.
        # As with our other data structures, return the actual path to the evidence, not
        # a path relative to the directory in which the evidence is defined. Also store
        # the component and actual file this evidence was defined in.
        yield {
            "key": verification["key"],
            "name": verification.get("name") or verification["key"],
            "path": os.path.join(component["path"], verification["path"]),
            "type": verification.get("type"),
            "component": component,
            "source_file": source_file,
        }

    # Yield the evidence in the "verifications" key.
    yield from transform_list(component_opencontrol.get("verifications", []), fn, file_loader=file_loader, transformer=transformer)

def get_new_system_defaults():

    organization_name = "My Organization"
    system_name = "New System"
    description = "Our shiny new IT system"
    repo_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", system_name.lower().replace(" ","_")))
    return organization_name, system_name, description, repo_path

def get_new_config(system_name="MySystem", organization_name="MyOrg", description="My shiny new IT system"):
    """Create the config file (opencontrol.yaml) data and return values"""
  
    cfg_str = """schema_version: 1.0.0
name: AgencyApp
metadata:
  authorization_id: ~
  description: Imaginary application for to show faked control narratives.
  organization:
    name: Department of Sobriety
    abbreviation: DOS
  repository: TBD
components: []
standards:
- ./standards/NIST-SP-800-53-rev4.yaml
certifications:
- ./certifications/fisma-low-impact.yaml
"""

    # read default opencontrol.yaml into object
    cfg = rtyaml.load(cfg_str)
    # customize values
    cfg["name"] = system_name
    cfg["metadata"]["organization"]["name"] = organization_name
    cfg["metadata"]["description"] = description
    cfg["metadata"]["organization"]["abbreviation"] = "".join([word[0].upper() for word in organization_name.split(" ")])

    return cfg

def create_system(organization_name, system_name, description, repo_path):
    """Create a new system and its repository and return path to repo on file system"""

    # make repo directory
    if os.path.exists(repo_path):
       print("Path {} exists".format(repo_path))
    else:
       os.makedirs(repo_path)
       print("Path {} created".format(repo_path))

    # get default opencontrol.yaml configuration
    cfg = get_new_config(system_name, organization_name, description)
    print(cfg["name"])
    print("\npreparing system dir: {}".format(system_name))

    # create various directories
    os.makedirs(os.path.join(repo_path, "components"))
    os.makedirs(os.path.join(repo_path, "standards"))
    os.makedirs(os.path.join(repo_path, "certifications"))
    os.makedirs(os.path.join(repo_path, "outputs"))

    # create opencontrol.yaml config file
    with open(os.path.join(repo_path, "opencontrol.yaml"), 'w') as outfile:
        outfile.write(rtyaml.dump(cfg))
        print("wrote file: {}\n".format(os.path.join(repo_path, "opencontrol.yaml")))

    # populate reference directories from reference
    shutil.copyfile(os.path.join("ref", "standards", "NIST-SP-800-53-rev4.yaml"), os.path.join(repo_path, "standards", "NIST-SP-800-53-rev4.yaml"))
    print("wrote file: {}\n".format(os.path.join(repo_path, "standards", "NIST-SP-800-53-rev4.yaml")))
    shutil.copyfile(os.path.join("ref", "standards", "opencontrol.yaml"), os.path.join(repo_path, "standards", "opencontrol.yaml"))
    print("wrote file: {}\n".format(os.path.join(repo_path, "standards", "opencontrol.yaml")))
    # shutil.copyfile(os.path.join("ref", "standards", "hipaa-draft.yaml"), os.path.join(repo_path, cfg["standards"][0], "hipaa-draft.yaml"))
    # print("wrote file: {}\n".format(os.path.join(repo_path, cfg["standards"][0], "hipaa-draft.yaml")))
    shutil.copyfile(os.path.join("ref", "certifications", "fisma-low-impact.yaml"), os.path.join(repo_path, "certifications", "fisma-low-impact.yaml"))
    print("wrote file: {}\n".format(os.path.join(repo_path, "certifications", "fisma-low-impact.yaml")))

    # make stub README.md file
    with open(os.path.join(repo_path, "README.md"), 'w') as outfile:
        outfile.write("Machine readable representation of 800-53 control implementations for {}.\n\n# Notes\n\n".format(system_name))
        print("wrote file: {}\n".format(os.path.join(repo_path, "README.md")))

    # append repo path to repos.conf
    # TODO - read and clean repos.conf and then append;use clean_text function?
    with open("repos.conf", 'a') as outfile:
        outfile.write("\n{}".format(repo_path))
        print("appended {} to file: repos.conf\n".format(repo_path))

    # Now return the path to the repository
    return repo_path

def get_new_component_defaults(project):
    # What is a good name and path for a new component?

    # For the path, get the common base path of existing components. If there isn't a common
    # path make a new good path. The path is relative to the project path.
    existing_components = list(load_project_components(project))
    component_paths = [ os.path.relpath(component["path"], start=project["path"]) for component in existing_components  ]
    try:
        basepath = os.path.commonpath(component_paths)
    except:
        basepath = None
    if not basepath or basepath.startswith(".") or basepath.startswith("/"): # ensure the path is relative
        basepath = "components"

    # Add to it a new component directory name that isn't an existing directory.
    i = 1
    while True:
        component_name = "New Component {}".format(i)
        component_path = os.path.join(basepath, component_name.replace(" ", ""))
        if not os.path.exists(component_path):
            break
        i += 1

    return component_name, component_path

def validate_component_path(project, component_path):
    d = os.path.join(project["path"], component_path)
    if os.path.exists(d):
        return False
    return True

def create_component(project, component_path, component_name):
    # Create a new OpenControl component.

    # Create the stub data structure.
    component_opencontrol = OrderedDict()
    component_opencontrol['schema_version'] = '3.0.0'
    component_opencontrol['name'] = component_name

    # Create the path.
    os.makedirs(os.path.join(project['path'], component_path))

    # Write the component.yaml file.
    with open(os.path.join(project['path'], component_path, 'component.yaml'), 'w', encoding="utf8") as f:
        f.write(rtyaml.dump(component_opencontrol))

    # Add the path to the project's opencontrol.yaml file.
    with open(os.path.join(project["path"], 'opencontrol.yaml'), "r+", encoding="utf8") as f:
        # Parse the content.
        data = rtyaml.load(f)

        # Create the "components" array if it does not exist.
        if not isinstance(data.get("components"), list):
            data["components"] = []

        # Append the new component path.
        data["components"].append(component_path)

        # Write back out to the data files.
        f.seek(0);
        f.truncate()
        rtyaml.dump(data, f)

    # Read the component back and return it.
    for component in load_project_components(project):
        if component["path"] == os.path.join(project['path'], component_path):
            return component

    raise ValueError("Component {} does not exist in project {} even after creating it.".format(component_path, project["id"]))

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

def update_component_control(controlimpl):
    # The control is defined in the component.yaml file given in controlimpl["source_file"].
    # Open that file for editing, find the control record, update it, and return.
    with open(controlimpl["source_file"], "r+", encoding="utf8") as f:
        # Parse the content.
        data = rtyaml.load(f)

        # Look for a matching control entry.
        for control in data["satisfies"]:
            # Skip over entries that are strings -- they hold (OpenControl non-conformant) filenames.
            if not isinstance(control, dict):
                continue

            if control["standard_key"] == controlimpl["standard"]["id"] \
              and control["control_key"] == controlimpl["control"]["id"]:

                for narrative_part in control.get("narrative", []):
                    if narrative_part.get("key") == controlimpl.get("control_part"):
                        
                        # Found the right entry. Update the fields.

                        narrative_part["text"] = clean_text(controlimpl["narrative"])

                        # Store implementation_status here. In OpenControl there is
                        # a `implementation_statuses` on the control. But our data
                        # model has a single implementation_status per control *part*.
                        # If the implementation status is cleared, remove the key.
                        if controlimpl["implementation_status"]:
                            narrative_part["implementation_status"] = clean_text(controlimpl["implementation_status"])
                        elif "implementation_status" in narrative_part:
                            del narrative_part["implementation_status"]

                        # Write back out to the data files.
                        f.seek(0);
                        f.truncate()
                        rtyaml.dump(data, f)

                        return True

    return False

def add_component_control(component, controlimpl):
    # Append the control to the component. controlimpl must have
    # a source_file key that is present in the component.yaml
    # file or is the component.yaml file itself.

    # Open the source file.
    with open(controlimpl["source_file"], "r+", encoding="utf8") as f:
        # Parse the content.
        data = rtyaml.load(f)

        # Create the 'satisfies' key if it doesn't exist.
        data.setdefault("satisfies", [])

        # Although we're adding it, the control record may already exist.
        # In that case, we're adding a new narrative part. First, see if
        # the control record already exists.
        for control in data["satisfies"]:
            # Skip over entries that are strings -- they hold (OpenControl non-conformant) filenames.
            if not isinstance(control, dict):
                continue
            if control["standard_key"] == controlimpl["standard"]["id"] \
              and control["control_key"] == controlimpl["control"]["id"]:

                # Check that the control_part doesn't yet exist.
                for narrative_part in control.get("narrative", []):
                    if narrative_part.get("key") == controlimpl.get("control_part"):
                        return "The control part already exists."

                # Ok we found a match.
                break
        
        else:
            # Create a new control record.
            control = OrderedDict([
                ("standard_key", controlimpl["standard"]["id"]),
                ("control_key", controlimpl["control"]["id"]),
                ("narrative", []),
            ])
            data["satisfies"].append(control)

        # Append a new narrative part.
        narrative_part = OrderedDict()
        if (controlimpl.get("control_part") or "").strip():
            narrative_part['key'] = clean_text(controlimpl["control_part"])
        narrative_part["text"] = clean_text(controlimpl["narrative"])

        # Store implementation_status here. In OpenControl there is
        # a `implementation_statuses` on the control. But our data
        # model has a single implementation_status per control *part*.
        # If the implementation status is cleared, remove the key.
        if controlimpl["implementation_status"]:
            narrative_part["implementation_status"] = clean_text(controlimpl["implementation_status"])
        elif "implementation_status" in narrative_part:
            del narrative_part["implementation_status"]

        control["narrative"].append(narrative_part)

        # Write back out to the data files.
        f.seek(0);
        f.truncate()
        rtyaml.dump(data, f)

        return "OK"

