import shlex
import pathlib

from pyamsd.__main__ import main


def _main(cmd, **kw):
    main(shlex.split(cmd), **kw)


def test_check(repos, capsys):
    _main('--repos {} check'.format(repos))
    capsout = capsys.readouterr().out
    assert 'PRM-1989.46.3_01.png' in capsout


def test_copy_media(repos):
    _main('--repos {0} copy_media {0}/images'.format(repos))
    assert (repos / 'mediafiles' / 'upload' / 'PRM-1989.46.3_01.png').exists()


def test_upload_media(repos, capsys):
    _main('--repos {0} upload_media {0}/mediafiles/upload'.format(repos))
    assert 'skipping' in capsys.readouterr().out


def test_to_csv_check(repos, capsys):
    _main('--repos {} to_csv --dry-run'.format(repos))
    raw_dir = repos / 'raw'
    assert raw_dir.exists()
    assert not (raw_dir / 'sticks.csv').exists()
    capsout = capsys.readouterr().out
    assert 'Piers kelly' in capsout


def test_to_csv(repos):
    _main('--repos {} to_csv'.format(repos))
    raw_dir = repos / 'raw'
    assert raw_dir.exists()
    assert (raw_dir / 'sticks.csv').exists()
    assert len(list(raw_dir .glob('*.csv'))) == 23
