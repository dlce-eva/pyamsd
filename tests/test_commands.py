import shlex
import pathlib

from pyamsd.__main__ import main


def _main(cmd, **kw):
    main(shlex.split(cmd), **kw)


def test_check(repos, capsys):
    _main('--repos {} check'.format(repos))
    capsout = capsys.readouterr().out
    assert 'PRM-1989.46.3_01.png' in capsout


def test_to_csv_check(repos, capsys):
    _main('--repos {} to_csv check'.format(repos))
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
    assert len(list(raw_dir .glob('*.csv'))) == 22
