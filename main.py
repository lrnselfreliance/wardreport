#! /usr/bin/env python3
import argparse
import asyncio
import json
import os
from typing import Iterable

from dotenv import load_dotenv

from wardreport.common import MemberReport, email_report, check_emails

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


async def main(username: str, password: str, number: str,
               email_tos: Iterable[str], email_from: str, smtp_server: str, smtp_server_port: int, smtp_username: str,
               smtp_password: str,
               ):
    data = get_data(username, password, number)

    # with open('data.json', 'wt') as fh:
    #     json.dump(data, fh, indent=2)

    member_report = MemberReport(data['member_list'], data['callings'], data['recommend_status'])
    if email_tos:
        # Send the report as an email.
        check_emails(email_tos)
        email_report(
            email_tos,
            member_report,
            from_=email_from,
            smtp_server=smtp_server,
            smtp_server_port=smtp_server_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
        )
    else:
        # Print the report by default.
        member_report.print_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--emails', help='A comma-separated list of emails that will receive the report')
    args = parser.parse_args()

    lds_username, lds_password = os.getenv('LDS_USERNAME'), os.getenv('LDS_PASSWORD')
    lds_unit_number = os.getenv('LDS_UNIT_NUMBER')

    _smtp_server = os.getenv('SMTP_SERVER')
    _smtp_server_port = int(os.getenv('SMTP_SERVER_PORT', 25))
    _smtp_username = os.getenv('SMTP_USERNAME')
    _smtp_password = os.getenv('SMTP_PASSWORD')
    _email_tos = args.emails or os.getenv('EMAIL_TOS', '')
    _email_from = os.getenv('EMAIL_FROM')

    _email_tos = tuple(i.strip() for i in _email_tos.split(',') if i.strip())

    loop = asyncio.get_event_loop()
    coro = main(lds_username, lds_password, lds_unit_number, email_tos=_email_tos, email_from=_email_from,
                smtp_server=_smtp_server, smtp_server_port=_smtp_server_port, smtp_username=_smtp_username,
                smtp_password=_smtp_password
                )
    loop.run_until_complete(coro)
