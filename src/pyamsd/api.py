"""
Functionality to access data in the AMSD data repository.
"""
import os
import shutil
import pathlib
import collections
from typing import Optional

from csvw.dsv import reader
from clldutils.apilib import API
from clldutils import jsonlib
from cdstarcat import Catalog


class Amsd(API):
    """Programmatic access to objects in the AMSD data repository."""
    @property
    def media_catalog_path(self) -> pathlib.Path:
        """The location of the media catalog."""
        return self.repos / 'images' / 'catalog.json'

    @property
    def media_catalog(self) -> dict[str, dict]:
        """The media catalog as python dict read from JSON."""
        return jsonlib.load(self.media_catalog_path)

    def get_catalog(self) -> Catalog:
        """The media catalog for AMSD."""
        return Catalog(
            self.media_catalog_path,
            cdstar_url=os.environ.get('CDSTAR_URL', 'https://cdstar.eva.mpg.de'),
            cdstar_user=os.environ.get('CDSTAR_USER'),
            cdstar_pwd=os.environ.get('CDSTAR_PWD'),
        )

    @property
    def rows(self) -> list[collections.OrderedDict[str, str]]:
        """The rows of the AMSD data file exported from OCCAMS."""
        return list(reader(self.repos / 'org_data' / 'records.tsv', delimiter='\t', dicts=True))

    def validate(self, source_path: Optional[pathlib.Path] = None):
        """Validates the links between CSV data and media files."""
        media = set(v['metadata']['path'] for v in self.media_catalog.values())
        missing = collections.Counter()

        for row in self.rows:
            if row['Linked Filename']:
                for name in row['Linked Filename'].split(';'):
                    name = name.strip()
                    if name:
                        if name not in media:
                            print(f'missing: {name}')
                            missing.update([name])
        if source_path:
            target_path = str(self.repos / 'mediafiles' / 'upload')
        for i, (k, v) in enumerate(sorted(missing.items(), key=lambda i: (-i[1], i[0]))):
            if source_path:
                p = source_path / k
                if p.exists():
                    shutil.copy2(str(p), target_path)
                    print('copied ', k)
                else:
                    print('ERROR - not found in source path', k)
                continue
            if i == 0:
                print('Missing files:')
            print(f'{k} -- {v}x')
