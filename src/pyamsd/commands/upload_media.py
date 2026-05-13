"""
Uploads media files from the passed directory to the CDSTAR server,
if an object identified by metadata's 'name' exists it will be deleted first.
"""
from clldutils.misc import slug
from clldutils.clilib import PathType
from clldutils.path import md5


def get_checksum(obj, md5sum) -> str:
    """Get the md5 hash for the main bitstream of a CDSTAR object."""
    for bs in obj.bitstreams:
        if bs.md5 == md5sum:
            return bs.md5

    for bs in obj.bitstreams:
        if slug(bs.id).startswith(slug(obj.metadata['path'])):
            return bs.md5
    raise ValueError(obj.metadata)


def register(parser):  # pylint: disable=C0116
    parser.add_argument('upload_path', type=PathType(type='dir'))
    parser.add_argument('--dry-run', action='store_true', default=False)


def run(args):  # pylint: disable=C0116
    supported_types = {'imagefile': ['png', 'gif', 'jpg', 'jpeg', 'tif', 'tiff'],
                       'pdffile': ['pdf'],
                       'moviefile': ['mp4'],
                       'audiofile': ['mp3']}

    with args.api.get_catalog() as cat:
        name_uid_map = {obj.metadata['path']: obj for obj in cat}

        for ifn in sorted(args.upload_path.iterdir()):
            if ifn.name == 'README':
                print('skipping README')
                continue

            fmt = ifn.suffix[1:].lower()
            meta_type = None
            for t, suffixes in supported_types.items():
                if fmt in suffixes:
                    meta_type = t
                    break
            if meta_type is None:
                print(f'No supported media format - skipping {ifn}')
                continue

            if ifn.name in name_uid_map:
                cat_obj_id = name_uid_map[ifn.name].id
                md5sum = get_checksum(name_uid_map[ifn.name], md5(ifn))
                if md5(ifn) != md5sum:
                    print(f'{ifn.name}: object {cat_obj_id} exists - will be deleted')
                    if args.dry_run:
                        continue
                    cat.delete(cat_obj_id)
                else:
                    continue

            if args.dry_run:
                continue
            md = {
                'collection': 'amsd',
                'name': str(ifn.stem),
                'type': meta_type,
                'path': str(ifn.name)
            }
            # Create the new object
            for (fname, created, obj) in cat.create(str(ifn), md):
                args.log.info(
                    '%s -> %s object %s', fname, 'new' if created else 'existing', obj.id)
