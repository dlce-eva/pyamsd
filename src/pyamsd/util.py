"""
Utilities related to parsing records.tsv.
"""
import os
import re
import pathlib
import itertools
import collections
import dataclasses
from typing import Optional, Any, Union

from Levenshtein import distance
from csvw.dsv import UnicodeWriter, reader
from cdstarcat.catalog import Object

__all__ = ['StickTable']

LING_AREA_COLS = ['chirila_name', 'austlang_code', 'austlang_name', 'glottolog_code']


@dataclasses.dataclass(frozen=True)
class Field:
    """Specification of a field or column in records.tsv and sticks.csv."""
    old_name: str
    new_name: str
    controlled_vocab: bool = False
    pattern: Optional[re.Pattern] = None

    @classmethod
    def from_data(
            cls,
            old_name: str,
            new_name: str,
            controlled_vocab: bool = False,
            pattern: Optional[str] = None):
        """Factory"""
        return cls(old_name, new_name, controlled_vocab, re.compile(pattern) if pattern else None)

    @property
    def is_ling_area(self) -> bool:
        """Whether this is one of the three linguistic area fields."""
        return bool(re.fullmatch(r'ling_area_\d+', self.new_name))

    @staticmethod
    def _ling_area_data(m):
        d = {k: m.group(k).strip() for k in LING_AREA_COLS}
        if re.search('[0-9]', d['austlang_name']):
            # The two patterns for Austlang codes/names have code and name flipped with respect to
            # each other.
            d['austlang_name'], d['austlang_code'] = d['austlang_code'], d['austlang_name']
        return [d[k] for k in LING_AREA_COLS]

    def split(self, col: str, linenr: int) -> list[str]:
        """Some fields allow multiple values and this is how they are split."""
        if self.is_ling_area:
            m = self.pattern.fullmatch(col)
            if m:
                return ['|'.join(self._ling_area_data(m))]
            print(f'Error: {self.new_name} in line {linenr} has wrong structure: {col}\n')
            return []
        return self.pattern.split(col)


LING_AREA_PATTERN = (
    r'Chirila\s*:\s*(?P<chirila_name>.*?)  '
    r'+Austlang\s*:\s*(?P<austlang_name>.*?)\s*(:|\()(?P<austlang_code>[^\)]*?)\)?  '
    r'+Glottolog\s*:\s*(?P<glottolog_code>.*)\s*')

FIELDS = [
    Field.from_data('AMSD ID', 'amsd_id'),
    Field.from_data('Title', 'title'),
    Field.from_data('Keywords', 'keywords', True, r' {2,}'),
    Field.from_data('Description', 'description'),
    Field.from_data('Creator of Object', 'obj_creator'),
    Field.from_data('Date Created', 'date_created'),
    Field.from_data('Notes on date created', 'note_place_created'),
    Field.from_data('Place Created', 'place_created'),
    Field.from_data('Item type', 'item_type', True),
    Field.from_data('Subtype', 'item_subtype', True),
    Field.from_data('State or territory', 'state_territory'),
    Field.from_data('Cultural region', 'cultural_region', True),
    Field.from_data('Linguistic area', 'ling_area_1', True, LING_AREA_PATTERN),
    Field.from_data('Linguistic area 2', 'ling_area_2', True, LING_AREA_PATTERN),
    Field.from_data('Linguistic area 3', 'ling_area_3', True, LING_AREA_PATTERN),
    Field.from_data('Notes on Linguistic area(s)', 'notes_ling_area'),
    Field.from_data("Term for 'message stick' (or related) in language", 'stick_term'),
    Field.from_data('Message', 'message'),
    Field.from_data('Motifs', 'motifs'),
    Field.from_data('Motif transcription', 'motif_transcription'),
    Field.from_data('Semantic domain', 'sem_domain', True, r' {2,}'),
    Field.from_data('Dimension 1 (mm)', 'dim_1'),
    Field.from_data('Dimension 2 (mm)', 'dim_2'),
    Field.from_data('Dimension 3 (mm)', 'dim_3'),
    Field.from_data('Material', 'material', True, r' *, *|  +'),
    Field.from_data('Technique', 'technique', True, r' *, *'),
    Field.from_data('Source citation', 'source_citation', True, r'  +| *; '),
    Field.from_data('Source type', 'source_type', True, r'  +'),
    Field.from_data('Date Collected', 'date_collected'),
    Field.from_data('Institution/Holder: file', 'holder_file', True, r'  +'),
    Field.from_data('Institution/Holder: object identifier', 'holder_obj_id'),
    Field.from_data('Collector', 'collector'),
    Field.from_data('Place Collected', 'place_collected'),
    Field.from_data('Creator Copyright', 'creator_copyright'),
    Field.from_data('File Copyright and ICIP', 'file_copyright'),
    Field.from_data('Latitude', 'lat'),
    Field.from_data('Longitude', 'long'),
    Field.from_data('Notes on coordinates', 'notes_coords'),
    Field.from_data('URL (collecting institution)', 'url_institution'),
    Field.from_data('URL (source document)', 'url_source_1'),
    Field.from_data('URL (source document 2)', 'url_source_2'),
    Field.from_data('IRN', 'irn', pattern=r' *; *'),
    Field.from_data('Related entries', 'related_entries', pattern=r'[ ,;]+'),
    Field.from_data('Notes', 'notes'),
    Field.from_data('Data entry (OCCAMS)', 'data_entry', True, r'  +'),
    Field.from_data('Linked Filename', 'linked_filenames', True, r' *; *'),
]


