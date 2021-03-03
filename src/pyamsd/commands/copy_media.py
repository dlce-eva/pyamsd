"""
Copies missing media files which are listed in org_data/records.tsv
from the passed path to mediafiles/upload.
Example: amsd copy_media ~/Downloads/Message_sticks_images_all
"""
from clldutils.clilib import PathType


def register(parser):
    parser.add_argument('source_path', type=PathType(type='dir'))


def run(args):
    args.api.validate(args.source_path.resolve())
