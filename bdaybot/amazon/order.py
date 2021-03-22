import itertools
import asyncio
import pathlib
import click
import json
import time
import re
import os

from arsenic import get_session, keys, browsers, services, start_session
from .utils import fill_password, fill_credit_number, format_address, future_dates
from .errors import (ArsenicTimeout,
                     NoSuchElement,
                     FailedToAddToCart,
                     IncorrectCartValue,
                     AddressNotFoundError,
                     NoAvailableDelivery)

async def order_product(ASIN,
                        FULLNAME,
                        ADDRESS_LINE_ONE,
                        CITY,
                        STATE,
                        ZIPCODE,
                        PHONE_NUMBER=os.environ['PHONE_NUMBER'],
                        ADDRESS_LINE_TWO=None,
                        place_order=False,
                        remove_address=True,
                        screenshot=None,
                        quit=True):
    try:
        session = None
        added_address = False

        browser = browsers.Chrome()
        drivers = filter(lambda path: re.search(r'chrome\d\d-driver', str(path)), pathlib.Path('.').iterdir())
        if os.name == 'posix':
            service = services.Chromedriver(log_file=pathlib.Path('logs/chrome.log').resolve().open(mode='a'),
                                            binary=f"./{next(filter(lambda path: path.suffix == '', drivers))}")
            browser.capabilities = {"goog:chromeOptions": {"args": ["--headless"]}}
        else:
            service = services.Chromedriver(binary=f"./{next(filter(lambda path: path.suffix == '.exe', drivers))}")

        session = await start_session(service, browser)
        await session.set_window_size(width=1363, height=1094)

        await session.get("https://amazon.com/")

        with open('cookies.json') as file:
            for cookie in json.load(file):
                del cookie["httpOnly"]
                await session.add_cookie(**cookie)

        await session.get("https://www.amazon.com/a/addresses?ref_=ya_d_l_addr")

        await fill_password(session, os.environ['AMAZON_PASSWORD'])

        add_address_button = await session.wait_for_element(10, '#ya-myab-address-add-link')
        await add_address_button.click()

        # Add all the address info
        address_form = await session.wait_for_element(10, '#address-ui-address-form')
        ADDRESS = [
            FULLNAME,
            ADDRESS_LINE_ONE,
            ADDRESS_LINE_TWO,
            CITY,
            ZIPCODE,
            PHONE_NUMBER,
        ]
        ADDRESS = list(map(lambda item: '' if item is None else item, ADDRESS))

        input_ids = [
            "address-ui-widgets-enterAddressFullName",
            "address-ui-widgets-enterAddressLine1",
            "address-ui-widgets-enterAddressLine2",
            "address-ui-widgets-enterAddressCity",
            "address-ui-widgets-enterAddressPostalCode",
            "address-ui-widgets-enterAddressPhoneNumber",
        ]
        assert len(ADDRESS) == len(input_ids), 'Invalid address data was detected submitted'
        for info, html_id in zip(ADDRESS, input_ids):
            input_field = await address_form.get_element('#' + html_id)
            if html_id == "address-ui-widgets-enterAddressFullName":
                await input_field.clear()
            await input_field.send_keys(info)
        state_select = await address_form.get_element('#address-ui-widgets-enterAddressStateOrRegion-dropdown-nativeId')
        await state_select.select_by_value(STATE)
        await session.execute_script('document.getElementById("address-ui-address-form").submit();')

        added_address = True
        # Set previously added address as default address
        for number in itertools.count():
            if number == 0:
                address_tile = await session.wait_for_element(10, f'#ya-myab-display-address-block-{number}')
            else:
                address_tile = await session.get_element(f'#ya-myab-display-address-block-{number}')
            address_text = await (await address_tile.get_element('#address-ui-widgets-AddressLineOne')).get_text()
            if address_text == format_address(ADDRESS_LINE_ONE):
                set_as_default_button = await session.get_element(f'#ya-myab-set-default-shipping-btn-{number}')
                await set_as_default_button.click()
                break

        # Purchase item
        await session.get(f"https://amazon.com/dp/{ASIN}")

        amazon_fresh_link = await session.wait_for_element(10, '#freshAddToCartButton')
        await amazon_fresh_link.click()

        await asyncio.sleep(2)

        close_button = await session.wait_for_element(10, '#sis-close-div')
        await close_button.click()

        cart_count = int(await (await session.wait_for_element(10, '#nav-cart-count')).get_text())
        start = time.time()
        while cart_count == 0:
            if time.time() - start > 10:
                raise FailedToAddToCart()
            cart_count = int(await (await session.get_element('#nav-cart-count')).get_text())
        else:
            if cart_count != 1:
                raise IncorrectCartValue(f'{cart_count} items in cart')

        cart_button = await session.get_element('#nav-cart')
        await cart_button.click()

        checkout_button = await session.wait_for_element(10, '[name=proceedToALMCheckout-QW1hem9uIEZyZXNo]')
        await checkout_button.click()

        continue_to_checkout_button = await session.wait_for_element(10, '[name=proceedToCheckout]')
        await continue_to_checkout_button.click()

        # await fill_password(session, os.environ['AMAZON_PASSWORD'])

        change_address_button = await session.wait_for_element(10,'#hover-override')
        await change_address_button.click()

        for number in itertools.count():
            try:
                if number == 0:
                    current_address_option = await session.wait_for_element(10, f'#address-book-entry-{number}')
                else:
                    current_address_option = session.get_element(f'#address-book-entry-{number}')
            except NoSuchElement as error:
                raise AddressNotFoundError(click.style("Could not find the address selected in the .env file", fg='red')) from error

            address_text = await (await current_address_option.get_element('li.displayAddressLI.displayAddressAddressLine1')).get_text()
            if address_text == format_address(ADDRESS_LINE_ONE):
                confirm_address_button = await current_address_option.get_element('.a-declarative.a-button-text')
                await confirm_address_button.click()
                break
        
        try:
            day_delivery_classes = "span.a-button.a-button-toggle.ufss-date-select-toggle"
            limited_available_delivery = await session.wait_for_element(10, day_delivery_classes + '.ufss-limited-available')
            await limited_available_delivery.click()
        except (ArsenicTimeout, NoSuchElement):
            first_avaliable_delivery = await session.wait_for_element(10, day_delivery_classes + '.ufss-available')
            await first_avaliable_delivery.click()
        
        clicked = False
        for day in future_dates():
            date_format = format(day, '%Y%m%d')
            print(date_format)
            today_div = await session.get_element(f'[id="{date_format}"]')
            try:
                unordered_list = await today_div.get_element('[aria-label="2-hour delivery windows"]')
            except(NoSuchElement):
                continue
            day_button = await session.get_element(f'[name="{date_format}"]')
            await day_button.click()
            for num, slot in enumerate(await unordered_list.get_elements('li')):
                print(f'The slot class = {await (await slot.get_element("div.ufss-slot")).get_attribute("class")}')
                if "ufss-available" in await (await slot.get_element("div.ufss-slot")).get_attribute("class"):
                    await session.execute_script(f'document.getElementById("{date_format}").getElementsByTagName("li")[{num}].scrollIntoView();')
                    await (await slot.get_element('.ufss-slot.ufss-available')).click()
                    clicked = True
                    break
            if clicked:
                break

        if not clicked:
            raise NoAvailableDelivery("There was no available delivery")
        
        continue_order_button = await session.get_element('input.a-button-input')
        await continue_order_button.click()


        confirm_order_again = await session.wait_for_element(10,'[id="continue-top"]')
        await confirm_order_again.click()

        await fill_credit_number(session, os.environ["CREDIT_CARD"])

        edit_tip_button = await session.wait_for_element(10,'a.a-link-normal.tip-widget--edit-control')
        await edit_tip_button.click()

        select_tip_amount = await session.get_element('[id="tip-widget--edit-form--amount-input"]')
        while not await select_tip_amount.is_displayed():
            await edit_tip_button.click()
        await select_tip_amount.send_keys(keys.BACKSPACE * 4 + "0")

        apply_new_tip_button = await session.get_element('[id="tip-widget--submit-update"]')
        await apply_new_tip_button.click()

        loading_spinner = await session.wait_for_element(10, '[id="spinner-anchor"]')

        if place_order:
            place_order_button = await session.get_element('[name="placeYourOrder1"]')
            await place_order_button.click()
            await session.wait_for_element_gone(10, '#loading-spinner-img')
    finally:
        if session:
            if screenshot:
                with pathlib.Path(screenshot).open(mode='wb') as screenshot:
                    screenshot.write((await session.get_screenshot()).getvalue())
            if remove_address and added_address:
                await session.get("https://www.amazon.com/a/addresses?ref_=ya_d_l_addr")
                for number in itertools.count():
                    if number == 0:
                        address_tile = await session.wait_for_element(10, f'[id="ya-myab-display-address-block-{number}"]')
                    else:
                        address_tile = await session.get_element(f'[id="ya-myab-display-address-block-{number}"]')
                    address_text = await (await address_tile.get_element('[id="address-ui-widgets-AddressLineOne"]')).get_text()
                    if address_text == format_address(ADDRESS_LINE_ONE):
                        remove_address_button = await session.get_element(f'[id="ya-myab-address-delete-btn-{number}"]')
                        await remove_address_button.click()
                        await session.execute_script(f'document.getElementById("deleteAddressModal-{number}-submit-btn").parentElement.submit();')
                        break
            if quit:
                await session.close()
