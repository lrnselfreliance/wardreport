#! /usr/bin/env python3
import argparse
import asyncio
import logging
import os
import sys
from typing import Iterable

from dotenv import load_dotenv

from wardreport.lib import MemberReport, email_report, check_emails, logger, set_log_level

load_dotenv()

# Log all to STDOUT
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
logging.getLogger().addHandler(handler)

# Create logger for this file.
logger = logger.getChild('main')


def get_data(username: str, password: str, number: str) -> dict:
    """
    Get Ward data from the Church of Jesus Christ of Latter-Day Saints website.
    """
    logger.info(f'Getting data with username {username}')
    from wardreport.lcr import API
    lcr_api = API(username, password, number)

    member_list = lcr_api.member_list()
    callings = lcr_api.callings()
    ministering = lcr_api.ministering()
    recommend_status = lcr_api.recommend_status()

    data = dict(
        member_list=member_list,
        callings=callings,
        ministering=ministering,
        recommend_status=recommend_status,
    )
    return data


async def main(username: str, password: str, number: str,
               email_tos: Iterable[str], email_from: str, smtp_server: str, smtp_server_port: int, smtp_username: str,
               smtp_password: str,
               ):
    data = get_data(username, password, number)

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
    parser.add_argument('-p', '--print', default=False, action='store_true',
                        help='Override email report, only print the report.')
    parser.add_argument('-v', action='count', default=0, help='Increase logging verbosity')
    args = parser.parse_args()

    if args.v == 1:
        set_log_level(logging.INFO)
    elif args.v >= 2:
        set_log_level(logging.DEBUG)

    lds_username, lds_password = os.getenv('LDS_USERNAME'), os.getenv('LDS_PASSWORD')
    lds_unit_number = os.getenv('LDS_UNIT_NUMBER')

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_server_port = int(os.getenv('SMTP_SERVER_PORT', 25))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    email_tos = args.emails or os.getenv('EMAIL_TOS', '')
    email_from = os.getenv('EMAIL_FROM')

    # Check environment variables from .env
    if not lds_username:
        print('LDS_USERNAME not found in .env')
        sys.exit(1)
    if not lds_password:
        print('LDS_PASSWORD not found in .env')
        sys.exit(1)
    if not lds_unit_number:
        print('LDS_UNIT_NUMBER not found in .env')
        sys.exit(1)
    if email_tos:
        # Email report is requested, check the variables.
        if not smtp_server:
            print('SMTP_SERVER not found in .env')
            sys.exit(1)
        if not smtp_server_port:
            print('SMTP_SERVER_PORT not found in .env')
            sys.exit(1)
        if not smtp_username:
            print('SMTP_USERNAME not found in .env')
            sys.exit(1)
        if not smtp_password:
            print('SMTP_PASSWORD not found in .env')
            sys.exit(1)
        if not email_from:
            print('EMAIL_FROM not found in .env')
            sys.exit(1)

    email_tos = tuple(i.strip() for i in email_tos.split(',') if i.strip())

    if args.print:
        # Ignore the addresses in .env, print the report.
        email_tos = smtp_server = smtp_server_port = email_from = smtp_password = smtp_username = None

    loop = asyncio.get_event_loop()
    coro = main(lds_username, lds_password, lds_unit_number, email_tos=email_tos, email_from=email_from,
                smtp_server=smtp_server, smtp_server_port=smtp_server_port, smtp_username=smtp_username,
                smtp_password=smtp_password
                )
    loop.run_until_complete(coro)
