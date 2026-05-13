import pytest

from pyamsd.util import dms2dec, StickTable


def test_dms2dec():
    assert -2.033889, dms2dec("""2°2'2"W""")
    assert -13.5, dms2dec("-13.5")


@pytest.mark.parametrize(
    'items,inout',
    [
        ([dict(amsd_id='1', related_entries='1')], 'refers to itself'),
        ([dict(amsd_id='1', related_entries='1'), dict(amsd_id='1')], 'more than once'),
        ([dict(amsd_id='1', related_entries='2')], 'not found'),
    ]
)
def test_StickTable_check(capsys, items, inout):
    t = StickTable()
    t.data.extend(items)
    t.check()
    out, _ = capsys.readouterr()
    assert inout in out


def test_StickTable_from_records(repos):
    t = StickTable.from_records_tsv(repos / 'org_data' / 'records.tsv')
    assert len(t.data) == 5
