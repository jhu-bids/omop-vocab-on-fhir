"""OMOP2FHIR for CodeSystem

TODO's
  - time how long it takes
  - add option to dump json for concept.definition and property.description
Later areas for improvement
  1. Accept params from CLI
  2. Pre-bake common vocabularies, such as RxNorm. (what else is available and useful in OMOP?)
  3. Add versioning to CodeSystems in data/ dir. The version can be found in VOCABULARY.csv, vocabulary_version col.
  4. Need LFS (Large File Storage) for vocab files in data/ dir?
  5. Add upload_server_url
  6. QA check: Any diff between R4 and R5 for CodeSystem?
  7. Performance: Increase it? Took awhile. How to improve? Convert pandas to dict? profile it?

Assumptions
  1. For hierarchy building, only min_levels_of_separation=1 and max_levels_of_separation=1 is necessary. Everything
  else should only be useful for analytics.
"""
import json
import os
import zipfile
from datetime import datetime
from typing import Dict

import pandas as pd


# Vars
PKG_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.join(PKG_DIR, '..')
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
CONFIG = {
    'in_dir': os.path.join(DATA_DIR, '../data/RxNorm'),  # temp
    'out_dir': PROJECT_DIR,
    'out_format': ['fhir-json', 'fhir-hapi-csv'][0],  # todo: accept from CLI
    'codesystem_name': 'RxNorm',  # temp. can get w/out passing explicit param?
    # 'upload_server_url': 'http://20.119.216.32:8080/fhir/'
    'upload_server_url': 'http://hl7.org/fhir/CodeSystem/',
}


# Functions
def gen_json(
    in_dir: str, out_dir: str, codesystem_name: str = None, codesystem_version: str = None,
    upload_server_url: str = CONFIG['upload_server_url']
) -> Dict:
    """Create FHIR CodeSystem JSON.
    Resources:
      - https://build.fhir.org/codesystem.html
      - https://build.fhir.org/codesystem-example-supplement.json.html"""
    # Vars
    concept_dict = {}
    sep = '\t'
    _id = f'{codesystem_name}-{codesystem_version}'
    outpath = os.path.join(out_dir, f'{codesystem_name}-{codesystem_version}.json')
    # todo: later: handle: DtypeWarning: Columns (6,9) have mixed types. Specify dtype option on import or set
    #  low_memory=False. concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep)
    relationship_df = pd.read_csv(os.path.join(in_dir, 'RELATIONSHIP.csv'), sep=sep)
    concept_relationship_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT_RELATIONSHIP.csv'), sep=sep)  # hierarchy
    concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep)

    # 1. Construct top level CodeSystem JSON (excluding concept/ tree field)
    d = {  # todo: Is this thorough enough?
        "resourceType": "CodeSystem",
        "id": _id,  # todo: this ok?
        # "text": {  # todo
        #     "status": "generated",
        #     "div": ""
        # },
        "url": f"{upload_server_url}{_id}",
        "version": codesystem_version,
        "name": codesystem_name,
        "status": "draft",  # todo
        "experimental": True,  # todo
        "date": str(datetime.now())[0:10],
        # "publisher": "Athena? system e.g. RxNorm? OMOP? BIDS? TIMS?",  # todo
        # "contact": [{  # todo
        #     "name": "FHIR project team",
        #     "telecom": [{
        #         "system": "url",
        #         "value": "http://hl7.org/fhir"
        #     }]
        # }],
        "content": ['not-present', 'example', 'fragment', 'complete', 'supplement'][3],  # not true till finished
        "property": [],
        "concept": [],
    }

    # 2. Parse: RELATIONSHIP.csv: put in CodeSystem.property
    # https://build.fhir.org/codesystem-concept-property-type.html
    for _index, row in relationship_df.iterrows():
        # noinspection PyTypeChecker
        d["property"].append({
            "code": row["relationship_id"],
            "description": json.dumps(dict(row)),  # are there better descriptions avail?
            "type": "code",
            # "uri": "",  # todo?
        })

    # 3. Parse: CONCEPT.csv: put in CodeSystem.concept
    # https://build.fhir.org/codesystem.html#CodeSystem.concept
    # todo: anywhere to put these fields other than definition?: "['domain_id', 'vocabulary_id',
    #  'concept_class_id', 'standard_concept', 'concept_code', 'valid_start_date', 'valid_end_date', 'invalid_reason']"
    for _index, row in concept_df.iterrows():
        concept_dict[row['concept_id']] = {
            "code": row['concept_id'],
            "display": row['concept_name'],
            # todo: definition: not a better definition? or use a subset of these fields?
            "definition": json.dumps(dict(row)),
            # "designation": [{  # todo? example below
            #     "language": "en",
            #     "use": {
            #         "system": "http://acme.com/config/fhir/codesystems/internal",
            #         "code": "internal-label" },
            #     "value": "Obdurate Labs uses this with both kinds of units..."}]
            # "concept": ""  # todo?: Child Concepts (is-a/contains/categorizes)
        }

    # 4. Parse: CONCEPT_RELATIONSHIP.csv: put in CodeSystem.concept
    for _index, row in concept_relationship_df.iterrows():
        if 'property' not in concept_dict[row['concept_id_1']]:
            concept_dict[row['concept_id_1']]['property'] = []
        concept_dict[row['concept_id_1']]['property'].append({
            "code": row["relationship_id"],
            "valueCode": row["concept_id_2"]
            # anywhere to put?: `valid_start_date`, `valid_end_date`, `invalid_reason`?
        })
    d['concept'] = list(concept_dict.values())

    # Save
    with open(outpath, 'w') as fp:
        json.dump(d, fp)

    return d


