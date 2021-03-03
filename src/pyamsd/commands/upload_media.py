"""
Uploads media files from the passed directory to the CDSTAR server,
if an object identified by metadata's 'name' exists it will be deleted first.
"""
from clldutils.clilib import PathType


def register(parser):
    parser.add_argument('upload_path', type=PathType(type='dir'))


def run(args):
    supported_types = {'imagefile': ['png', 'gif', 'jpg', 'jpeg', 'tif', 'tiff'],
                       'pdffile': ['pdf'],
                       'moviefile': ['mp4']}

    with args.api.get_catalog() as cat:
        for ifn in sorted(args.upload_path.iterdir()):
            print(ifn.name)

            fmt = ifn.suffix[1:].lower()
            meta_type = None
            for t, suffixes in supported_types.items():
                if fmt in suffixes:
                    meta_type = t
                    break
            if meta_type is None:
                print('No supported media format - skipping {0}'.format(fmt))
                continue

            md = {
                'collection': 'amsd',
                'name': str(ifn.stem),
                'type': meta_type,
                'path': str(ifn.name)
            }

            # Create the new object
            for (fname, created, obj) in cat.create(str(ifn), md):
                args.log.info('{0} -> {1} object {2.id}'.format(
                    fname, 'new' if created else 'existing', obj))
