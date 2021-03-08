import pathlib

import pytest

from clldutils.path import copytree


@pytest.fixture
def repos(tmp_path):
    repos = tmp_path / 'amsd-data'
    copytree(pathlib.Path(__file__).parent / 'repos', repos)
    return repos
