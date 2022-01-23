import io
import re
import smtplib
import ssl
import sys
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from functools import partial
from itertools import tee, filterfalse
from typing import List, Dict, Tuple, Optional, Iterable

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


def recommend_finder_maker(recommend_status: List[dict]):
    """
    Creates a function which will return the endowment record of a member by their legacyCmisId.
    """
    recommends = {i['id']: i for i in recommend_status}

    def recommend_finder(member: dict) -> Optional[dict]:
        legacy_member_id = member['legacyCmisId']
        return recommends.get(legacy_member_id)

    return recommend_finder


def endowed_splitter(recommend_finder: recommend_finder_maker, members: List[dict]):
    return partition(lambda i: (r := recommend_finder(i)) and r['endowmentDate'], members)


STATUSES = (
    'ACTIVE',
    'CANCELED',
    'EXPIRED_LESS_THAN_1_MONTH',
    'EXPIRED_LESS_THAN_3_MONTHS',
    'EXPIRED_OVER_3_MONTHS',
    'EXPIRING_NEXT_MONTH',
    'EXPIRING_THIS_MONTH',
    'LOST_OR_STOLEN',
)


def recommend_status_grouper(recommend_status) -> Dict[str, List[dict]]:
    """
    Group members by their recommend status.
    """
    groups = {i: [] for i in STATUSES}
    for status in recommend_status:
        if recommend_status := status.get('recommendStatus'):
            groups[recommend_status].append(status)
    return groups


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


