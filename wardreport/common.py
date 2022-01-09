from collections import defaultdict
from datetime import datetime
from functools import partial
from itertools import tee, filterfalse
from typing import List, Dict, Tuple, Optional

TEST_YEAR = None
REAL_YEAR = datetime.now().year


def get_current_year():
    global TEST_YEAR
    return TEST_YEAR or REAL_YEAR


def set_test_year(year: int):
    global TEST_YEAR
    TEST_YEAR = year


def household_grouper(members: List[dict]) -> Dict:
    """
    Each member has a householdAnchorPersonUuid, group them by it.
    """
    households = defaultdict(lambda: list())
    for member in members:
        household_uuid = member['householdAnchorPersonUuid']
        households[household_uuid].append(member)
    return households


def year_age(member: dict) -> int:
    january_year = int(member['birth']['date']['calc'].split('-')[0])
    return get_current_year() - january_year


def partition(pred, iterable):
    """
    Use a predicate to partition entries into false entries
    and true entries.

    >>> is_even = lambda i: not i % 2
    >>> partition(is_even, range(10))
    ([0, 2, 4, 6, 8], [1, 3, 5, 7, 9])
    """
    t1, t2 = tee(iterable)
    return list(filter(pred, t2)), list(filterfalse(pred, t1))


member_splitter = partial(partition, lambda i: i['isMember'] is True)
adult_splitter = partial(partition, lambda i: int(i['age']) >= 18)
male_splitter = partial(partition, lambda i: i['sex'] == 'M')
youth_splitter = partial(partition, lambda i: 12 <= year_age(i) < 18)


def multi_partition(predicates: List[callable], iterable: List) -> Tuple[List, ...]:
    """
    Split an iterable into many partitions based on if they match one predicate.  If an object matches more than one
    predicate (or none) an error will be raised.
    """
    partitions = tuple(list() for _ in predicates)
    for member in iterable:
        match = False
        for idx, predicate in enumerate(predicates):
            if predicate(member) and not match:
                partitions[idx].append(member)
                match = True
        if not match:
            raise ValueError('Item did not match any predicates!')

    return partitions


single_splitter = partial(partition, lambda i: i['isSingleAdult'] or i['isYoungSingleAdult'])
_single_age_partition = partial(multi_partition, [lambda i: 18 <= i['age'] <= 30,
                                                  lambda i: 31 <= i['age'] <= 45,
                                                  lambda i: 46 <= i['age'],
                                                  lambda i: True,
                                                  ])


def singles_by_age(members: List[dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    single, _ = single_splitter(members)
    single_18, single_31, single_46, _ = _single_age_partition(single)
    return single_18, single_31, single_46


def callings_by_member_id(callings: List[dict]) -> dict:
    """
    Convert callings to a dictionary.  They key will be the member's `memberId`.
    """
    new_callings = {}
    for group in callings:
        for children in group['children']:
            for calling in children['callings']:
                new_callings[calling['memberId']] = calling

    return new_callings


def calling_finder_maker(callings: List[dict]):
    """
    Used to create a function which will find a member's calling, if any.

    :param callings: The callings list from the data.
    :return: callable
    """
    callings = callings_by_member_id(callings)

    def calling_finder(member: dict) -> Optional[dict]:
        legacy_member_id = member['legacyCmisId']
        return callings.get(legacy_member_id)

    return calling_finder


def calling_splitter(calling_finder: calling_finder_maker, members: List[dict]):
    """
    Split members by their calling status.
    :param calling_finder: the function returned by `calling_finder_maker`
    :param members:
    :return:
    """
    return partition(lambda i: calling_finder(i), members)


PRIESTHOODS = ('HIGH_PRIEST', 'ELDER', 'PRIEST', 'TEACHER', 'DEACON', 'UNORDAINED')


def priesthood_grouper(members):
    """
    Group members by their priesthood.
    """
    groups = {i: [] for i in PRIESTHOODS}
    for member in members:
        priesthood_office = member['priesthoodOffice']
        if priesthood_office in groups:
            groups[priesthood_office].append(member)
        else:
            groups['UNORDAINED'].append(member)

    return groups


def percent_str(top: int, bottom: int) -> str:
    percent = (top / bottom) * 100
    return '{:,.0f}%'.format(percent)
