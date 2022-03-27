from itertools import chain

import pytest

from wardreport import lib


def test_year():
    """
    Test that the year can be overwritten during testing.  If this test fails, let me know where you
    got that time machine.
    """
    assert lib.get_current_year() != 1900
    lib.set_test_year(1900)
    assert lib.get_current_year() == 1900


def test_partition():
    assert lib.partition(lambda i: not i % 2, range(10)) == ([0, 2, 4, 6, 8], [1, 3, 5, 7, 9])


def test_member_splitter(members):
    members, non_members = lib.member_splitter(members)
    assert len(members) == 25
    assert len(non_members) == 19


def test_adult_splitter(members):
    adults, non_adults = lib.adult_splitter(members)
    assert all(i['age'] >= 18 for i in adults)
    assert all(i['age'] < 18 for i in non_adults)


def test_male_splitter(members):
    males, females = lib.male_splitter(members)
    assert all([i['sex'] == 'M' for i in males])
    assert all([i['sex'] == 'F' for i in females])


def test_household_grouper(members):
    households = lib.household_grouper(members)
    assert len(households) == 25


def test_multi_partition(members):
    # Partition children by age.
    _, children = lib.adult_splitter(members)

    predicates = [
        lambda i: i['age'] <= 2,
        lambda i: 2 < i['age'] <= 7,
        lambda i: i['age'] >= 8,
    ]
    two_or_less, three_to_seven, over_eight = lib.multi_partition(predicates, children)
    assert all(i['age'] <= 2 for i in two_or_less)
    assert max(i['age'] for i in two_or_less) == 2
    assert min(i['age'] for i in two_or_less) == 0
    assert len(two_or_less) == 4

    assert all(2 < i['age'] <= 7 for i in three_to_seven)
    assert max(i['age'] for i in three_to_seven) == 7
    assert min(i['age'] for i in three_to_seven) == 3
    assert len(three_to_seven) == 4

    assert len(over_eight) == 7
    assert all(i['age'] >= 8 for i in over_eight)
    assert max(i['age'] for i in over_eight) == 17
    assert min(i['age'] for i in over_eight) == 8

    # All children were in their group.
    assert len(list(chain(two_or_less, three_to_seven, over_eight))) == len(children)


def test_calling_finder(members, callings):
    """
    `calling_finder` will return the calling of the member, or None if they have no calling.
    """
    by_id = lib.callings_by_member_id(callings)
    assert len(by_id) == 4

    calling_finder = lib.calling_finder_maker(callings)
    expected = [
        8453335106,
        9156228629,
        1868128949,
        5663696836
    ]
    assert [i['memberId'] for i in map(calling_finder, members) if i] == expected


def test_calling_splitter(members, calling_finder):
    """
    Members can be split by their calling status.
    """
    called, not_called = lib.calling_splitter(calling_finder, members)
    assert len(called) == 4
    assert len(not_called) == 40
    assert len(called) + len(not_called) == len(members)


