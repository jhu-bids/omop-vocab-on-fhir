# OMOP Vocab on FHIR
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

##### Standard variation
Example concept relationship property:
```json
{"code": "Has specimen proc", "type": "code"}
```

Example concept:
```json
{
  "code": 756331,
  "display": "procedure_occurrence.procedure_type_concept_id",
  "property": [
    {
      "code": "Contained in version",
      "valueCode": 756265
    },
    {
      "code": "Is a",
      "valueCode": 1147301
    },
    {
      "code": "Mapped from",
      "valueCode": 756331
    },
    {
      "code": "Maps to",
      "valueCode": 756331
    }
  ]
}
```

##### Extended variation
Example concept relationship property (includes `description`):
```json
{
  "code": "Has specimen proc",
  "type": "code",
  "description": "{\"relationship_id\": \"Has specimen proc\", \"relationship_name\": \"Has specimen procedure (SNOMED)\", \"is_hierarchical\": 0, \"defines_ancestry\": 0, \"reverse_relationship_id\": \"Specimen proc of\", \"relationship_concept_id\": 44818775}"
}
```

Example concept (includes `definition`):
```json
{
  "code": 756331,
  "display": "procedure_occurrence.procedure_type_concept_id",
  "definition": "{\"concept_id\": 756331, \"concept_name\": \"procedure_occurrence.procedure_type_concept_id\", \"domain_id\": \"Metadata\", \"vocabulary_id\": \"CDM\", \"concept_class_id\": \"Field\", \"standard_concept\": \"S\", \"concept_code\": \"CDM1016\", \"valid_start_date\": 20210925, \"valid_end_date\": 20991231, \"invalid_reason\": \"\"}",
  "property": [
    {
      "code": "Contained in version",
      "valueCode": 756265
    },
    {
      "code": "Is a",
      "valueCode": 1147301
    },
    {
      "code": "Mapped from",
      "valueCode": 756331
    },
    {
      "code": "Maps to",
      "valueCode": 756331
    }
  ]
}
```

## Usage
You can use this package by cloning this repository and running the CLI (Command
Line Interface) from the cloned directory.

Run: `python -m omop_vocab_on_fhir <PARAMS>`

CLI Params
|Short flag | Long flag | Choices | Default | Description |
|---	|---	|---	|--- | --- |
| `-n` | `--codesystem-name` |  |  | The name of the code system, e.g. RxNorm, CPT4, etc. Required. |
| `-vc` | `--codesystem-version` | | `'unknown-version'` | The version of the native code system / vocabulary. This can be found by looking up the code system's 'row within VOCABULARY.csv. |
| `-vo` | `--omop-version` | | `5` | The OMOP version (integer) to support. Currently, only 5.0 is supported. |
| `-i` | `--in-dir` | | The `data/` directory of the cloned repository. | The data where OMOP `.csv` files are stored. |
| `-o` | `--out-dir` | | The cloned repository directory. | The directory where results should be saved. |
| `-f` | `--out-format` | `['fhir-json', 'fhir-json-extended', 'fhir-hapi-csv']` | `'fhir-json'` | The format of the output to generate. |
| `-s` | `--server-url` | | `'http://hl7.org/fhir/'` | Will show this within any JSON generated. Will also upload to this server if `--upload` is passed. This should be the "FHIR base URL". |
| `-u` | `--upload` | | | If passed, will attempt to upload at the `--server-url` passed. |
| `-h` | `--help` | | | Shows help information for using the tool. |
