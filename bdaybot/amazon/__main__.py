import asyncio

from ..data import values
from .order import order_product

person_with_address = values.student_data_df[values.student_data_df['addrline1'].notnull()].iloc[0]
asyncio.run(order_product(ASIN="B000RGY5RG",
                          FULLNAME=person_with_address['firstname'] + ' ' + person_with_address['lastname'],
                          ADDRESS_LINE_ONE=person_with_address['addrline1'],
                          ADDRESS_LINE_TWO=person_with_address['addrline2'],
                          CITY=person_with_address['city'],
                          STATE=person_with_address['state'],
                          ZIPCODE=str(int(person_with_address['zipcode'])),
                          place_order=False,
                          quit=False))
