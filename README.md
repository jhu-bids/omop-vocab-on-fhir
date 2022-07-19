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
| `-n` | `--codesystem-name` |  |  | The name of the code system, e.g. RxNorm, CPT4, etc. It is intended that the set of OMOP files being read (i.e. `CONCEPT.csv`, etc) pertain to a single code system. If that is not the case or if using `--all-codesystems`, leave blank. Otherwise this flag is required. |
| `-vc` | `--codesystem-version` | | `'unknown-version'` | The version of the native code system / vocabulary. OMOP-Vocab-on-FHIR will try to find this by looking up the code system\'s row within VOCABULARY.csv. However, it will not always appear, so passing the version as CLI argument is useful if you happen to know it. |
| `-vo` | `--omop-cdm-version` | | `5` | Optional. The OMOP CDM (Common Data Model) version to support, in integer form (e.g. 5 and not 5.x.y). Currently, only version 5 is supported, though it will try for other versions anyway. OMOP-Vocab-on-FHIR will find this by looking in VOCABULARY.csv where `vocabulary_id == "None"`. However, this CLI argument has been left here for edge cases where old versions may display the version in this way. |
| `-i` | `--in-dir` | | The `data/` directory of the cloned repository. | The path where OMOP `.csv` files are stored. If using `--all-codesystems`, should be a directory containing subdirectories, where each subdirectory is a different code system with its corresponding OMOP `.csv` files. |
| `-o` | `--out-dir` | | The cloned repository directory. | The directory where results should be saved. |
| `-f` | `--out-format` | `['fhir-json', 'fhir-json-extended', 'fhir-hapi-csv']` | `'fhir-json'` | The format of the output to generate. |
| `-s` | `--server-url` | | `'http://hl7.org/fhir/'` | Will show this within any JSON generated. Will also upload to this server if `--upload` is passed. This should be the "FHIR base URL". |
| `-a` | `--all-codesystems` | | | If passed, will use a `<in_dir>/config.csv` to orchestrate which vocabularies to convert and in what format(s). Must contain 2 columns: (1) `codesystem_name`, the names of which should match corresponding subfolder names in `<in_dir>`, and (2) `out_format`, the formats of which should be one of `<out_format>`. Can include (3) `done`, an optional boolean column for storing information about which `codesystem_name`/`out_format` combos have already been converted. If the value is `TRUE` for a given row, that `codesystem_name`/`out_format` combo will be skipped. |
| `-h` | `--help` | | | Shows help information for using the tool. |
