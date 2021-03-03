import pytest

from pyamsd.util import *


@pytest.mark.parametrize(
    's,t,res',
    [
        ('abc', 'abc', 0),
        ('abc', '', 3),
        ('', 'abc', 3),
        ('abc', 'cde', 3),
    ]
)
def test_sim(s, t, res):
    assert res == sim(s, t)


def test_dms2dec():
    assert pytest.approx(-2.0339, dms2dec("""2°2'2"W"""))
