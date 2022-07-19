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
import sys
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
    'omop-cdm-version': 'unknown-omop-cdm-version',
    'codesystem-version': 'unknown-codesystem-version',  # can get if `codesystem_name` matches what's in VOCABULARY.csv
    # 'codesystem-name': '',  # seems no way to programmatically ascertain

}


# Functions
def _gen_json(
    in_dir: str, out_dir: str, out_format: str, codesystem_name: str, codesystem_version: str, omop_cdm_version: str,
    server_url: str,
) -> Dict:
    """Create FHIR CodeSystem JSON.
    Resources:
      - https://build.fhir.org/codesystem.html
      - https://build.fhir.org/codesystem-example-supplement.json.html"""
    # Vars
    concept_dict = {}
    sep = '\t'
    _id = f'{codesystem_name}-{codesystem_version}'.replace(' ', '.').replace('\t', '.')
    server_url = server_url if server_url.endswith('/') else server_url + '/'
    codesystem_url = server_url if server_url.endswith('CodeSystem') else server_url + 'CodeSystem/'
    if omop_cdm_version != DEFAULTS['omop-cdm-version']:
        omop_cdm_version = 'OMOP-CDM-' + omop_cdm_version
    outpath = os.path.join(out_dir, f'{codesystem_name}-{codesystem_version}_{omop_cdm_version}.json')
    if out_format == 'fhir-json-extended':
        outpath = outpath.replace('.json', '-extended.json')
    # todo: later #1: handle: DtypeWarning: Columns (6,9) have mixed types. Specify dtype option on import or set
    #  low_memory=False. concept_df = pd.read_csv(os.path.join(in_dir, 'CONCEPT.csv'), sep=sep)
    #  pandas docs: dict of column -> type: Data type for data or columns. E.g. {‘a’: np.float64, ‘b’: np.int32, ‘c’:
    #  ‘Int64’} Use str or object together with suitable na_values settings to preserve and not interpret dtype.
    #  If converters are specified, they will be applied INSTEAD of dtype conversion.
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
            "code": int(row['concept_id']),
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
        # TODO: Need to have pandas DF use dtypes instead of casting to int() here and elsewhere
        concept_dict[int(row['concept_id'])] = concept

    # 4. Parse: CONCEPT_RELATIONSHIP.csv: put in CodeSystem.concept
    for _index, row in concept_relationship_df.iterrows():
        try:
            if 'property' not in concept_dict[int(row['concept_id_1'])]:
                concept_dict[int(row['concept_id_1'])]['property'] = []
            concept_dict[int(row['concept_id_1'])]['property'].append({
                "code": row["relationship_id"],
                "valueCode": int(row["concept_id_2"])
                # anywhere to put?: `valid_start_date`, `valid_end_date`, `invalid_reason`?
            })
        except KeyError:
            print(f'Warning: Concept with id {row["concept_id_1"]} appeared in the `concept_id_1` column of '
                  f'`CONCEPT_RELATIONSHIP.csv`, but was not found in `CONCEPT.csv`. This concept will thus be excluded.'
                  , file=sys.stderr)
    d['concept'] = list(concept_dict.values())

    # Save
    with open(outpath, 'w') as fp:
        json.dump(d, fp)

    return d


def _gen_hapi_csv(
    in_dir: str, out_dir: str, codesystem_name: str, codesystem_version: str, omop_cdm_version: str
) -> Dict[str, pd.DataFrame]:
    """Create custom HAPI FHIR CodeSystem CSV."""
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

    archive_name = 'HAPI-FHIR-CodeSystem-CSVs.zip'
    if codesystem_name:
        codesystem_name = codesystem_name + '_'
        codesystem_version = codesystem_version + '_'
    else:
        codesystem_name = ''
        codesystem_version = ''
    if omop_cdm_version != DEFAULTS['omop-cdm-version']:
        omop_cdm_version = 'OMOP-CDM-' + omop_cdm_version
    archive_name = f'{codesystem_name}{codesystem_version}{omop_cdm_version}-{archive_name}'
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
    omop_cdm_version: str = DEFAULTS['omop-cdm-version'],
) -> Dict[str, pd.DataFrame]:
    """Run"""
    omop_vocab_registry_df = pd.read_csv(os.path.join(in_dir, 'VOCABULARY.csv'), sep='\t')

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
            codesystem_version=codesystem_version, omop_cdm_version=omop_cdm_version, server_url=server_url)
    else:  # 'fhir-hapi-csv'
        output: Dict = _gen_hapi_csv(
            in_dir=in_dir, out_dir=out_dir, codesystem_name=codesystem_name, codesystem_version=codesystem_version,
            omop_cdm_version=omop_cdm_version)

    # todo: add feature: upload to server
    #  - POST not possible for hapi csv from outside server. throw warn for that
    if upload:
        print('Warning: Upload feature not yet supported. Skipping this step.', file=sys.stderr)

    return output