def test_priesthood_grouper(members):
    """
    Members can be grouped by their priesthood.
    """
    males, _ = lib.male_splitter(members)
    priesthood_groups = lib.priesthood_grouper(males)
    priesthood_expected = [
        ('HIGH_PRIEST', ['5b35df49-afd5-4835-a692-c368cbd9afe9', '272c3d61-af50-40d3-8dfd-053191daca4e']),
        ('ELDER', ['fde732f0-20cb-44d0-b0a7-733f50fd3534', 'b37174d2-f04f-4a3b-a55f-3cdec8a973e6']),
        ('PRIEST', ['11055f0f-5898-4c24-8e60-95967095dd39']),
        ('TEACHER', ['9c3311e7-5687-43dd-a108-7193c2d22c60', '5823d9bb-28d4-4184-b1a1-b298acc0a3a0',
                     'a5391200-c247-4aa2-83cf-b69c6c7650e3']),
        ('DEACON', ['17883d65-b8c3-4c97-9b93-ac7290f64314']),
        ('UNORDAINED', ['67b6a160-e627-4495-96df-d04b3a490ff6', 'a0e15684-4ab5-4af5-98de-ffd2a9d29afe',
                        '1dd58755-69d0-4358-bb12-6e5fb5c12ba3', '37b4e1c5-e605-44c3-b1cc-c6552472426a',
                        '3454913b-8e7a-4740-a6ef-6386accb321d', 'ead4d935-f601-47bf-94f7-adc71c122e48',
                        '77fd036f-29e4-4a83-b31e-a36205ef1757', '773bd00b-a606-4e3a-94cc-cbc225337f92',
                        'f7fb3eb2-bf60-439b-8125-6303a7f42d45', '54a143f8-aa22-4e14-a4d7-66a751fac92d',
                        'be803eb8-26cf-4a3e-9a04-08d570d95db5', '69ceb2ef-fe54-4ef3-b6e8-b4e265c3b84b']),
    ]
    for priesthood, expected in priesthood_expected:
        assert [i['uuid'] for i in priesthood_groups[priesthood]] == expected

    # Priesthood grouper can be used on boys as well.
    _, boys = lib.adult_splitter(males)
    priesthood_groups = lib.priesthood_grouper(boys)
    priesthood_expected = [
        ('HIGH_PRIEST', []),
        ('ELDER', []),
        ('PRIEST', []),
        ('TEACHER', ['a5391200-c247-4aa2-83cf-b69c6c7650e3']),
        ('DEACON', []),
        ('UNORDAINED', ['a0e15684-4ab5-4af5-98de-ffd2a9d29afe', '77fd036f-29e4-4a83-b31e-a36205ef1757',
                        '773bd00b-a606-4e3a-94cc-cbc225337f92', 'f7fb3eb2-bf60-439b-8125-6303a7f42d45',
                        '54a143f8-aa22-4e14-a4d7-66a751fac92d', 'be803eb8-26cf-4a3e-9a04-08d570d95db5',
                        '69ceb2ef-fe54-4ef3-b6e8-b4e265c3b84b']),
    ]
    for priesthood, expected in priesthood_expected:
        assert [i['uuid'] for i in priesthood_groups[priesthood]] == expected, f'Expected {priesthood} is wrong'


@pytest.mark.parametrize('top,bottom,expected', [
    (2, 1, '200%'),
    (1, 1, '100%'),
    (1, 2, '50%'),
    (0, 2, '0%'),
]
                         )
def test_percent_str(top, bottom, expected):
    assert lib.percent_str(top, bottom) == expected


def test_single(members):
    singles, not_singles = lib.single_splitter(members)
    singles = list(singles)
    assert all(i['isSingleAdult'] or i['isYoungSingleAdult'] for i in singles)
    assert all(not i['isSingleAdult'] and not i['isYoungSingleAdult'] for i in not_singles)
    assert len(singles) == 12

    single_18, single_31, single_46 = lib.singles_by_age(members)
    assert len(single_18) == 2
    assert len(single_31) == 1
    assert len(single_46) == 9


def test_recommend(members, recommend_status):
    recommend_finder = lib.recommend_finder_maker(recommend_status)
    endowed, not_endowed = lib.endowed_splitter(recommend_finder, members)
    assert len(endowed) == 29
    assert len(not_endowed) == 15
    assert len(endowed) + len(not_endowed) == len(members)

    recommend_groups = lib.recommend_status_grouper(recommend_status)
    active = recommend_groups['ACTIVE']
    canceled = recommend_groups['CANCELED']
    expired_less_than_1_month = recommend_groups['EXPIRED_LESS_THAN_1_MONTH']
    expired_less_than_3_month = recommend_groups['EXPIRED_LESS_THAN_3_MONTHS']
    expired_over_3_months = recommend_groups['EXPIRED_OVER_3_MONTHS']
    expiring_next_month = recommend_groups['EXPIRING_NEXT_MONTH']
    expiring_this_month = recommend_groups['EXPIRING_THIS_MONTH']
    lost_or_stolen = recommend_groups['LOST_OR_STOLEN']

    assert len(active) == 3
    assert len(canceled) == 3
    assert len(expired_less_than_1_month) == 6
    assert len(expired_less_than_3_month) == 4
    assert len(expired_over_3_months) == 2
    assert len(expiring_next_month) == 7
    assert len(expiring_this_month) == 1
    assert len(lost_or_stolen) == 3
