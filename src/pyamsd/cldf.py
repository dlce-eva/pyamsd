"""
Functionality implementing CLDF creation from pre-processed AMSD data in org_data.
"""
import logging
import pathlib
import re
import shutil
import argparse
import functools
import mimetypes
import dataclasses
import urllib.request
from typing import Literal, get_args, Optional

from clldutils.coordinates import Coordinates
from clldutils.misc import nfilter
from clldutils.jsonlib import load
from cldfbench import Dataset as BaseDataset

StateTerritoryType = Literal[
    'New South Wales', 'Victoria', 'Northern Territory', 'Western Australia', 'South Australia',
    'Queensland']
ItemType = Literal[
    'message stick found in situ',
    'message stick in a collection',
    'message stick in a private collection',
    'message stick from a private sale',
    'image of a message stick (artefact missing)',
    'footage of a message stick',
    'image of a message stick and messenger',
    'image of a message stick accessory and messenger',
    'text reference',
    'positive text reference',
    'lexical item',
    'message stick accessory',
    'negative text reference',
    'fictional message stick',
]
ItemSubtype = Literal[
    'traditional',
    'traditional_context',
    'political',
    'unknown',
    'replicative_traditional',
    'story',
    'replicative_artistic',
    'replicative',
]


def year_collected(s) -> Optional[int]:
    """
    Extract a year from the text provided as date_collected.
    """
    if not s:
        return None
    if s in (
        'Acquisition details unknown.',
        'Acquisition date: unknown',
        'Unknown',
    ):
        return None  # pragma: no cover
    if s.endswith('Feb 27'):
        return 1927  # pragma: no cover
    if s.endswith('Tausch, 87'):
        return 1987  # pragma: no cover
    m = re.search('(?P<year>[12][0-9]{3})', s)
    assert m, s
    return int(m.group('year'))


def norm_latlon(lat: str, lon: str) -> tuple[float, float]:
    """Convert geo-coordinate from string to pair of floats."""
    c = Coordinates(
        lat.replace("'", '\u2032').replace('"', '\u2033'),
        lon.replace("'", '\u2032').replace('"', '\u2033'),
        format='degminsec')
    return c.latitude, c.longitude


def norm_row(row: dict[str, str]) -> dict[str, str]:
    """Remove HTML markup in values."""
    if None in row:
        del row[None]

    def norm_value(v):
        try:
            v = v.replace('<br/><br/>', '\n')
        except AttributeError as e:
            raise ValueError(v) from e
        assert not re.search(r'<[a-z]]', v), v
        return v

    return {k: norm_value(v) for k, v in row.items()}


