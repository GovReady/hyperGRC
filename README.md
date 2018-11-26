hyperGRC is a lightweight tool for managing component-to-control mappings for Compliance As Code written in Python for Python 3.

hyperGRC provides a very friendly, kanban-style GUI for reading and writing YAML files representing control implementation content associated with system components.

The plan is for hyperGRC to support multiple underlying data formats. The goal is to make the world's most loved and hyper-useful IT GRC tool.


# How It Works

hyperGRC is a web application for workstation or server that reads a `.govready` or `opencontrol.yaml` and presents a GUI environment for editing system compliance based on component security plans.

hyperGRC reads the `.govready` configuration file, then reads the YAML files describing the controls provided by components, to generate web pages for making it easier to read and write reusable control implementation content.


# The .hypergrc_repos file

Copy the `.hypergrc_repos_example` file to your `.hypergrc_repos` file and edit to list the paths to `.govready` files in the compliance as code repositories on your workstation. List the paths one per line. Note that your local `.hypergrc_repos` file is gitignored. 

hyperGRC reads the `.hypergc_repos` file on start up for a list of local compliance as code to navigate between. This list will be displayed on hyperGRC's home page.

Example `.hypergrc_repos` file:

`/codedata/code/civicactions/Dept-of-Sobriety/dos.gov/.govready`
`/codedata/code/civicactions/democracy/citizenapp/.govready`

The paths in the `.hypergrc_repos` file can be given as command-line arguments instead, and the `.hypergrc_repos` file itself can be specified explicitly on the command-line by prefixing it with an `@` sign, as in `@.hypergrc_repos`.

# The .govready file

Here's a sample .govready file for each repo:

```
hgrc_version: 0.3.0
mode: local workstation
standard_controls_dir: standards
certifications_dir: certifications
components_dir: components
organization:
  name: Department of Sobriety
system:
  name: DOS.gov
  src_repo: https://git.vendorco.net/dos/ssp-csv-to-yaml
  primary_standard: 800-53r4
  primary_certification: FISMA Low Impact
standards:
- standard: 800-53r4
  standard_file: nist-800-53-rev4.yaml
certifications:
- name: FISMA Low Impact
  certification_file: fisma-low-impact.yaml
components:
- name: VendorCo
  directory: VendorCo
- name: Drupal
  directory: Drupal
- name: Department of Sobriety
  directory: DOS
- name: Acquia-ACE
  directory: Acquia-ACE
- name: AWS
  directory: AWS
documents:
- name: outputs
  directory: outputs
  description: Default output directory
team:
- name: Jane Doe
  role: ISSO
  phone: (202) 555-5555
  email: jane.doe@dos.gov
users:
- name: Anonymous (workstation mode)
```


# Supported Data Formats:

### OpenControl

(Coming soon - content to be added)

### "Fen" Format

```
name: Acquia-ACE
family: ACCESS CONTROL
documentation_complete: false
schema_version: 3.0.0
satisfies:
- control_key: AC-01
  control_key_part: a
  control_name: ACCESS CONTROL POLICY AND PROCEDURES
  standard_key: NIST-800-53
  covered_by: []
  security_control_type: Hybrid
  implementation_status: In Place
  narrative: >
    The system partially inherits this control from the FedRAMP Provisional ATO granted
    to the Acquia Cloud Cloud Service Provider dated 17 March 2016 and documented
    in their SSP v1.16 18 September 2018.
  summary: Partially inherited from ACE and AWS (FedRAMP).
  responsibile_entities:
  - entity: Acquia-ACE
  - entity: System Owner
- control_key: AC-01
  control_key_part: b
  control_name: ACCESS CONTROL POLICY AND PROCEDURES
  standard_key: NIST-800-53
  covered_by: []
  security_control_type: Hybrid
  implementation_status: In Place
  narrative: >
    The system partially inherits this control from the FedRAMP Provisional ATO granted
    to the Acquia Cloud Cloud Service Provider dated 17 March 2016 and documented
    in their SSP v1.16 18 September 2018.
  summary: Partially inherited from ACE and AWS (FedRAMP).
  responsibile_entities:
  - entity: Acquia-ACE
  - entity: System Owner
```

### GovReady Compliance Apps

(Coming soon - content to be added)


### GovReady SSP Parser

(Working - content to be added)

# Launching

### Installing virtualenv

```
cd hypergrc
virtualenv venv -ppython3
source venv/bin/activate
pip install -r requirements.txt
```

### Fetching standards data

```
mkdir standards
curl https://raw.githubusercontent.com/GovReady/NIST-800-53r4-Standards/master/NIST-800-53r4.yaml > standards/nist-800-53-rev4.yaml
```

### Adding components

To use existing component YAML files, cplace them in files named like so inside the target system repo (not hyperGRC repo):

```
components/Component1/controlset1.yaml
components/Component1/controlset2.yaml
components/Component2/controlset1.yaml
components/Component2/controlset2.yaml
```

### Starting hyperGRC

```
cd hypergrc

# Activate the virtual environment if it is not already active.
source venv/bin/activate

python3 -m hypergrc
```

# Licensing

hyperGRC is copyrighted 2018 by GovReady PBC and available under the open source license indicated in [LICENSE.md](LICENSE.md).