@dataclasses.dataclass
class AssociationTable:
    """Many-to-many relations between sticks and controlled vocabularies are stored here."""
    name: str
    data: list[tuple[int, int]] = dataclasses.field(default_factory=list)

    def write(self, raw_path):
        """Write the association table to a CSV file."""
        with UnicodeWriter(raw_path.joinpath('x_sticks_' + self.name + '.csv')) as writer:
            writer.writerow(['stick_pk', self.name + '_pk'])
            writer.writerows(self.data)


@dataclasses.dataclass
class ControlledVocab:
    """A controlled list of items appearing in a particular column in records.tsv."""
    name: str
    similarity: Optional[int] = None
    data: dict[str, int] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_name_and_similarity(cls, t: Union[str, tuple[str, int]]):
        """Initialize a named controlled vocabulary, optionally configuring similarity checking."""
        if isinstance(t, tuple):
            return cls(t[0], t[1])
        return cls(t)

    def pk(self, item: str) -> int:
        """Return the primary key of an item in the vocabulary."""
        if item not in self.data:
            self.data[item] = len(self.data) + 1
        return self.data[item]

    def check_similarity(self):
        """Check the similarity of the items to spot spelling mistakes, etc."""
        if self.similarity is None:
            return
        # look for similar entries
        check_sim = list(self.data.keys())
        for a, b in itertools.combinations(check_sim, 2):
            if distance(a, b) < self.similarity:
                print(f'sim check: {self.name}\n{a}\n{b}\n')

    def write(self, raw_path: pathlib.Path, images_objs: dict[str, Object]):
        """Write the data to a CSV file."""
        with UnicodeWriter(raw_path.joinpath(self.name + '.csv')) as writer:
            d = []
            if self.name == 'ling_area':
                d.append(['pk'] + LING_AREA_COLS)
                for k, v in self.data.items():
                    c, ac, an, g = re.split(r'\|', k)
                    if g == 'no code':
                        g = ''
                    d.append([v, c, ac, an, g])
            elif self.name == 'linked_filenames':
                d.append(['pk', 'name', 'oid', 'path'])
                for k, v in self.data.items():
                    k_ = os.path.splitext(k)[0]
                    if k_ in images_objs:
                        url_path = ''
                        for o in images_objs[k_].bitstreams:
                            if o.id not in ['thumbnail.jpg', 'web.jpg']:
                                url_path = o.id
                                break
                        if url_path == '':
                            print(f"no path found for {k}")  # pragma: no cover
                        d.append([v, k, images_objs[k_].id, url_path])
                    #else:
                    #    d.append([v, k, ''])
            else:
                d.append(['pk', 'name'])
                for k, v in self.data.items():
                    d.append([v, k])
            for item in d:
                writer.writerow(item)