@dataclasses.dataclass
class Stick:  # pylint: disable=R0902
    """
    The AMSD has the strict structure of one discrete item per database entry. But within each
    entry, a single item may have multiple sources informing it and more than one representation,
    for example, an official museum photograph, a hand-drawn sketch in a notebook, an illustration
    in a published article, etc. The core item types are labelled as follows, with counts accurate
    at the time of publication:
    - message stick in a collection (N = 1197),
    - message stick in a private collection (N = 70),
    - message stick from a private sale (N = 49),
    - image of a message stick (artefact missing) (N = 170),
    - footage of a message stick (N = 6) and
    - image of a message stick and messenger (N = 5).

    Three additional item types are associated with indirect sources evidence for message stick use.
    These are:
    - positive text reference (N = 19) referring to an observation of message stick use in a
      particular time and place recorded in an archive,
    - lexical item (N = 10) meaning an Indigenous term for message stick from an identifiable
      Australian language, and
    - message stick accessory (N = 4) referring to paraphernalia connected to a message stick such
      as cleft carrying sticks.

    The final two item types are
    - negative text reference (N = 5) recording an archival observation that no message sticks are
      used by a particular group or in a particular territory at a specific time in history, and
    - fictional message stick (N = 22) for imaginative or artistic representations of message
      sticks that are not known to have existed but which may have a bearing on the cultural
      history of these objects.

    Thus, in terms of plotting the distribution of message sticks, the final two item types must be
    excluded from raw counts, although negative text reference may be used to identify historical
    absences. These item types are designed to capture the range of data types that contribute to
    the dataset as a whole, but may overlap.
    """
    pk: str
    amsd_id: str
    title: str
    keywords: str
    description: str
    obj_creator: str
    date_created: Optional[int]
    note_place_created: str  # A misnomer, it's note_date_created
    place_created: str
    item_type: Optional[ItemType]
    item_subtype: Optional[ItemSubtype]
    state_territory: list[StateTerritoryType]
    cultural_region: str
    ling_area_1: str
    ling_area_2: str
    ling_area_3: str
    notes_ling_area: str
    stick_term: str
    message: str
    motifs: str
    motif_transcription: str
    sem_domain: list[str]
    dim_1: str
    dim_2: str
    dim_3: str
    material: list[str]
    technique: list[str]
    source_citation: list[str]
    source_type: list[str]
    date_collected: str
    holder_file: str
    holder_obj_id: str
    # collector: NULL: source unrecorded; Source unrecorded
    collector: str
    place_collected: str
    creator_copyright: str  # This is empty for all items!
    file_copyright: str
    lat: float
    long: float
    notes_coords: str
    url_institution: str
    url_source_1: str
    url_source_2: str
    irn: str  # No idea what this is.
    related_entries: list[str]  # self-referential, list-valued foreign key.
    # Model as additional table "related", collect clusters!
    notes: str
    data_entry: list[str]  # controlled vocab
    linked_filenames: str
    year_collected: Optional[int] = None

    @staticmethod
    def resolve(row, what: str, ds: 'Dataset', multiple: bool = True, null=None):
        """Resolve references to entries in a controlled vocabulary to the vocab items."""
        null = null or []
        items = ds.items(what)
        if multiple:
            row[what] = [items[k] for k in row[what].split(';') if k and items[k] not in null]
        else:
            if row[what]:
                row[what] = None if items[row[what]] in null else items[row[what]]

    @classmethod
    def from_row(cls, ds, row):
        """Initialize a Stick with the data in a row of raw/sticks.csv."""
        row = norm_row(row)
        item_type_map = {
            r['pk']: r['name'] for r in ds.raw_dir.read_csv('item_type.csv', dicts=True)}
        row['item_type'] = item_type_map.get(row['item_type'])
        if row['item_type']:
            for cmt in ('(missing an object number)', '(donated)'):
                row['item_type'] = row['item_type'].replace(cmt, '')
            row['item_type'] = row['item_type'].strip()
        cls.resolve(row, 'cultural_region', ds, multiple=False)
        row['cultural_region'] = {
            'Queensland': 'QLD',
            'nt_ca': 'NT_CA',
            'WA_kimberley': 'WA_Kimberley',
            'Victoria': 'VIC',
            'Pilbara': 'WA_Pilbara',
            'wa_kimberley': 'WA_Kimberley',
            'Central Australia': 'NT_CA',
            'Central Australia / western desert': 'NT_CA / WD',
        }.get(row['cultural_region'], row['cultural_region'])

        cls.resolve(row, 'data_entry', ds)
        # - holder_file
        cls.resolve(row, 'keywords', ds)
        cls.resolve(row, 'item_subtype', ds, multiple=False, null=['unknown'])
        # - linked_filenames multiple
        cls.resolve(row, 'material', ds)
        cls.resolve(row, 'technique', ds)
        cls.resolve(row, 'sem_domain', ds)
        cls.resolve(row, 'source_citation', ds)
        cls.resolve(row, 'source_type', ds)
        return cls(**row)

    def __post_init__(self):  # pylint: disable=R0912,R0915
        # Fix cases of information in the wrong fields:
        if self.id == 'MEG_ETHOC_011610':  # self.pk == '1600':  #
            self.notes_coords, self.url_source_1 = self.url_source_1, ''
        elif self.id == 'FMC132100_1':  # self.pk == '1702':  #
            self.item_type, self.place_created = self.place_created, ''
        elif self.id == 'AMus_E013406':  # self.pk == '748':  #
            self.state_territory, self.place_created = 'Queensland', ''
        #elif self.id == 'JWC1878':  # self.pk == '1373':  #
        #    self.item_type, self.item_subtype = self.item_subtype.lower(), ''
        elif self.id == 'BERNDT1946_0003_3':  # self.pk == '1044':  #
            self.motifs, self.sem_domain = '', self.motifs.split()
        elif self.id == 'SAM_A_77523':  # self.pk == '569':  #
            self.lat, self.long = norm_latlon(self.place_collected, self.creator_copyright)
            self.place_collected, self.creator_copyright = None, None

        self.year_collected = year_collected(self.date_collected)

        if self.collector.lower() == 'source unrecorded':
            self.collector = None

        if self.lat:
            self.lat = float(self.lat)
        if self.long:
            self.long = float(self.long)

        if self.title.startswith('A message stick'):
            if 'Museum' in self.title and not self.item_type:
                self.item_type = 'message stick in a collection'
            elif any(s in self.title for s in ('on eBay', 'sold via')):
                self.item_type = 'message stick from a private sale'
        if self.item_type:
            self.item_type = self.item_type.lower()
            assert self.item_type in get_args(ItemType), self.item_type
        if self.item_subtype:
            assert self.item_subtype in get_args(ItemSubtype), self.item_subtype

        self.amsd_id = self.amsd_id.replace(' ', '')
        self.url_institution = self.url_institution.replace('&amp;', '&')
        if self.url_institution:
            if self.url_institution.startswith('ark:'):
                self.url_institution = 'https://n2t.net/' + self.url_institution
            assert self.url_institution.startswith('http'), self.url_institution
        if self.date_created == 'Unknown':  # pragma: no cover
            self.date_created = None
        if self.date_created == '1930s':  # pragma: no cover
            self.date_created = 1930
        if self.date_created == '1895; AMus pdf date':  # pragma: no cover
            self.date_created = 1895
            self.note_place_created += ' (AMus pdf date)'
        if isinstance(self.date_created, str) and re.fullmatch(
                r'[0-9]{4}-[0-9]+-[0-9]+', self.date_created):
            self.date_created = self.date_created.split('-')[0]  # pragma: no cover
        if self.date_created == '1948 (accessioned 1952)':  # pragma: no cover
            self.date_created, self.note_place_created = 1948, 'accessioned 1952'
        if self.date_created:
            self.date_created = int(self.date_created)

        self.state_territory = {
            "New South Wales": ["New South Wales"],
            "Northern Territory": ["Northern Territory"],
            "Northern Territory (?)": ["Northern Territory"],
            "Northern Territory, Australia, Australia": ["Northern Territory"],
            "NSW": ["New South Wales"],
            "NSW/QLD": ["New South Wales", "Queensland"],
            "NT": ["Northern Territory"],
            "QLD": ["Queensland"],
            "QLD/NSW": ["New South Wales"],
            "Queensland": ["Queensland"],
            "SA": ["South Australia"],
            "SA_unlocalisable": ["South Australia"],
            "VIC": ["Victoria"],
            "Victoria": ["Victoria"],
            "WA": ["Western Australia"],
            "Western Australia": ["Western Australia"],
            "Western Australia, Australia, Australia": ["Western Australia"],
        }.get(self.state_territory, [])
        assert all(s in get_args(StateTerritoryType) for s in self.state_territory), (
            self.state_territory)

    @property
    def urls(self) -> list[str]:
        """HTTP URLs listed in the two source_url fields."""
        res = []
        for s in [self.url_source_1, self.url_source_2]:
            ss = s.split()
            if len(ss) > 1:
                assert all(u.startswith('http') for u in ss), ss
                res.extend(ss)
            elif s:
                res.append(s)
        assert all(u.startswith('http') for u in res)
        return res

    @property
    def note_date_created(self) -> str:
        """An alias to correct the wrong field name."""
        return self.note_place_created

    @property
    def id(self) -> str:
        """Unique ID."""
        return self.amsd_id or f'amsd_{str(self.pk).rjust(5, "0")}'

    @property
    def linguistic_areas(self) -> list[str]:
        """The list of all linguistic areas mentioned in the three ling area fields."""
        return sorted(set(nfilter(getattr(self, f'ling_area_{i}', None) for i in range(1, 4))))

    @property
    def dimensions(self) -> list[str]:
        """
        Dimensions, collected from the 3 dim fields. We keep them as strings in order to be able
        to use a multi-valued CLDF dataset column.
        """
        dims = nfilter(getattr(self, f'dim_{i}', None) for i in range(1, 4))
        try:
            _ = [float(s) for s in dims]
            return dims
        except ValueError:  # pragma: no cover
            return []

    @property
    def dimensions_note(self) -> Optional[str]:
        """Whatever appears in dimension fields and cannot be interpreted as float."""
        dims = nfilter(getattr(self, f'dim_{i}', None) for i in range(1, 4))
        try:
            _ = [float(s) for s in dims]
            return None
        except ValueError:  # pragma: no cover
            # If any of the given dimensions cannot be interpreted as floating point number, we
            # shove the info given for all dimensions into a note.
            return '; '.join(dims)


