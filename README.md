# `omop2fhir-codesystem`
OMOP2FHIR converter specifically for CodeSystems.

## How it works
This converter works on OMOP standard vocabulary tables and converts them to FHIR CodeSystem formats.

### OMOP [standardized vocabulary tables](https://ohdsi.github.io/CommonDataModel/)
The following tables are present and downloadable in CSV form, e.g. from [Athena](https://athena.ohdsi.org/).
```
CONCEPT.csv              CONCEPT_CLASS.csv        CONCEPT_SYNONYM.csv      DRUG_STRENGTH.csv        VOCABULARY.csv
CONCEPT_ANCESTOR.csv     CONCEPT_RELATIONSHIP.csv DOMAIN.csv               RELATIONSHIP.csv
```

Particularly, `CONCEPT.csv` and `CONCEPT_ANCESTOR.csv` are used to construct FHIR CodeSystem, at least in its simplest 
variation.

### FHIR CodeSystem
#### HAPI CodeSystem CSV format
- `concept.csv`: List of concepts with fields `CODE` and `DISPLAY`.
- `hierarchy.csv`: A simple `is_a` hierarchy with fields `PARENT` and `CHILD`, the range of both fields being the 
concept's OMOP code.

#### FHIR standard CodeSystem JSON format
There are two variations that can be generated: (i) standard, and (ii) extended. 
Both are valid FHIR JSON. The difference is that _extended_ includes additional 
information: (i) concept definitions, and (ii) property descriptions. OMOP does
not provide these, so what the _extended_ version provides is _all_ information
about the concepts and relationship properties. That is, every field  that OMOP
provides becomes JSON serialiazed into these concept definition and property 
description fields.

##### Standard variation ( -- TODO -- )
Example concept:
```json

```

Example concept relationship property:
```json

```

##### Extended variation
Example concept:
```json

```

Example concept relationship property:
```json

```

## Usage
You can use this package by cloning this repository and running the CLI (Command
Line Interface) from the cloned directory.

Run: `python -m omop2fhir_codesystems <PARAMS>`

CLI Params
|Short flag | Long flag | Choices | Default | Description |
|---	|---	|---	|--- | --- |
| `-n` | `--codesystem-name` |  |  | The name of the code system, e.g. RxNorm, CPT4, etc. Required. |
| `-v` | `--codesystem-version` | | `'unknown-version'` | The version of the code system. This can be found by looking up the code system's row within VOCABULARY.csv. |
| `-i` | `--in-dir` | | The `data/` directory of the cloned repository. | The data where OMOP `.csv` files are stored. |
| `-o` | `--out-dir` | | The cloned repository directory. | The directory where results should be saved. |
| `-f` | `--out-format` | `['fhir-json', 'fhir-json-extended', 'fhir-hapi-csv']` | `'fhir-json'` | The format of the output to generate. |
| `-s` | `--server-url` | | `'http://hl7.org/fhir/'` | Will show this within any JSON generated. Will also upload to this server if `--upload` is passed. This should be the "FHIR base URL". |
| `-u` | `--upload` | | | If passed, will attempt to upload at the `--server-url` passed. |
| `-h` | `--help` | | | Shows help information for using the tool. |