@dataclasses.dataclass
class StickTable:
    """Object implementing conversion of OCCAMS export to a set of interrelated CSV files."""
    data: list[collections.OrderedDict[str, Any]] = dataclasses.field(default_factory=list)
    controlled_vocabularies: dict[str, ControlledVocab] = dataclasses.field(default_factory=dict)
    association_tables: dict[str, AssociationTable] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_records_tsv(cls, datafile: pathlib.Path) -> 'StickTable':
        """Intitalize with the data from the OCCAMS export."""
        res = cls()
        for name_and_similarity in [
            'keywords',
            'sem_domain',
            'linked_filenames',
            ('item_type', 2),
            ('item_subtype', 2),
            'state_territory',
            ('cultural_region', 2),
            ('material', 1),
            'technique',
            ('ling_area', 10),
            ('source_citation', 5),
            'source_type',
            ('holder_file', 4),
            ('data_entry', 2),
        ]:
            cv = ControlledVocab.from_name_and_similarity(name_and_similarity)
            res.controlled_vocabularies[cv.name] = cv
        header = [f.new_name for f in FIELDS]
        lcol = 0
        for row_index, row in enumerate(reader(datafile, delimiter='\t')):
            if row_index == 0:  # header
                lcol = len(row)
                for col_index, col in enumerate(row):
                    assert FIELDS[col_index].old_name == col, \
                        f'{FIELDS[col_index].old_name} vs. {col}'
                continue
            if lcol != len(row):
                if len(row) == lcol + 1 and row[-1] == '':
                    # records.tsv from occams seems to add an extra tab at the end of data rows.
                    row = row[:-1]
                else:  # pragma: no cover
                    if len(row) < lcol:
                        print(f'Error: probably new_line in cell in line {row_index + 1} - '
                              f'line has {len(row)} columns instead of {lcol}')
                    else:
                        print(f'Error: too many filled columns for line {row_index + 1}\n')
                    continue
            data = []
            for col_index, col_ in enumerate(row):
                if re.sub(r'[ ]+', '', col_.strip()) == '':
                    data.append('')
                else:
                    data.append(res._get_val(
                        col_.strip(),
                        FIELDS[col_index],
                        row_index + 1))
            res.data.append(collections.OrderedDict(zip(
                header,
                map(lambda s: s
                    .replace('<br/>', '@@!@@')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('&', '&amp;')
                    .replace('@@!@@', '<br/><br/>') if isinstance(s, str) else s, data))))
        return res

    def _get_val_regular(self, col: str, field: Field, linenr: int):
        if field.new_name in ['lat', 'long']:
            try:
                return dms2dec(col)
            except ValueError:
                print(f'Error: check lat/long notation in line {linenr} for "{col}\n"')
                return None
        return col

    def _get_val_regular_multivalued(self, col: str, field: Field):
        if field.new_name in ['related_entries', 'irn']:
            a = map(str.strip, field.split(col, None))
            a = [x for x in a if x.strip()]
            return ';'.join(a)
        print(f'Check init of field {field.new_name}\n')  # pragma: no cover
        return None  # pragma: no cover

    def _get_val_cv(self, col: str, field: Field):
        return self.controlled_vocabularies[field.new_name].pk(col)

    def _get_val_cv_multivalued(self,col: str, field: Field, linenr: int):
        ref_data = []
        for item_ in field.split(col, linenr):
            item = item_.strip()
            if field.is_ling_area:
                ref_data.append(self.controlled_vocabularies['ling_area'].pk(item))
            elif field.new_name in ['holder_file']:
                ref_data.append(self.controlled_vocabularies[field.new_name].pk(item))
            else:
                pk = self.controlled_vocabularies[field.new_name].pk(item)
                if pk not in ref_data:
                    ref_data.append(pk)
                    # dfkey = 'x_sticks_' + field.new_name
                    assoc = self.association_tables.get(field.new_name)
                    if not assoc:
                        assoc = AssociationTable(field.new_name)
                        self.association_tables[field.new_name] = assoc
                        # assoc.data.append(['stick_pk', field.new_name + '_pk'])
                    assoc.data.append((linenr - 1, pk))

        # save ids to related table as semicolon separated lists of ids
        return ';'.join(map(str, ref_data))

    def _get_val(self, col: str, field: Field, linenr: int):
        lowercase_fields = [
            'material',
            'technique',
            'keywords',
            'sem_domain',
            'item_type',
            'source_type',
        ]
        if field.new_name in lowercase_fields:
            col = col.lower()
        if not field.controlled_vocab:
            if not field.pattern:
                return self._get_val_regular(col, field, linenr)
            # With split regex:
            return self._get_val_regular_multivalued(col, field)
        # With controlled vocab:
        if not field.pattern:
            return self._get_val_cv(col, field)
        return self._get_val_cv_multivalued(col, field, linenr)

    def write(self, raw_path: pathlib.Path, images_objs: dict[str, Object]):
        """Write the data to a set of related CSV files."""
        with UnicodeWriter(raw_path / 'sticks.csv') as writer:
            for i, stick in enumerate(self.data):
                if i == 0:
                    writer.writerow(['pk'] + list(stick.keys()))
                writer.writerow([str(i + 1)] + list(stick.values()))
        for cv in self.controlled_vocabularies.values():
            cv.write(raw_path, images_objs)
        for assoc in self.association_tables.values():
            assoc.write(raw_path)

    def check(self):
        """Run some consistency checks on the data."""
        # look for similar entries
        for cv in self.controlled_vocabularies.values():
            cv.check_similarity()

        # look for unique AMSD IDs
        unique_ids = collections.Counter(s['amsd_id'] for s in self.data if s['amsd_id'])
        unclear_ids = set()
        for k, v in unique_ids.most_common():
            if v > 1:
                print(f'AMSD ID check: {k} occurs {v} times\n')
                unclear_ids.add(k)

        # check related_entries
        for i, s in enumerate(self.data):
            if s.get('related_entries'):
                for rid in s['related_entries'].split(';'):
                    prefix = f'Related entry ID ::{rid}:: in line {i + 1}'
                    if rid not in unique_ids:
                        print(f'{prefix} not found as AMSD ID\n')
                    if rid == s['amsd_id']:
                        print(f'{prefix} refers to itself\n')
                    if rid in unclear_ids:
                        print(f'{prefix} is marked as occurring more than once\n')


def dms2dec(c: str) -> Optional[float]:
    """Convert a geographic dimension from a string representation to a float."""
    try:
        return float(c)
    except ValueError:
        deg, min_, sec, dir_ = re.split(r'[°\'"]\s*', c.strip())
        if dir_ == '':
            if deg.startswith('-'):
                dir_ = 'w'
                deg = deg[1:]
        return round(
            (float(deg) + float(min_) / 60 + float(sec) / 3600) * (
                -1 if dir_.strip().lower() in ['w', 's'] else 1), 6)
