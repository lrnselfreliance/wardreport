#! /usr/bin/env python3
import asyncio
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
        self.data['current_recommend'] = len(recommend_groups['ACTIVE']) + \
                                         len(recommend_groups['EXPIRING_NEXT_MONTH']) + \
                                         len(recommend_groups['EXPIRING_THIS_MONTH'])
        self.data['expired_recommend'] = len(recommend_groups['CANCELED']) + \
                                         len(recommend_groups['EXPIRED_LESS_THAN_1_MONTH']) + \
                                         len(recommend_groups['EXPIRED_LESS_THAN_3_MONTHS']) + \
                                         len(recommend_groups['EXPIRED_OVER_3_MONTHS'])
        self.data.update({f'recommend_{k.lower()}': len(v) for k, v in recommend_groups.items()})

    def __getattr__(self, item):
        return self.data[item]

    def print_report(self):
        """
        Print a text report of my data to stdout.
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
''')


async def main(username: str, password: str, number: str):
    data = get_data(username, password, number)

    # with open('data.json', 'wt') as fh:
    #     json.dump(data, fh, indent=2)

    member_report = MemberReport(data['member_list'], data['callings'], data['recommend_status'])
    member_report.print_report()


if __name__ == '__main__':
    lds_username, lds_password = os.getenv('LDS_USERNAME'), os.getenv('LDS_PASSWORD')
    lds_unit_number = os.getenv('LDS_UNIT_NUMBER')

    loop = asyncio.get_event_loop()
    coro = main(lds_username, lds_password, lds_unit_number)
    loop.run_until_complete(coro)
