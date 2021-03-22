import datetime
import asyncio

from .errors import ArsenicTimeout, NoSuchElement

async def fill_password(session, password, timeout=2):
    try:
        password_input = await session.wait_for_element(timeout,'#ap_password')
        await password_input.send_keys(password)

        await session.execute_script('document.getElementsByName("signIn")[0].submit();')
    except (ArsenicTimeout, NoSuchElement):
        pass

async def fill_credit_number(session, credit_card_number, timeout=4):
    try:
        await asyncio.sleep(timeout)
        credit_input = await session.wait_for_element(timeout, '[id="addCreditCardNumber"]')
        # await credit_input.click()
        await credit_input.send_keys(credit_card_number)

        credit_form = await session.get_element('div.aok-float-left>span.a-button.a-button-primary.a-padding-none')
        await credit_form.click()

        await asyncio.sleep(timeout)
        continue_btn = await session.wait_for_element(timeout, 'span.a-button.a-button-primary.a-padding-none.a-button-span12')
        await continue_btn.click()
    except (ArsenicTimeout, NoSuchElement):
        pass

def format_address(address):
    return address.upper() \
                  .replace('AVENUE', 'AVE') \
                  .replace('LANE', 'LN') \
                  .replace('DRIVE', 'DR') \
                  .replace('BOULEVARD', 'BLVD') \
                  .rstrip('.')
                  # Add more here as you encounter more addresses

def future_dates():
    day = datetime.date.today()
    for _ in range(4):
        yield day
        day += datetime.timedelta(days=1)
