import pathlib
import shutil
import pytest


@pytest.fixture
def repos(tmp_path):
    repos = tmp_path / 'amsd-data'
    shutil.copytree(pathlib.Path(__file__).parent / 'repos', repos)
    return repos