def gen_hapi_csv(
    in_dir: str, out_dir: str, codesystem_name: str = None, codesystem_version: str = None, **kwargs
) -> Dict[str, pd.DataFrame]:
    """Create custom HAPI FHIR CodeSystem CSV."""
    print(kwargs)  # todo: temp: need kwargs because im routing all params to all funcs, but
    #  ...i don't want IDE to show error for unused var here. Better solution avail?
    omop_concepts_path = os.path.join(in_dir, 'CONCEPT.csv')
    omop_hierarchy_path = os.path.join(in_dir, 'CONCEPT_ANCESTOR.csv')
    omop_concepts_df = pd.read_csv(omop_concepts_path, sep='\t')
    omop_hierarchy_df = pd.read_csv(omop_hierarchy_path, sep='\t')

    # Construct: concepts
    hapi_concepts_df = omop_concepts_df[['concept_id', 'concept_name']]
    hapi_concepts_df = hapi_concepts_df.rename(columns={
        'concept_id': 'CODE',
        'concept_name': 'DISPLAY',
    })

    # Construct: hierarchy
    hapi_hierarchy_df = omop_hierarchy_df[
        (omop_hierarchy_df['min_levels_of_separation'] == 1) &
        (omop_hierarchy_df['max_levels_of_separation'] == 1)]
    hapi_hierarchy_df = hapi_hierarchy_df[['ancestor_concept_id', 'descendant_concept_id']]
    hapi_hierarchy_df = hapi_hierarchy_df.rename(columns={
        'ancestor_concept_id': 'PARENT',
        'descendant_concept_id': 'CHILD',
    })

    # Save and return
    hapi_concepts_path = os.path.join(out_dir, 'concepts.csv')
    hapi_hierarchy_path = os.path.join(out_dir, 'hierarchy.csv')
    hapi_paths = [hapi_concepts_path, hapi_hierarchy_path]
    hapi_concepts_df.to_csv(hapi_concepts_path, index=False)
    hapi_hierarchy_df.to_csv(hapi_hierarchy_path, index=False)

    archive_name = 'hapi_fhir_codesystem_csv.zip'
    if codesystem_name:
        codesystem_version = codesystem_version + '_' if codesystem_version else ''
        archive_name = f'{codesystem_name}_{codesystem_version}hapi_csv.zip'
    with zipfile.ZipFile(os.path.join(PROJECT_DIR, archive_name), 'w') as arch:
        for path in hapi_paths:
            filename = os.path.basename(path)
            arch.write(path, filename, compress_type=zipfile.ZIP_DEFLATED)

    for path in hapi_paths:
        os.remove(path)
    output = {
        'concepts.csv': hapi_concepts_df,
        'hierarchy.csv': hapi_hierarchy_df,
    }
    return output


def run(
    in_dir: str, out_dir: str, out_format: str, codesystem_name: str,
    upload_server_url: str = CONFIG['upload_server_url']
) -> Dict[str, pd.DataFrame]:
    """Run
    upload_server: If present, will upload to that server."""
    # Create additional params
    omop_vocab_registry_path = os.path.join(in_dir, 'VOCABULARY.csv')
    omop_vocab_registry_df = pd.read_csv(omop_vocab_registry_path, sep='\t')
    omop_vocab_registry_df = omop_vocab_registry_df[omop_vocab_registry_df['vocabulary_id'] == codesystem_name]
    codsystem_version = omop_vocab_registry_df['vocabulary_version']
    codsystem_version = list(dict(codsystem_version).values())[0]
    codsystem_version = codsystem_version.replace(codesystem_name, '').strip()

    # Call func
    format_funcs = {
        'fhir-json': gen_json,
        'fhir-hapi-csv': gen_hapi_csv,
    }
    func = format_funcs[out_format]
    output = func(in_dir, out_dir, codesystem_name, codsystem_version, upload_server_url)

    # todo: upload to server
    #  - POST not possible for hapi csv from outside server. throw warn for that

    return output


# Execution
if __name__ == '__main__':
    run(**CONFIG)
