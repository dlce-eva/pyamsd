import pathlib

import pytest

from pyamsd.api import Amsd


@pytest.fixture
def api():
    return Amsd(pathlib.Path(__file__).parent / 'repos')


def test_catalog(api):
    assert "EAEA0-002A-2E89-2AAB-0" in api.media_catalog


def test_rows(api):
    assert len(api.rows) == 4


def test_validate(api, capsys):
    api.validate()
    out, _ = capsys.readouterr()
    assert 'Missing file' in out
