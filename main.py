#! /usr/bin/env python3
import asyncio
import dataclasses
import json
import os
from datetime import datetime

from dotenv import load_dotenv

from wardreport.common import household_grouper, member_splitter, male_splitter, calling_finder_maker, calling_splitter, \
    multi_partition, priesthood_grouper, percent_str, singles_by_age, recommend_finder_maker, endowed_splitter, \
    recommend_status_grouper

load_dotenv()


# def get_data(username: str, password: str, number: str):
#     from wardreport.lcr import API
#     lcr_api = API(username, password, number)
#
#     member_list = lcr_api.member_list()
#     callings = lcr_api.callings()
#     ministering = lcr_api.ministering()
#     recommend_status = lcr_api.recommend_status()
#
#     data = dict(
#         member_list=member_list,
#         callings=callings,
#         ministering=ministering,
#         recommend_status=recommend_status,
#     )
#     return data


def get_data(*a, **kw):
    import pathlib
    out = pathlib.Path('data.json')
    with out.open('rt') as fh:
        return json.load(fh)


@dataclasses.dataclass
class MemberReport:
    members: int = 0
    non_members: int = 0

    households: int = 0

    adults: int = 0
    non_adults: int = 0

    brethren: int = 0
    brethren_with_callings: int = 0
    brethren_melchizedek: int = 0
    brethren_aaronic: int = 0
    brethren_unordained: int = 0

    sisters: int = 0
    sisters_with_callings: int = 0

    young_men: int = 0
    young_men_aaronic: int = 0
    young_men_unordained: int = 0

    young_women: int = 0

    primary: int = 0
    age_0_to_2: int = 0
    age_3_to_7: int = 0
    age_8_plus: int = 0

    single_18: int = 0
    single_31: int = 0
    single_46: int = 0

    endowed: int = 0
    not_endowed: int = 0

    recommend_active: int = 0
    recommend_expiring_next_month: int = 0
    recommend_expiring_this_month: int = 0

    recommend_canceled: int = 0
    recommend_expired_less_than_1_month: int = 0
    recommend_expired_less_than_3_months: int = 0
    recommend_expired_over_3_months: int = 0
    recommend_lost_or_stolen: int = 0

    def print_report(self):
        current_recommend = self.recommend_active + self.recommend_expiring_this_month + \
                            self.recommend_expiring_next_month
        expired_recommend = self.recommend_expired_over_3_months + self.recommend_expired_less_than_1_month + \
                            self.recommend_expired_less_than_3_months + self.recommend_canceled
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
\tCurrent Recommend: {current_recommend} ({percent_str(current_recommend, self.endowed)})
\tExpired Recommend: {expired_recommend} ({percent_str(expired_recommend, self.endowed)})
\tRecommend Expiring this month: {self.recommend_expiring_this_month}
\tRecommend Expiring next month: {self.recommend_expiring_next_month}
\tRecommend Lost or Stolen: {self.recommend_lost_or_stolen}
''')


def summarize_members(data: dict) -> MemberReport:
    all_members = data['member_list']

    calling_finder = calling_finder_maker(data['callings'])
    recommend_status = data['recommend_status']
    recommend_finder = recommend_finder_maker(recommend_status)

    members, non_members = member_splitter(all_members)
    households = household_grouper(all_members)

    predicates = [
        lambda i: i['age'] < 12,
        lambda i: 12 <= i['age'] <= 17,
        lambda i: i['age'] > 17,
    ]
    primary, young_people, adults = multi_partition(predicates, all_members)
    young_men, young_women = male_splitter(young_people)

    brethren, sisters = male_splitter(adults)
    brethren_with_calling, brethren_no_calling = calling_splitter(calling_finder, brethren)
    sisters_with_calling, sisters_no_calling = calling_splitter(calling_finder, sisters)

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

    endowed, not_endowed = endowed_splitter(recommend_finder, adults)
    recommend_groups = recommend_status_grouper(recommend_status)

    report = MemberReport()
    report.members = len(members)
    report.non_members = len(non_members)
    report.households = len(households)
    report.adults = len(adults)
    report.non_adults = len(primary) + len(young_people)
    report.brethren = len(brethren)
    report.brethren_with_callings = len(brethren_with_calling)
    report.brethren_melchizedek = len(brethren_no_calling)
    report.brethren_aaronic = len(b_priest) + len(b_teacher) + len(b_deacon)
    report.brethren_unordained = len(b_unordained)
    report.sisters = len(sisters)
    report.sisters_with_callings = len(sisters_with_calling)
    report.young_men = len(young_men)
    report.young_men_aaronic = len(y_priest) + len(y_teacher) + len(y_deacon)
    report.young_men_unordained = len(y_unordained)
    report.young_women = len(young_women)
    report.primary = len(primary)
    report.age_0_to_2 = len(age_0_to_2)
    report.age_3_to_7 = len(age_3_to_7)
    report.age_8_plus = len(age_8_plus)
    report.single_18 = len(single_18)
    report.single_31 = len(single_31)
    report.single_46 = len(single_46)
    report.endowed = len(endowed)
    report.not_endowed = len(not_endowed)
    for name, group in recommend_groups.items():
        setattr(report, f'recommend_{name.lower()}', len(group))

    return report


async def main(username: str, password: str, number: str):
    data = get_data(username, password, number)

    # with open('data.json', 'wt') as fh:
    #     json.dump(data, fh, indent=2)

    member_report = summarize_members(data)
    member_report.print_report()


if __name__ == '__main__':
    lds_username, lds_password = os.getenv('LDS_USERNAME'), os.getenv('LDS_PASSWORD')
    lds_unit_number = os.getenv('LDS_UNIT_NUMBER')

    loop = asyncio.get_event_loop()
    coro = main(lds_username, lds_password, lds_unit_number)
    loop.run_until_complete(coro)
