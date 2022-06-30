"""OMOP2FHIR for CodeSystem"""
try:
    from omop_vocab_on_fhir.omop_vocab_on_fhir import cli
except ModuleNotFoundError:
    from omop_vocab_on_fhir import cli


cli()