class Dataset(BaseDataset):
    """The cldfbench dataset for AMSD."""
    dir = None
    id = "amsd"

    @functools.lru_cache(maxsize=10)
    def items(self, what: str) -> dict[str, str]:
        """The items of a controlled vocabulary."""
        return {r['pk']: r['name'] for r in self.raw_dir.read_csv(what + '.csv', dicts=True)}

    def cmd_download(self, args: argparse.Namespace):
        """
        Download files to the raw/
        """
        # FIXME: run conversion from records.tsv here!  # pylint: disable=W0511
        target_dir = self.dir / 'images' / 'media'
        target_dir.mkdir(exist_ok=True, parents=True)
        i = 0
        for oid, spec in load(self.dir / 'images' / 'catalog.json').items():
            for bitstream in spec['bitstreams']:
                tpath = target_dir.joinpath(oid, bitstream['bitstreamid'])
                if not tpath.exists():
                    i += 1
                    tpath.parent.mkdir(exist_ok=True)
                    urllib.request.urlretrieve(
                        f'https://cdstar.eva.mpg.de/bitstreams/{oid}/{bitstream["bitstreamid"]}',
                        tpath)
        args.log.info('%s bitstreams downloaded', i)

    def cmd_makecldf(self, args):
        self.schema(args.writer.cldf)
        glangs = {lg.id: lg for lg in args.glottolog.api.languoids()}

        for row in self.raw_dir.read_csv('ling_area.csv', dicts=True):
            glang = glangs.get(row['glottolog_code'])
            args.writer.objects['LanguageTable'].append(dict(  # pylint: disable=R1735
                ID=row['pk'],
                Name=f"{row['chirila_name']} / {row['austlang_name']}",
                Austlang_Code=row['austlang_code'],
                Glottocode=row['glottolog_code'] or None,
                Latitude=glang.latitude if glang else None,
                Longitude=glang.longitude if glang else None,
                ISO639P3code=glang.iso if glang else None,
            ))

        media = Media()
        for row in self.raw_dir.read_csv('linked_filenames.csv', dicts=True):
            res = media.add(row, self.dir / 'images' / 'media', self.cldf_dir, args.log)
            if res:
                args.writer.objects['MediaTable'].append(res)

        # Clusters of related sticks:
        related: list[set[str]] = []
        for row in self.raw_dir.read_csv('sticks.csv', dicts=True):
            if row['related_entries']:
                es = {e.strip() for e in row['related_entries'].split(';') if e.strip()}
                es.add(row['amsd_id'])
                for rel in related:
                    if any(e in rel for e in es):
                        rel |= es
                        break
                else:
                    related.append(es)
        related_dict = {str(i): rel for i, rel in enumerate(related, start=1)}

        for row in self.raw_dir.read_csv('sticks.csv', dicts=True):
            stick = Stick.from_row(self, row)
            rel = [k for k, v in related_dict.items() if stick.id in v]
            assert len(rel) < 2
            args.writer.objects['ContributionTable'].append(dict(  # pylint: disable=R1735
                ID=stick.id,
                Name=row['title'],
                Keywords=stick.keywords,
                Description=row['description'],
                Object_Creator=stick.obj_creator,
                Date_Created=stick.date_created,
                Note_Date_Created=stick.note_date_created,
                Place_Created=stick.place_created,
                Item_Type=stick.item_type,
                Item_Subtype=stick.item_subtype,
                State_Territory=stick.state_territory,
                Cultural_Region=stick.cultural_region,
                Linguistic_Areas=stick.linguistic_areas,
                Note_Linguistic_Areas=stick.notes_ling_area,
                # In theory, stick_term could go into a FormTable. But there are only 76, and
                # not very standardized.
                Stick_Term=stick.stick_term,
                Message=stick.message,
                Motifs=stick.motifs,
                Motif_Transcription=stick.motif_transcription,
                Semantic_Domains=stick.sem_domain,
                Dimensions=stick.dimensions,
                Note_Dimensions=stick.dimensions_note,
                Material=stick.material,
                Technique=stick.technique,
                Source_Citation=stick.source_citation,
                Source_Type=stick.source_type,
                Year_Collected=stick.year_collected,
                Note_Date_Collected=stick.date_collected,
                Holder_File=stick.holder_file,
                Holder_Object_ID=stick.holder_obj_id,
                Collector=stick.collector,
                Place_Collected=stick.place_collected,
                File_Copyright=stick.file_copyright,
                Latitude=stick.lat,
                Longitude=stick.long,
                Note_Coordinates=stick.notes_coords,
                URL_Institution=stick.url_institution,
                Source_URLs=stick.urls,
                Related=rel[0] if rel else None,
                Note=stick.notes,
                Data_Entry=stick.data_entry,
                Media_IDs=sorted(set(media.pk2id[pk] for pk in stick.linked_filenames.split(';')
                                     if pk and pk in media.pk2id)),
            ))

        for i, g in related_dict.items():
            args.writer.objects['related.csv'].append({'ID': i, 'Stick_IDs': g})

    def schema(self, cldf):
        """Create the dataset schema."""
        t = cldf.add_component(
            'LanguageTable',
            {
                'name': 'Austlang_Code',
                'valueUrl': 'https://aiatsis.gov.au/austlang/language/{Austlang_Code}',
            }
        )
        t.common_props['dc:description'] = 'Linguistic areas'
        cldf.add_component('MediaTable')
        ct = cldf.add_component(
            'ContributionTable',
            {
                'name': 'Item_Type',
                'dc:description': 'FIXME',
                'datatype': {'base': 'string', 'format': '|'.join(
                    re.escape(s) for s in get_args(ItemType))}
            },
            'Item_Subtype',
            {
                'name': 'State_Territory',
                'separator': '|',
                'datatype': {'base': 'string', 'format': '|'.join(
                    re.escape(s) for s in get_args(StateTerritoryType))}
            },
            'Cultural_Region',
            'Motifs',
            'Motif_Transcription',
            {
                'name': 'Keywords',
                'separator': '|',
            },
            'Object_Creator',
            {
                'name': 'Date_Created',
                'datatype': 'int',
                'dc:description': 'Year of creation. See also Note_Date_Created'
            },
            'Note_Date_Created',
            {
                'name': 'Linguistic_Areas',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#languageReference',
            },
            'Note_Linguistic_Areas',
            'Stick_Term',
            'Message',
            {
                'name': 'Dimensions',
                'dc:description': 'Dimensions of the message stick in mm.',
                'separator': ' ',
            },
            {
                'name': 'Note_Dimensions',
                'dc:description': 'A note specifying how to interpret dimensions.',
            },
            {
                'name': 'Material',
                'separator': '|',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(m) for m in self.items('material').values())},
            },
            {
                'name': 'Technique',
                'separator': '|',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(m) for m in self.items('technique').values())},
            },
            {
                'name': 'Source_Citation',
                'separator': '|',
                'datatype': 'string',
            },
            {
                'name': 'Source_Type',
                'separator': '|',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(m) for m in self.items('source_type').values())},
            },
            {'name': 'Year_Collected', 'datatype': 'integer'},
            'Note_Date_Collected',
            'Holder_File',
            'Holder_Object_ID',
            'Collector',
            'Place_Collected',
            'File_Copyright',
            cldf['LanguageTable', 'Latitude'].asdict(),
            cldf['LanguageTable', 'Longitude'].asdict(),
            'Note_Coordinates',
            {'name': 'URL_Institution', 'datatype': 'anyURI'},
            {
                'name': 'Source_URLs',
                'separator': ' ',
                'datatype': 'anyURI',
            },
            'Related',
            {
                'name': 'Note',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment',
            },
            {
                'name': 'Semantic_Domains',
                'separator': ' ',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(sd) for sd in self.items('sem_domain').values())},
            },
            {
                'name': 'Data_Entry',
                'separator': '|',
                'datatype': {
                    'base': 'string',
                    'format': '|'.join(re.escape(m) for m in self.items('data_entry').values())},
            },
            {
                'name': 'Media_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#mediaReference',
            },
        )
        cldf.add_table(
            'related.csv',
            {
                'name': 'ID',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
            },
            {
                'name': 'Stick_IDs',
                'separator': ' ',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#contributionReference',
            }
        )
        ct.add_foreign_key('Related', 'related.csv', 'ID')


