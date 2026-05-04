import logging
import argparse

from pyamsd.cldf import Dataset


def test_makecldf(repos, mocker):
    class DS(Dataset):
        dir = repos

    ds = DS()
    ds._cmd_makecldf(argparse.Namespace(
        log=logging.getLogger(__name__),
        glottolog=mocker.MagicMock()))
