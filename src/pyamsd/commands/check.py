"""
Prints out missing media files which are listed in org_data/records.tsv
but not found in the media catalog (images/catalog.json).
"""


def run(args):
    args.api.validate()
