import pathlib

import pytest

from clldutils.path import copytree


@pytest.fixture
def tmppath(tmpdir):
    return pathlib.Path(str(tmpdir))


@pytest.fixture
def repos(tmppath):
    repos = tmppath / 'amsd-data'
    copytree(pathlib.Path(__file__).parent / 'repos', repos)
    return repos