@dataclasses.dataclass
class Media:
    """Object to keep track of linked media files, identified by CDSTAR oid."""
    pk2id: dict[str, str] = dataclasses.field(default_factory=dict)
    oids: set[str] = dataclasses.field(default_factory=set)

    def add(
            self,
            row: dict[str, str],
            media_dir: pathlib.Path,
            cldf_dir: pathlib.Path,
            log: logging.Logger
    ) -> Optional[dict[str, str]]:
        """Add a row from linked_filenames, optionally returning a row for MediaTable."""
        if row['oid'] in self.oids:
            self.pk2id[row['pk']] = row['oid']
            return None
        self.oids.add(row['oid'])
        if not (row['oid'] and row['path']):
            log.warning('Invalid filename linked: %s', row)
            return None
        src = media_dir / row['oid'] / row['path']
        if not src.exists():  # pragma: no cover
            log.error('Invalid path: %s', src)
            return None
        t, _ = mimetypes.guess_type(src.name)
        assert t, (t, src.name)
        target = cldf_dir / row['oid'][:7] / (row['oid'] + src.suffix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)
        self.pk2id[row['pk']] = row['oid']
        return dict(  # pylint: disable=R1735
            ID=row['oid'],
            Name=row['name'],
            Media_Type=t,
            Download_URL=str(target.relative_to(cldf_dir)),
        )
