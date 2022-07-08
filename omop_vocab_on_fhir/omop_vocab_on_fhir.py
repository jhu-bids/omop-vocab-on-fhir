"""OMOP2FHIR for CodeSystem

TODO's
  - CPT4: Require a valid API key. this can be inferred by successfully running the .jar from OMOP,
    though it took me ~10 minutes to finish, so would be better if it canceled the process early and read stdin
    and then from that can infer if it successfully started (aka valid key).
  - Make .run/ configs for every voc (1: copy paste files, 2: find/replace CPT4 -> <VOC>)
    can tell which ones needed because they still have zip files.
  - time how long it takes
  - add option to dump json for concept.definition and property.description
  - What if it can't find version and version isn't passed?
  - Add --all-single-codesystem
  - Add --all-codesystems (if no -f, do all formats, else just that format)
  - todo: later #1: (see where referenced below)
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
from argparse import ArgumentParser
from datetime import datetime
from typing import Dict, List

import pandas as pd


# Vars
PKG_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.join(PKG_DIR, '..')
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
OUT_FORMAT_CHOICES = ['fhir-json', 'fhir-json-extended', 'fhir-hapi-csv']
DEFAULTS = {
    'in-dir': DATA_DIR,
    'out-dir': PROJECT_DIR,
    'out-format': OUT_FORMAT_CHOICES[0],
    'server-url': 'http://hl7.org/fhir/',
    'upload': False,
    'codesystem-version': 'unknown-version',  # only can ascertain if `codesystem_name` matches what's in VOCABULARY.csv
    # 'codesystem-name': '',  # seems no way to programmatically ascertain

}


# Functions
def _gen_json(
    in_dir: str, out_dir: str, out_format: str, codesystem_name: str, codesystem_version: str,
    server_url: str,
) -> Dict:
    """Create FHIR CodeSystem JSON.
    Resources:
      - https://build.fhir.org/codesystem.html
      - https://build.fhir.org/codesystem-example-supplement.json.html"""
    # Vars
    concept_dict = {}
    sep = '\t'
    _id = f'{codesystem_name}-{codesystem_version}'
    server_url = server_url if server_url.endswith('/') else server_url + '/'
    codesystem_url = server_url if server_url.endswith('CodeSystem') else server_url + 'CodeSystem/'
    outpath = os.path.join(out_dir, f'{codesystem_name}-{codesystem_version}.json')
    if out_format == 'fhir-json-extended':
        outpath = outpath.replace('.json', '-extended.json')
    # todo: later #1: handle: DtypeWarning: Columns (6,9) have mixed types. Specify dtype option on import or set
    #  low_memory=False. concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep)
    try:
        relationship_df = pd.read_csv(os.path.join(in_dir, 'RELATIONSHIP.csv'), sep=sep).fillna('')
        concept_relationship_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT_RELATIONSHIP.csv'), sep=sep).fillna('')
        concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep).fillna('')
    except FileNotFoundError:
        in_dir = os.path.join(in_dir, codesystem_name)
        relationship_df = pd.read_csv(os.path.join(in_dir, 'RELATIONSHIP.csv'), sep=sep).fillna('')
        concept_relationship_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT_RELATIONSHIP.csv'), sep=sep).fillna('')
        concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep).fillna('')

    # 1. Construct top level CodeSystem JSON (excluding concept/ tree field)
    d = {  # todo: Is this thorough enough?
        "resourceType": "CodeSystem",
        "id": _id,  # todo: this ok?
        # "text": {  # todo
        #     "status": "generated",
        #     "div": ""
        # },
        "url": f"{codesystem_url}{_id}",
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
        prop = {
            "code": row["relationship_id"],
            "type": "code",
            # "uri": "",  # todo?
        }
        if out_format == 'fhir-json-extended':
            prop["description"] = json.dumps(dict(row))  # are there better descriptions avail?
        d["property"].append(prop)

    # 3. Parse: CONCEPT.csv: put in CodeSystem.concept
    # https://build.fhir.org/codesystem.html#CodeSystem.concept
    # todo: anywhere to put these fields other than definition?: "['domain_id', 'vocabulary_id',
    #  'concept_class_id', 'standard_concept', 'concept_code', 'valid_start_date', 'valid_end_date', 'invalid_reason']"
    for _index, row in concept_df.iterrows():
        concept = {
            "code": row['concept_id'],
            "display": row['concept_name'],
            # "designation": [{  # todo? example below
            #     "language": "en",
            #     "use": {
            #         "system": "http://acme.com/config/fhir/codesystems/internal",
            #         "code": "internal-label" },
            #     "value": "Obdurate Labs uses this with both kinds of units..."}]
            # "concept": ""  # todo?: Child Concepts (is-a/contains/categorizes)
        }
        # todo: definition: not a better definition? or use a subset of these fields?
        if out_format == 'fhir-json-extended':
            concept["definition"] = json.dumps(dict(row))
        # TODO temp
        concept_dict[row['concept_id']] = concept

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


def _gen_hapi_csv(
    in_dir: str, out_dir: str, codesystem_name: str, codesystem_version: str
) -> Dict[str, pd.DataFrame]:
    """Create custom HAPI FHIR CodeSystem CSV."""
    #  ...i don't want IDE to show error for unused var here. Better solution avail?
    try:
        omop_concepts_path = os.path.join(in_dir, 'CONCEPT.csv')
        omop_hierarchy_path = os.path.join(in_dir, 'CONCEPT_ANCESTOR.csv')
        omop_concepts_df = pd.read_csv(omop_concepts_path, sep='\t')
        omop_hierarchy_df = pd.read_csv(omop_hierarchy_path, sep='\t')
    except FileNotFoundError:
        in_dir = os.path.join(in_dir, codesystem_name)
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
    codesystem_name: str, in_dir: str = DEFAULTS['in-dir'], out_dir: str = DEFAULTS['out-dir'],
    out_format: str = DEFAULTS['out-format'], server_url: str = DEFAULTS['server-url'],
    upload: bool = DEFAULTS['upload'], codesystem_version: str = DEFAULTS['codesystem-version'],
) -> Dict[str, pd.DataFrame]:
    """Run"""
    # Massage params
    try:
        omop_vocab_registry_path = os.path.join(in_dir, 'VOCABULARY.csv')
        omop_vocab_registry_df = pd.read_csv(omop_vocab_registry_path, sep='\t')
    except FileNotFoundError:
        omop_vocab_registry_path = os.path.join(in_dir, codesystem_name, 'VOCABULARY.csv')
        omop_vocab_registry_df = pd.read_csv(omop_vocab_registry_path, sep='\t')

    if codesystem_version == DEFAULTS['codesystem-version']:
        # try to ascertain
        omop_vocab_registry_df = omop_vocab_registry_df[omop_vocab_registry_df['vocabulary_id'] == codesystem_name]
        if len(omop_vocab_registry_df) == 1:
            codesystem_version = omop_vocab_registry_df['vocabulary_version']
            codesystem_version = list(dict(codesystem_version).values())[0]
            codesystem_version = codesystem_version.replace(codesystem_name, '').strip()

    # Create results
    if out_format in ['fhir-json', 'fhir-json-extended']:
        output: Dict = _gen_json(
            in_dir=in_dir, out_dir=out_dir, out_format=out_format, codesystem_name=codesystem_name,
            codesystem_version=codesystem_version, server_url=server_url)
    else:  # 'fhir-hapi-csv'
        output: Dict = _gen_hapi_csv(
            in_dir=in_dir, out_dir=out_dir, codesystem_name=codesystem_name, codesystem_version=codesystem_version)

    # todo: upload to server
    #  - POST not possible for hapi csv from outside server. throw warn for that
    if upload:
        print()

    return output