def run_all():
    """Run all code systems based on config.tsv"""
    config_path = os.path.join(DATA_DIR, 'config.csv')
    df = pd.read_csv(config_path)
    if len(list(df.columns)) == 1:  # likely means tab-separated
        df = pd.read_csv(config_path, sep='\t')
    if 'done' in list(df.columns):
        df = df[df['done'] != True]
    run_configs: List[Dict] = []
    for _index, row in df.iterrows():
        run_configs.append({
            'codesystem_name': row['codesystem_name'],
            'out_format': row['out_format'],
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
        help='The name of the code system, e.g. RxNorm, CPT4, etc. It is intended that the set of OMOP files being read'
             ' (i.e. `CONCEPT.csv`, etc) pertain to a single code system. If that is not the case or if using '
             '`--all-codesystems`, leave blank. Otherwise this flag is required.')
    parser.add_argument(
        '-vc', '--codesystem-version',
        default=DEFAULTS['codesystem-version'],
        help='The version of the native code system / vocabulary. OMOP-Vocab-on-FHIR will try to find this by looking '
             'up the code system\'s row within VOCABULARY.csv. However, it will not always appear, so passing the '
             'version as CLI argument is useful if you happen to know it.')
    parser.add_argument(
        '-vo', '--omop-cdm-version',
        default=DEFAULTS['omop-cdm-version'],
        help='Optional. The OMOP CDM (Common Data Model) version to support, in integer form (e.g. 5 and not 5.x.y). '
             'Currently, only version 5 is officially supported, though it will try for other versions anyway. '
             'OMOP-Vocab-on-FHIR will find this by looking in VOCABULARY.csv where `vocabulary_id == "None"`. '
             'However, this CLI argument has been left here for edge cases where '
             'old versions may display the version in this way.')
    parser.add_argument(
        '-i', '--in-dir',
        default=DEFAULTS['in-dir'],
        help='The path where OMOP `.csv` files are stored. If using `--all-codesystems`, should be a directory '
             'containing subdirectories, where each subdirectory is a different code system with its corresponding OMOP'
             ' `.csv` files.')
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
    # todo: when/if added back, need to (i) add logic to do the upload, (ii) add a line back to the README table.
    # parser.add_argument(
    #     '-u', '--upload',
    #     action='store_true',
    #     help='If passed, will attempt to upload at the `--server-url` passed.')
    parser.add_argument(
        '-a', '--all-codesystems',
        action='store_true',
        help=f'If passed, will use a `<in_dir>/config.csv` to orchestrate which vocabularies to convert and in what '
             f'format(s). Must contain 2 columns: (1) `codesystem_name`, the names of which should match corresponding '
             f'subfolder names in `<in_dir>`, and (2) `out_format`, the formats of which should be one of '
             f'`{OUT_FORMAT_CHOICES}`. Can include (3) `done`, an optional boolean column for storing information about'
             f' which `codesystem_name`/`out_format` combos have already been converted. If the value is `TRUE` for a '
             f'given row, that `codesystem_name`/`out_format` combo will be skipped.')

    return parser


def get_omopcdmversion_and_indir(in_dir: str, codesystem_name: str) -> (str, str):
    """Get OMOP CDM Version"""
    VOCAB_FILENAME = 'VOCABULARY.csv'
    v = DEFAULTS['omop-cdm-version']

    omop_vocab_registry_path = os.path.join(in_dir, VOCAB_FILENAME)
    if not os.path.exists(omop_vocab_registry_path):  # try looking in subdir w/ codesystem's name
        omop_vocab_registry_path = os.path.join(in_dir, codesystem_name, VOCAB_FILENAME)
    if not os.path.exists(omop_vocab_registry_path):  # try lowercase
        omop_vocab_registry_path = os.path.join(in_dir, codesystem_name.lower(), VOCAB_FILENAME)
    if not os.path.exists(omop_vocab_registry_path):  # try uppercase
        omop_vocab_registry_path = os.path.join(in_dir, codesystem_name.upper(), VOCAB_FILENAME)
    if not os.path.exists(omop_vocab_registry_path):  # try title case
        omop_vocab_registry_path = os.path.join(in_dir, codesystem_name.title(), VOCAB_FILENAME)
    omop_vocab_registry_df = pd.read_csv(omop_vocab_registry_path, sep='\t').fillna('')  # will fail if still not found
    # Update `in_dir` if it changed
    in_dir = omop_vocab_registry_path.replace(VOCAB_FILENAME, '')

    version_row: pd.DataFrame = omop_vocab_registry_df[omop_vocab_registry_df['vocabulary_id'] == 'None']
    if len(version_row) == 1:
        v: str = list(version_row['vocabulary_version'])[0]
    return v, in_dir


# todo: upload: should turn to false if server_url is default, and print warning
def cli_validate(d: Dict) -> Dict:
    """Validate CLI args. Also updates these args if/as necessary"""
    # codesystem_name
    if not d['codesystem_name']:
        raise RuntimeError('--codesystem-name is required unless using `--all-codesystems`.')

    # omop_cdm_version & in_dir
    d['omop_cdm_version'], d['in_dir'] = get_omopcdmversion_and_indir(
        in_dir=d['in_dir'], codesystem_name=d['codesystem_name'])
    if d['omop_cdm_version'] == DEFAULTS['omop-cdm-version']:
        print('Could not identify OMOP CDM version.', file=sys.stderr)
    if not any([d['omop_cdm_version'].startswith(x) for x in ['v5', '5']]):
        print('Only OMOP CDM version 5 is officially supported. Trying anyway.', file=sys.stderr)

    return d


def cli() -> Dict[str, pd.DataFrame]:
    """Command line interface."""
    parser = cli_get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    if kwargs_dict['all_codesystems'] == True:
        run_all()
    else:
        del kwargs_dict['all_codesystems']
        kwargs_dict = cli_validate(kwargs_dict)
        return run(**kwargs_dict)


# Execution
if __name__ == '__main__':
    cli()
