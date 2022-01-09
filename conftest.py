import pathlib

import pytest

from wardreport import common

example_members_file = pathlib.Path('./test/example_members.json')


@pytest.fixture
def members():
    from test import examples
    return examples.members


@pytest.fixture
def callings():
    from test import examples
    return examples.callings


@pytest.fixture
def calling_finder(callings):
    return common.calling_finder_maker(callings)