def run_all():
    """Run all code systems based on config.tsv"""
    config_path = os.path.join(DATA_DIR, 'config.tsv')
    df = pd.read_csv(config_path, sep='\t')
    df = df[df['done'] == False]
    run_configs: List[Dict] = []
    for _index, row in df.iterrows():
        # TODO: skipping -extended for now
        if row['format'] == 'fhir-json-extended':
            continue
        run_configs.append({
            'codesystem_name': row['vocabulary'],
            'out_format': row['format'],
        })
    for d in run_configs:
        print(f'Converting {d["codesystem_name"]} to {d["out_format"]}.')
        t0 = datetime.now()
        run(**d)
        t1 = datetime.now()
        # TODO: Update the CSV as each vocab/format combo is done.
        # todo: update somehow by index of this?
        # df_i = df[df['vocabulary'] == d['codesystem_name'] & df['out_format'] == d['format']]
        # todo or can I assign an eq statement like?
        # df[df['vocabulary'] == d['codesystem_name'] & df['out_format'] == d['format']]['done'] = TRUE?
        # then:
        # pd.to_csv(config_path, index=False, sep='\t')
        print(f'Completed after {(t1 - t0).seconds} seconds.')
        print()


def cli_get_parser() -> ArgumentParser:
    """Add required fields to parser."""
    package_description = \
        ''
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-n', '--codesystem-name',
        help='The name of the code system, e.g. RxNorm, CPT4, etc. Required.')
    parser.add_argument(
        '-v', '--codesystem-version',
        default=DEFAULTS['codesystem-version'],
        help='The version of the code system. This can be found by looking up the code system\'s row within '
             'VOCABULARY.csv.')
    parser.add_argument(
        '-i', '--in-dir',
        default=DEFAULTS['in-dir'],
        help='The data where OMOP `.csv` files are stored.')
    parser.add_argument(
        '-o', '--out-dir',
        default=DEFAULTS['out-dir'],
        help='The directory where results should be saved.')
    parser.add_argument(
        '-f', '--out-format',
        choices=OUT_FORMAT_CHOICES,
        default=DEFAULTS['out-format'],
        help='The format of the output to generate.')
    parser.add_argument(
        '-s', '--server-url',
        default=DEFAULTS['server-url'],
        help='Will show this within any JSON generated. Will also upload to this server if `--upload` is passed. This '
             'should be the "FHIR base URL".')
    parser.add_argument(
        '-u', '--upload',
        action='store_true',
        help='If passed, will attempt to upload at the `--server-url` passed.')
    parser.add_argument(
        '-a', '--all-codesystems',
        action='store_true',
        help='If passed, will check data/config.tsv and convert based on that.')

    return parser


# todo: upload: should turn to false if server_url is default, and print warning
def cli_validate(d: Dict) -> Dict:
    """Validate CLI args. Also updates these args if/as necessary"""
    if not d['codesystem_name']:
        raise RuntimeError('--codesystem-name is required')
    return d


def cli() -> Dict[str, pd.DataFrame]:
    """Command line interface."""
    parser = cli_get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    if kwargs_dict['all_codesystems'] == True:
        run_all()
    else:
        kwargs_dict = cli_validate(kwargs_dict)
        return run(**kwargs_dict)


# Execution
if __name__ == '__main__':
    cli()
