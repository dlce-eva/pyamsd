"""
Parses data file 'org_data/records.tsv' into single csv files into 'raw'.
In addition it outputs given warnings while parsing. If you only want to check
the data integrity of data file 'org_data/records.tsv' then pass the argument
'--dry-run' -> amsd to_csv --dry-run.
"""
import os
import re
import collections

from csvw.dsv import reader, UnicodeWriter

from pyamsd.util import *  # noqa: F403


def register(parser):
    parser.add_argument(
        '--dry-run', action='store_true', default=False,
        help='Only check the data without generating csv files'
    )


def run(args):
    assert args.repos

    raw_path = args.repos / 'raw'
    if not raw_path.exists():
        raw_path.mkdir()

    csv_dataframe = {
        'sticks': [],
        'keywords': {},
        'sem_domain': {},
        'linked_filenames': {},
        'item_type': {},
        'item_subtype': {},
        'cultural_region': {},
        'material': {},
        'technique': {},
        'ling_area': {},
        'source_citation': {},
        'source_type': {},
        'holder_file': {},
        'data_entry': {},
    }

    datafile = args.repos / 'org_data' / 'records.tsv'

    pk_to_linenr = dict()

    lcol = 0
    for i, row in enumerate(reader(datafile, delimiter='\t')):
        data = []
        if i == 0:  # header
            lcol = len(row)
            data.append('pk')  # add pk
            for j, col in enumerate(row):
                data.append(fields[j][2].strip())
        else:
            data.append(i)  # add id    -    -1 due to spreadsheet app
            if lcol != len(row) - 1:
                print('Error: probably new_line in cell in line {} - line has {} columns instead of {}'.format(i+1, len(row), lcol))
                continue
            for j, col_ in enumerate(row):
                if j > lcol-1:
                    if col_.strip() != '':
                        print('Error: too many filled columns for line {0}\n'.format(i + 1))
                        continue
                if re.sub(r'[ ]+', '', col_.strip()) == '':
                    data.append('')
                else:
                    col = col_.strip()
                    if fields[j][2] in fields_not_in_sticks \
                            and fields[j][2] not in ['linked_filenames', 'source_citation']:
                        col = col.lower()
                    if fields[j][0] == 0 and len(fields[j][3]) == 0:
                        if fields[j][2] in ['lat', 'long']:
                            try:
                                data.append(dms2dec(col))
                            except ValueError:
                                print('Error: check lat/long notation in line {0} for "{1}\n"'.format(
                                    i + 1, col))
                                data.append(None)
                        else:
                            data.append(col)
                    elif fields[j][0] == 1 and len(fields[j][3]) == 0:
                        if col not in csv_dataframe[fields[j][2]]:
                            csv_dataframe[fields[j][2]][col] = len(csv_dataframe[fields[j][2]]) + 1
                        data.append(csv_dataframe[fields[j][2]][col])
                    elif fields[j][0] == 0 and len(fields[j][3]) > 1:
                        col_name = fields[j][2]
                        if col_name in ['related_entries', 'irn']:
                            a = map(str.strip, re.split(fields[j][3], col))
                            data.append(';'.join(a))
                        else:
                            print('Check init of field {}\n').format(col_name)
                    elif fields[j][0] == 1 and len(fields[j][3]) > 1:
                        ref_data = []
                        if re.match(r'^ling_area_\d+$', fields[j][2]):
                            try:
                                data_array = ["|".join([i.strip() for i in list(
                                    re.findall(fields[j][3], col)[0])])]
                            except IndexError:
                                print('Error: {0} in line {1} has wrong structure: {2}\n'.format(
                                    fields[j][2], i + 1, col))
                                data_array = []
                        else:
                            data_array = re.split(fields[j][3], col)
                        for item_ in data_array:
                            item = item_.strip()
                            col_name = fields[j][2]
                            if re.match(r'^ling_area_\d+$', col_name):
                                col_name = 'ling_area'
                                if item not in csv_dataframe[col_name]:
                                    csv_dataframe[col_name][item] = len(csv_dataframe[col_name]) + 1
                                ref_data.append(csv_dataframe[col_name][item])
                            elif col_name in ['holder_file']:
                                if item not in csv_dataframe[col_name]:
                                    csv_dataframe[col_name][item] = len(csv_dataframe[col_name]) + 1
                                ref_data.append(csv_dataframe[col_name][item])
                            else:
                                dfkey = 'x_sticks_' + col_name
                                if item not in csv_dataframe[col_name]:
                                    csv_dataframe[col_name][item] = len(csv_dataframe[col_name]) + 1
                                if not csv_dataframe[col_name][item] in ref_data:
                                    ref_data.append(csv_dataframe[col_name][item])
                                    if dfkey not in csv_dataframe:  # header
                                        csv_dataframe[dfkey] = []
                                        csv_dataframe[dfkey].append(['stick_pk', col_name + '_pk'])
                                    csv_dataframe[dfkey].append([i, csv_dataframe[col_name][item]])
                                    pk_to_linenr[csv_dataframe[col_name][item]] = i + 1
                        # save ids to related table as semicolon separated lists of ids
                        data.append(';'.join(map(str, ref_data)))
        csv_dataframe['sticks'].append(data)

    with args.api.get_catalog() as cat:
        images_objs = {obj.metadata['name']: obj for obj in cat}

    # look for similar entries
    for t, k in [('source_citation', 5), ('holder_file', 4), ('ling_area', 10), ('material', 1),
                 ('data_entry', 2), ('item_type', 2), ('item_subtype', 2), ('cultural_region', 2)]:
        check_sim = list(csv_dataframe[t].keys())
        for i in range(len(check_sim)):
            for j in range(i + 1, len(check_sim)):
                if sim(check_sim[i], check_sim[j]) < k:
                    print('sim check: {}\n{}\n{}\n'.format(t, check_sim[i], check_sim[j]))

    # look for unique AMSD IDs
    unique_ids_check = collections.defaultdict(int)
    for s in csv_dataframe['sticks']:
        if s[1].strip():
            unique_ids_check[s[1]] += 1
    unclear_ids = set()
    for k, v in unique_ids_check.items():
        if v > 1:
            print('AMSD ID check: {0} occurs {1} times\n'.format(k, v))
            unclear_ids.add(k)

    # check related_entries
    for i, s in enumerate(csv_dataframe['sticks']):
        if i > 0 and s[42].strip():
            rids = s[42].split(';')
            for rid in rids:
                if rid not in unique_ids_check:
                    print('Related entry ID {} in line {} not found as AMSD ID\n'.format(rid, i+1))
                if rid == s[1]:
                    print('Related entry ID {} in line {} refers to itself\n'.format(rid, i+1))
                if rid in unclear_ids:
                    print('Related entry ID {} in line {} is marked as occurring more than once\n'.format(rid, i+1))

    if not args.dry_run:
        for filename, data in csv_dataframe.items():
            with UnicodeWriter(raw_path.joinpath(filename + '.csv')) as writer:
                if type(data) is list:
                    for item in data:
                        writer.writerow(item)
                else:
                    d = []
                    if filename == 'ling_area':
                        d.append(['pk', 'chirila_name', 'austlang_code',
                                  'austlang_name', 'glottolog_code'])
                        for k, v in data.items():
                            c, ac, an, g = re.split(r'\|', k)
                            if g == 'no code':
                                g = ''
                            d.append([v, c, ac, an, g])
                    elif filename == 'linked_filenames':
                        d.append(['pk', 'name', 'oid', 'path'])
                        for k, v in data.items():
                            k_ = os.path.splitext(k)[0]
                            if k_ in images_objs:
                                url_path = ''
                                for o in images_objs[k_].bitstreams:
                                    if o.id not in ['thumbnail.jpg', 'web.jpg']:
                                        url_path = o.id
                                        break
                                if url_path == '':
                                    print("no path found for {}" .format(k_))
                                d.append([v, k, images_objs[k_].id, url_path])
                            else:
                                print("no image match for '{}' in line {}".format(k, pk_to_linenr.get(v, v)))
                                d.append([v, k, ''])
                    else:
                        d.append(['pk', 'name'])
                        for k, v in data.items():
                            d.append([v, k])
                    for item in d:
                        writer.writerow(item)
