import os
import time
import json
import pathlib
import itertools
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC

def fill_password(driver, password, timeout=2):
    try:
        password_input = WebDriverWait(driver, timeout) \
                         .until(EC.presence_of_element_located((By.ID, 'ap_password')))
        password_input.send_keys(password)

        password_form = driver.find_element_by_name('signIn')
        password_form.submit()
    except (TimeoutException, NoSuchElementException):
        pass

def format_address(address):
    return address.upper() \
                  .replace('AVENUE', 'AVE') \
                  .replace('LANE', 'LN')
                  # Add more here as you encounter more addresses

def order_product(ASIN,
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
        driver = None
        added_address = False
        if os.name == 'posix':
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless'); # chrome_options.add_argument('--no-sandbox')
            driver = webdriver.Chrome(executable_path=str(pathlib.Path('chrome86-driver').resolve()),
                                      chrome_options=chrome_options,
                                      service_args=['--verbose', f"--log-path={pathlib.Path('logs/chrome-logs').resolve()}"])
            driver.set_window_size(width=1363, height=1094)
        else:
            driver = webdriver.Chrome('chrome86-driver.exe')

        driver.get("https://amazon.com/")

        with open('cookies.json') as file:
            for cookie in json.load(file):
                driver.add_cookie(cookie)

        driver.refresh()

        # Set address
        account_button = WebDriverWait(driver, 10) \
                         .until(EC.presence_of_element_located((By.ID, 'nav-link-accountList')))
        account_button.click()

        addresses_button = WebDriverWait(driver, 10) \
                           .until(EC.presence_of_element_located((By.LINK_TEXT, 'Your addresses')))
        addresses_button.click()

        fill_password(driver, os.environ['AMAZON_PASSWORD'])

        add_address_button = WebDriverWait(driver, 10) \
                             .until(EC.presence_of_element_located((By.ID, 'ya-myab-address-add-link')))
        add_address_button.click()

        # Add all the address info
        address_form = WebDriverWait(driver, 10) \
                      .until(EC.presence_of_element_located((By.ID, 'address-ui-address-form')))
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
            input_field = address_form.find_element_by_id(html_id)
            input_field.send_keys(info)
        state_select = Select(address_form.find_element_by_id('address-ui-widgets-enterAddressStateOrRegion-dropdown-nativeId'))
        state_select.select_by_value(STATE)
        address_form.submit()

        added_address = True
        # Set previously added address as default address
        for number in itertools.count():
            if number == 0:
                address_tile = WebDriverWait(driver, 10) \
                               .until(EC.presence_of_element_located((By.ID, f'ya-myab-display-address-block-{number}')))
            else:
                address_tile = driver.find_element_by_id(f'ya-myab-display-address-block-{number}')
            address_text = address_tile.find_element_by_id('address-ui-widgets-AddressLineOne').text
            if address_text == format_address(ADDRESS_LINE_ONE):
                set_as_default_button = driver.find_element_by_id(f'ya-myab-set-default-shipping-btn-{number}')
                set_as_default_button.click()
                break

        # Purchase item
        driver.get(f"https://amazon.com/dp/{ASIN}")

        amazon_fresh_link = WebDriverWait(driver, 10) \
                            .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.a-box.almOffer')))
        amazon_fresh_link.click()
        add_to_cart_button = WebDriverWait(driver, 10) \
                             .until(EC.presence_of_element_located((By.ID, 'freshAddToCartButton')))
        add_to_cart_button.click()

        WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.ID, 'nav-cart-count'), '1'))

        cart_button = driver.find_element_by_id('nav-cart')
        cart_button.click()

        checkout_button = WebDriverWait(driver, 10) \
                          .until(EC.presence_of_element_located((By.NAME, 'proceedToALMCheckout-QW1hem9uIEZyZXNo')))
        checkout_button.click()

        continue_to_checkout_button = WebDriverWait(driver, 10) \
                                      .until(EC.presence_of_element_located((By.NAME, 'proceedToCheckout')))
        continue_to_checkout_button.click()

        fill_password(driver, os.environ['AMAZON_PASSWORD'])

        change_address_button = WebDriverWait(driver, 10) \
                                .until(EC.presence_of_element_located((By.ID, 'hover-override')))
        change_address_button.click()

        class AddressNotFoundError(Exception):
            pass

        for number in itertools.count():
            try:
                if number == 0:
                    current_address_option = WebDriverWait(driver, 10) \
                                             .until(EC.presence_of_element_located((By.ID, f'address-book-entry-{number}')))
                else:
                    current_address_option = driver.find_element_by_id(f'address-book-entry-{number}')
            except NoSuchElementException as error:
                raise AddressNotFoundError(click.style("Could not find the address selected in the .env file", fg='red')) from error

            address_text = current_address_option.find_element_by_css_selector('li.displayAddressLI.displayAddressAddressLine1').text
            if address_text == format_address(ADDRESS_LINE_ONE):
                confirm_address_button = current_address_option.find_element_by_link_text('Deliver to this address')
                confirm_address_button.click()
                break

        first_avaliable_delivery = WebDriverWait(driver, 10) \
                                   .until(EC.presence_of_element_located((By.CLASS_NAME, 'ufss-slot-container')))
        first_avaliable_delivery.click()

        continue_order_button = driver.find_element_by_css_selector('input.a-button-input')
        continue_order_button.click()

        confirm_order_again = WebDriverWait(driver, 10) \
                              .until(EC.presence_of_element_located((By.ID, 'continue-top')))
        confirm_order_again.click()

        edit_tip_button = WebDriverWait(driver, 10) \
                          .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.a-link-normal.tip-widget--edit-control')))
        edit_tip_button.click()

        select_tip_amount = driver.find_element_by_id('tip-widget--edit-form--amount-input')
        select_tip_amount.send_keys(Keys.BACK_SPACE * 4 + "0")

        apply_new_tip_button = driver.find_element_by_id('tip-widget--submit-update')
        apply_new_tip_button.click()

        loading_spinner = WebDriverWait(driver, 10) \
                          .until(EC.invisibility_of_element((By.ID, 'spinner-anchor')))

        if place_order:
            place_order_button = driver.find_element_by_name('placeYourOrder1')
            place_order_button.click()
            WebDriverWait(driver, 10).until(EC.invisibility_of_element((By.ID, 'loading-spinner-img')))
    finally:
        if driver:
            if screenshot:
                driver.save_screenshot(str(pathlib.Path(screenshot).resolve()))
            if remove_address and added_address:
                driver.get("https://amazon.com/")
                account_button = WebDriverWait(driver, 10) \
                                 .until(EC.presence_of_element_located((By.ID, 'nav-link-accountList')))
                account_button.click()
                addresses_button = WebDriverWait(driver, 10) \
                                   .until(EC.presence_of_element_located((By.LINK_TEXT, 'Your addresses')))
                addresses_button.click()
                fill_password(driver, os.environ['AMAZON_PASSWORD'])
                for number in itertools.count():
                    if number == 0:
                        address_tile = WebDriverWait(driver, 10) \
                                       .until(EC.presence_of_element_located((By.ID, f'ya-myab-display-address-block-{number}')))
                    else:
                        address_tile = driver.find_element_by_id(f'ya-myab-display-address-block-{number}')
                    address_text = address_tile.find_element_by_id('address-ui-widgets-AddressLineOne').text
                    if address_text == format_address(ADDRESS_LINE_ONE):
                        delete_address_button = driver.find_element_by_id(f'ya-myab-address-delete-btn-{number}')
                        delete_address_button.click()
                        confirm_delete_address_form = driver.find_element_by_css_selector('.a-column.a-span8>form')
                        confirm_delete_address_form.submit()
                        break
            if quit:
                driver.quit()
