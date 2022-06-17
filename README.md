# `omop2fhir-codesystem`
OMOP2FHIR converter specifically for CodeSystems.

## How it works
This converter works on OMOP standard vocabulary tables and converts them to FHIR CodeSystem format(s).

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
TODO
