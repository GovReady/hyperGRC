hyperGRC is a lightweight tool for managing multiple Compliance As Code repositories on a workstation.

The goal is a low-profile, hyper-useful IT GRC tool supporting Compliance as Code.

# Requirements

* Python3
* Packages listed in requirements.txt
* At least one Compliance as Code repository

# Install

```
git clone https://github.com/GovReady/hyperGRC.git hypergrc
cd hypergrc
pip install -r requirements.txt
```

### Installing with virtualenv

```
git clone https://github.com/GovReady/hyperGRC.git hypergrc
cd hypergrc
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

# Setting things up

1. Set up at least one Compliance As Code repository on your workstation.
2. Copy `.hypergrc_repos_example` to `.hypergrc_repos`.
3. Edit  `.hypergrc_repos` contents to point to each Compliance As Code hypergrc configuration file (default is currently `.govready`).

You are now ready to launch hyperGRC.

An example hyperGRC install along side a Compliance as Code repository for a system called "agencyapp" might look like the following, with one directory for the Compliance as Code repository and one directory for the hyperGRC.

```
workspace
├── agencyapp
│   ├── .git
│   ├── .gitignore
│   ├── .govready
│   ├── README.md
│   ├── certifications
│   │   └── fisma-low-impact.yaml
│   ├── components
│   │   ├── AWS
│   │   ├── CentOS
│   │   ├── Cisco-Cloud-Rtr
│   │   ├── Graylog
│   │   ├── Jenkins
│   │   ├── OpenLDAP
│   │   ├── SOC-Services
│   │   └── Terraform
│   ├── outputs
│   └── standards
│       └── nist-800-53-rev4.yaml
└── hypergrc
    ├── .git
    │   ├── ...
    ├── .gitignore
    ├── .hypergrc_repos
    ├── .hypergrc_repos_example
    ├── LICENSE.md
    ├── README.md
    ├── app
    │   ├── ...
    ├── hypergrc
    │   ├── ...
    ├── lint.py
    ├── ref
    │   ├── certifications
    │   │   └── fisma-low-impact.yaml
    │   └── standards
    │       ├── NIST-800-171r1.yaml
    │       └── nist-800-53-rev4.yaml
    ├── requirements.txt
    ├── static
    │   ├── ...
    └── venv
    │   ├── ...
```



# Launching

### Starting hyperGRC

```
python3 -m hypergrc
```

### Starting hyperGRC with virtualenv

```
# Activate the virtual environment if it is not already active.
source venv/bin/activate

python3 -m hypergrc
```



# Understanding the files

### The `.hypergrc_repos` file

hyperGRC reads the `.hypergc_repos` file on start up unless command-line options are provided.

The `.hypergrc_repos` file tells hyperGRC where to find all your local Compliance as Code repository. The format is a simple list of full file paths, one per line, to the hypergrc configuration file within each repository. The repositories configuration file can be named anything, but by convention we call it `.govready`.  For privacy, your  local `.hypergrc_repos` file is gitignored.

An example `.hypergrc_repos_example`file is included and looks like this:

```
/codedata/code/civicactions/Dept-of-Sobriety/dos.gov/.govready
/codedata/code/civicactions/democracy/citizenapp/.govready
```

#### Command-line options

The paths in the `.hypergrc_repos` file can also be given as command-line arguments instead, and the `.hypergrc_repos` file itself can be specified explicitly on the command-line by prefixing it with an `@` sign, as in `@.hypergrc_repos`.

### The Compliance as Code repo's hypergrc config file (default: `.govready`)

 hyperGRC reads a special "configuration file" found in each Compliance as Code repository to gather information about the system the repository represents and under what directory to find required data files. We call our configuration file `.govready`. 

Here's a sample configuration file for our imaginary "agencyapp" Compliance as Code repository:

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

### The individual component control files (various formats supported)

#### OpenControl

OpenControl is one of the first attempts at creating a friendly structured standard for representing component to control mappings. A `component.yaml` defines the component's controls.

```
components
├── AWS
│   ├── component.yaml
├── Graylog
│   ├── component.yaml
├── Keycloak
│   ├── component.yaml
```

Here's what an individual component control file looks like:

(Coming soon - content to be added)

#### "Fen" Format

An OpenControl variant that stores control families as separate files for smaller files and informative feedback on the command-line.

```
components
├── AWS
│   ├── AC-ACCESS_CONTROL.yaml
│   ├── AT-AWARENESS_AND_TRAINING.yaml
│   ├── AU-AUDIT_AND_ACCOUNTABILITY.yaml
│   ├── CA-SECURITY_ASSESSMENT_AND_AUTHORIZATION.yaml
│   ├── CM-CONFIGURATION_MANAGEMENT.yaml
│   ├── CP-CONTINGENCY_PLANNING.yaml
│   ├── IA-IDENTIFICATION_AND_AUTHENTICATION.yaml
│   ├── IR-INCIDENT_RESPONSE.yaml
│   ├── MA-MAINTENANCE.yaml
│   ├── MP-MEDIA_PROTECTION.yaml
│   ├── PE-PHYSICAL_AND_ENVIRONMENTAL_PROTECTION.yaml
│   ├── PL-PLANNING.yaml
│   ├── PS-PERSONNEL_SECURITY.yaml
│   ├── RA-RISK_ASSESSMENT.yaml
│   ├── SA-SYSTEM_AND_SERVICES_ACQUISITION.yaml
│   ├── SC-SYSTEM_AND_COMMUNICATIONS_PROTECTION.yaml
│   └── SI-SYSTEM_AND_INFORMATION_INTEGRITY.yaml
├── Graylog
│   ├── AC-ACCESS_CONTROL.yaml
│   ├── AU-AUDIT_AND_ACCOUNTABILITY.yaml
│   ├── CM-CONFIGURATION_MANAGEMENT.yaml
│   └── SI-SYSTEM_AND_INFORMATION_INTEGRITY.yaml
├── Keycloak
│   ├── AC-ACCESS_CONTROL.yaml
│   ├── AU-AUDIT_AND_ACCOUNTABILITY.yaml
```

Here's what an individual component control file looks like:

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

### The standards and certifications data file

hyperGRC expects to find individual "standard" and "certification" files in the local Compliance as Code repository to properly identify control, control guidance and the controls needed for a certification. 

You don't have to create these files. You can fetch from other repositories.

```
mkdir standards
curl https://raw.githubusercontent.com/GovReady/NIST-800-53r4-Standards/master/NIST-800-53r4.yaml > standards/nist-800-53-rev4.yaml
```

# Licensing

hyperGRC is copyrighted 2018 by GovReady PBC and available under the open source license indicated in [LICENSE.md](LICENSE.md).

