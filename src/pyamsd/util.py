import re

__all__ = ['fields', 'fields_not_in_sticks', 'dms2dec', 'sim']


# [separated table, old header, new header, split regex]
fields = [
    [0, 'AMSD ID', 'amsd_id', ''],
    [0, 'Title', 'title', ''],
    [1, 'Keywords', 'keywords', r' {2,}'],
    [0, 'Description', 'description', ''],
    [0, 'Creator of Object', 'obj_creator', ''],
    [0, 'Date Created', 'date_created', ''],
    [0, 'Notes on date created', 'note_place_created', ''],
    [0, 'Place Created', 'place_created', ''],
    [1, 'Item type', 'item_type', ''],
    [1, 'Subtype', 'item_subtype', ''],
    [1, 'Cultural region', 'cultural_region', ''],
    [1, 'Linguistic area', 'ling_area_1',
     r'Chirila\s*:\s*(.*?)  +Austlang\s*:\s*(.*?)\s*:(.*?)  +Glottolog\s*:\s*(.*)\s*'],
    [1, 'Linguistic area 2', 'ling_area_2',
     r'Chirila\s*:\s*(.*?)  +Austlang\s*:\s*(.*?)\s*:(.*?)  +Glottolog\s*:\s*(.*)\s*'],
    [1, 'Linguistic area 3', 'ling_area_3',
     r'Chirila\s*:\s*(.*?)  +Austlang\s*:\s*(.*?)\s*:(.*?)  +Glottolog\s*:\s*(.*)\s*'],
    [0, 'Notes on Linguistic area(s)', 'notes_ling_area', ''],
    [0, "Term for 'message stick' (or related) in language", 'stick_term', ''],
    [0, 'Message', 'message', ''],
    [0, 'Motifs', 'motifs', ''],
    [0, 'Motif transcription', 'motif_transcription', ''],
    [1, 'Semantic domain', 'sem_domain', r' {2,}'],
    [0, 'Dimension 1 (mm)', 'dim_1', ''],
    [0, 'Dimension 2 (mm)', 'dim_2', ''],
    [0, 'Dimension 3 (mm)', 'dim_3', ''],
    [1, 'Material', 'material', r' *, *|  +'],
    [1, 'Technique', 'technique', r' *, *'],
    [1, 'Source citation', 'source_citation', r'  +| *; '],
    [1, 'Source type', 'source_type', r'  +'],
    [0, 'Date Collected', 'date_collected', ''],
    [1, 'Institution/Holder: file', 'holder_file', r'  +'],
    [0, 'Institution/Holder: object identifier', 'holder_obj_id', ''],
    [0, 'Collector', 'collector', ''],
    [0, 'Place Collected', 'place_collected', ''],
    [0, 'Creator Copyright', 'creator_copyright', ''],
    [0, 'File Copyright', 'file_copyright', ''],
    [0, 'Latitude', 'lat', ''],
    [0, 'Longitude', 'long', ''],
    [0, 'Notes on coordinates', 'notes_coords', ''],
    [0, 'URL (collecting institution)', 'url_institution', ''],
    [0, 'URL (source document)', 'url_source_1', ''],
    [0, 'URL (source document 2)', 'url_source_2', ''],
    [0, 'IRN', 'irn', ''],
    [0, 'Notes', 'notes', ''],
    [1, 'Data entry (OCCAMS)', 'data_entry', r'  +'],
    [1, 'Linked Filename', 'linked_filenames', r' *; *']
]

fields_not_in_sticks = [
    'material',
    'technique',
    'keywords',
    'sem_domain',
    'linked_filenames',
    'item_type',
    'source_type',
    'source_citation'
]


def sim(s, t):
    if s == t:
        return 0
    elif len(s) == 0:
        return len(t)
    elif len(t) == 0:
        return len(s)
    v0 = [None] * (len(t) + 1)
    v1 = [None] * (len(t) + 1)
    for i in range(len(v0)):
        v0[i] = i
    for i in range(len(s)):
        v1[0] = i + 1
        for j in range(len(t)):
            cost = 0 if s[i] == t[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        for j in range(len(v0)):
            v0[j] = v1[j]
    return v1[len(t)]


def dms2dec(c):
    deg, min, sec, dir = re.split('[°\'"]', c)
    return round(
        (float(deg) + float(min) / 60 + float(sec) / 3600) * (
            -1 if dir.strip().lower() in ['w', 's'] else 1), 6)
