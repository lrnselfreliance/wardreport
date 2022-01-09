#! /usr/bin/env python3
"""
Useful script for creating example members.
"""
from datetime import date
from pprint import pprint
from uuid import uuid4

from faker import Faker
from faker.providers import DynamicProvider

today = date.today()


def calculate_age(born):
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


membership_provider = DynamicProvider(
    provider_name="member",
    elements=[True, False],
)


def membership_record_from_faker(membership):
    profile = membership.profile()

    membership = dict(
        age=calculate_age(profile['birthdate']),
        sex=profile['sex'],
        isMember=membership.member(),
        uuid=str(uuid4()),
        birth=dict(
            date=dict(
                calc=profile['birthdate'].strftime('%Y-%m-%d'),
            )
        )
    )

    return membership


members = []
for i in range(10):
    fake = Faker()
    fake.add_provider(membership_provider)
    fake = membership_record_from_faker(fake)
    members.append(fake)

pprint(members)