class MemberReport:

    def __init__(self, member_list, callings, recommend_status):
        self.member_list = member_list
        self.callings = callings
        self.recommend_status = recommend_status
        self.recommend_finder = recommend_finder_maker(recommend_status)
        self.calling_finder = calling_finder_maker(self.callings)

        self.data = dict()
        self.process_data()

    def process_data(self):
        """
        Calculate and summarize all member information.
        """
        members, non_members = member_splitter(self.member_list)

        predicates = [
            lambda i: i['age'] < 12,
            lambda i: 12 <= i['age'] <= 17,
            lambda i: i['age'] > 17,
        ]
        primary, young_people, adults = multi_partition(predicates, self.member_list)
        young_men, young_women = male_splitter(young_people)

        brethren, sisters = male_splitter(adults)
        brethren_with_callings, brethren_no_calling = calling_splitter(self.calling_finder, brethren)
        sisters_with_callings, sisters_no_calling = calling_splitter(self.calling_finder, sisters)

        bpg = priesthood_grouper(brethren)
        b_high_priest, b_elder, b_priest, b_teacher, b_deacon, b_unordained = bpg['HIGH_PRIEST'], \
                                                                              bpg['ELDER'], \
                                                                              bpg['PRIEST'], \
                                                                              bpg['TEACHER'], \
                                                                              bpg['DEACON'], \
                                                                              bpg['UNORDAINED']
        ypg = priesthood_grouper(young_men)
        y_priest, y_teacher, y_deacon, y_unordained = ypg['PRIEST'], ypg['TEACHER'], ypg['DEACON'], ypg['UNORDAINED']

        predicates = [
            lambda i: i['age'] <= 2,
            lambda i: 2 < i['age'] <= 7,
            lambda i: i['age'] >= 8,
        ]
        age_0_to_2, age_3_to_7, age_8_plus = multi_partition(predicates, primary)

        single_18, single_31, single_46 = singles_by_age(members)

        endowed, not_endowed = endowed_splitter(self.recommend_finder, adults)
        recommend_groups = recommend_status_grouper(self.recommend_status)

        self.data['members'] = len(members)
        self.data['non_members'] = len(non_members)
        self.data['households'] = len(household_grouper(self.member_list))
        self.data['primary'] = len(primary)
        self.data['adults'] = len(adults)
        self.data['young_women'] = len(young_women)
        self.data['sisters'] = len(sisters)
        self.data['sisters_with_callings'] = len(sisters_with_callings)
        self.data['sisters_no_calling'] = len(sisters_no_calling)
        self.data['young_men'] = len(young_men)
        self.data['young_men_aaronic'] = len(y_priest) + len(y_teacher) + len(y_deacon)
        self.data['young_men_unordained'] = len(y_unordained)
        self.data['brethren'] = len(brethren)
        self.data['brethren_with_callings'] = len(brethren_with_callings)
        self.data['brethren_no_calling'] = len(brethren_no_calling)
        self.data['brethren_melchizedek'] = len(b_elder) + len(b_high_priest)
        self.data['brethren_aaronic'] = len(b_priest) + len(b_teacher) + len(b_deacon)
        self.data['brethren_unordained'] = len(b_unordained)
        self.data['age_0_to_2'] = len(age_0_to_2)
        self.data['age_3_to_7'] = len(age_3_to_7)
        self.data['age_8_plus'] = len(age_8_plus)
        self.data['single_18'] = len(single_18)
        self.data['single_31'] = len(single_31)
        self.data['single_46'] = len(single_46)
        self.data['endowed'] = len(endowed)
        self.data['not_endowed'] = len(not_endowed)
        self.data.update({f'recommend_{k.lower()}': len(v) for k, v in recommend_groups.items()})
        self.data['current_recommend'] = self.recommend_active + \
                                         self.recommend_expiring_next_month + \
                                         self.recommend_expiring_this_month
        self.data['expired_recommend'] = self.recommend_canceled + \
                                         self.recommend_expired_less_than_1_month + \
                                         self.recommend_expired_less_than_3_months + \
                                         self.recommend_expired_over_3_months

    def __getattr__(self, item):
        return self.data[item]

    def print_report(self, *, file=sys.stdout):
        """
        Print a text report of my data to the provided file (default: stdout).
        """
        print(f'''Report Date: {datetime.now().date()}

Total Members: {self.members}
Non-Members: {self.non_members}

Brethren: {self.brethren}
Sisters: {self.sisters}
Total Adults: {self.adults}

Young Men: {self.young_men}
Young Women: {self.young_women}

Primary
===================================
Total: {self.primary}
    0-2: {self.age_0_to_2}    3-7: {self.age_3_to_7}    8+: {self.age_8_plus}
    {percent_str(self.age_0_to_2, self.primary)}        {percent_str(self.age_3_to_7, self.primary)}         {percent_str(self.age_8_plus, self.primary)}

Callings
===================================
Brethren with callings: {self.brethren_with_callings} ({percent_str(self.brethren_with_callings, self.brethren)})
Sisters with callings: {self.sisters_with_callings} ({percent_str(self.sisters_with_callings, self.sisters)})


Priesthood
===================================
Brethren:
\tMelchizedek: {self.brethren_melchizedek} ({percent_str(self.brethren_melchizedek, self.brethren)})
\tAaronic: {self.brethren_aaronic} ({percent_str(self.brethren_aaronic, self.brethren)})
\tUnordained: {self.brethren_unordained} ({percent_str(self.brethren_unordained, self.brethren)})

Young Men:
\tAaronic: {self.young_men_aaronic} ({percent_str(self.young_men_aaronic, self.young_men)})
\tUnordained: {self.young_men_unordained} ({percent_str(self.young_men_unordained, self.young_men)})


Single Adults
===================================
Young Singles: {self.single_18}
Mid Singles: {self.single_31} 
46+ Singles: {self.single_46} 
Total: {self.single_18 + self.single_31 + self.single_46}


Temple
===================================
Adults:
\tEndowed: {self.endowed} ({percent_str(self.endowed, self.adults)})
\tNot Endowed: {self.not_endowed} ({percent_str(self.not_endowed, self.adults)})
\tCurrent Recommend: {self.current_recommend} ({percent_str(self.current_recommend, self.endowed)})
\tExpired Recommend: {self.expired_recommend} ({percent_str(self.expired_recommend, self.endowed)})
\tRecommend Expiring this month: {self.recommend_expiring_this_month}
\tRecommend Expiring next month: {self.recommend_expiring_next_month}
\tRecommend Lost or Stolen: {self.recommend_lost_or_stolen}
''', file=file)


EMAIL_REGEX = re.compile(r'.*@.*\..*')


def check_emails(emails: Iterable[str]):
    """
    Do some sanity-checking for the list of emails.
    """
    invalid_emails = []
    for email in emails:
        if not EMAIL_REGEX.match(email):
            invalid_emails.append(email)

    if invalid_emails:
        raise ValueError(f'Emails are invalid:  {", ".join(invalid_emails)}')


def email_report(tos: Iterable[str], report: MemberReport, *, from_: str,
                 smtp_server: str, smtp_server_port: int, smtp_username: str, smtp_password: str):
    """
    Send an email
    """
    msg = EmailMessage()

    with io.StringIO() as out:
        report.print_report(file=out)
        out.seek(0)
        report_text = out.read()
        msg.set_content(report_text)

    msg['Subject'] = subject = f'Ward Report {datetime.now().date()}'
    msg['From'] = from_
    msg['To'] = ', '.join(tos)

    # Attach the report as a txt file for saving.
    msg.add_attachment(report_text, filename=f'{subject}.txt')

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    with smtplib.SMTP(host=smtp_server, port=smtp_server_port) as conn:
        conn.ehlo()
        conn.starttls(context=context)
        conn.ehlo()
        conn.login(smtp_username, smtp_password)
        conn.send_message(msg)
