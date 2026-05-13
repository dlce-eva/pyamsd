"""
Parses data file 'org_data/records.tsv' into single csv files into 'raw'.
In addition it outputs given warnings while parsing. If you only want to check
the data integrity of data file 'org_data/records.tsv' then pass the argument
'--dry-run' -> amsd to_csv --dry-run.
"""
from pyamsd.util import StickTable


def register(parser):  # pylint: disable=C0116
    parser.add_argument(
        '--dry-run', action='store_true', default=False,
        help='Only check the data without generating csv files'
    )


def run(args):  # pylint: disable=C0116
    assert args.repos

    sticks = StickTable.from_records_tsv(args.repos / 'org_data' / 'records.tsv')
    sticks.check()
    if not args.dry_run:
        raw_path = args.repos / 'raw'
        raw_path.mkdir(exist_ok=True)
        with args.api.get_catalog() as cat:
            sticks.write(raw_path, {obj.metadata['name']: obj for obj in cat})
