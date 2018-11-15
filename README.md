hyperGRC is a lightweight tool for managing component-to-control mappings for Compliance As Code written in Python and Flask.

hyperGRC provides a very friendly, kanban-style GUI for reading and writing YAML files representing control implementation content associated with system components.

The plan is for hyperGRC to support multiple underlying data formats. The goal is to make the world's most loved and hyper-useful IT GRC tool.


# How It Works

hyperGRC is a web application for workstation or server that reads a `.govready` or `opencontrol.yaml` and presents a GUI environment for editing system compliance based on component security plans.

hyperGRC reads the `.govready` configuration file, then reads the YAML files describing the controls provided by components, to generate web pages for making it easier to read and write reusable control implementation content.


# The .govready file

Here's a sample .govready file:

```
hgrc_version: 0.3.0
mode: local workstation
standard_controls_dir: standards
components_dir: components
organization:
  name: Department of Sobriety
system:
  name: DOS.gov
  src_repo: https://git.vendorco.net/dos/ssp-csv-to-yaml
  primary_standard: 800-53r4
standards:
- standard: 800-53r4
  standard_file: nist-800-53-rev4.yaml
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
team:
  user:
    name: Anonymous (workstation mode)
 ```


# Supported Data Formats:

### OpenControl

(content to be added)

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

(content coming soon)


### GovReady SSP Parser

(content coming soon)

# Launching

### Installing virtualenv

```
cd hypergrc
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=hypergrc.py
export GOVREADY_FILE=/abs/path/to/.govready

# Force reload upon code changes
export FLASK_DEBUG=1

flask run
```

### Running Flask server
```
cd hypergrc

# If venv not active
source venv/bin/activate

# If not run in a while
export FLASK_APP=hypergrc.py

# Force reload upon code changes
export FLASK_DEBUG=1

# Path to .govready file
export GOVREADY_FILE=/abs/path/to/.govready

flask run
```

# Licensing

hyperGRC is copyrighted 2018 by GovReady PBC and available under the open source license indicated in [LICENSE.md](LICENSE.md).

