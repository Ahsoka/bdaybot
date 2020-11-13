import os
import time
import json
import itertools
import click
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
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

def order_product(ASIN,
                  FULLNAME,
                  ADDRESS_LINE_ONE,
                  CITY,
                  STATE,
                  ZIPCODE,
                  PHONE_NUMBER=os.environ['PHONE_NUMBER'],
                  ADDRESS_LINE_TWO=None,
                  place_order=False):
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
        STATE,
        ZIPCODE,
        PHONE_NUMBER,
        None,
        None
    ]
    ADDRESS = list(map(lambda item: '' if item is None else item, ADDRESS))

    input_ids = [
        "address-ui-widgets-enterAddressFullName",
        "address-ui-widgets-enterAddressLine1",
        "address-ui-widgets-enterAddressLine2",
        "address-ui-widgets-enterAddressCity",
        "address-ui-widgets-enterAddressStateOrRegion",
        "address-ui-widgets-enterAddressPostalCode",
        "address-ui-widgets-enterAddressPhoneNumber",
        "address-ui-widgets-addr-details-address-instructions",
        "address-ui-widgets-addr-details-gate-code"
    ]
    assert len(ADDRESS) == len(input_ids), 'Invalid address data was detected submitted'
    for info, html_id in zip(ADDRESS, input_ids):
        input_field = address_form.find_element_by_id(html_id)
        input_field.send_keys(info)
    address_form.submit()

    # NOTE: Might want to add more 'intelligence' here so that the bot does not just click the
    # first instance of 'Set as Default' button it sees.  We want it to click the 'Set as Default'
    # that corresponds to address we just added.
    set_as_default_button = WebDriverWait(driver, 10) \
                            .until(EC.presence_of_element_located((By.LINK_TEXT, 'Set as Default')))
    set_as_default_button.click()

    # input("Press enter when your ready to proceed: ")

    # Purchase item
    driver.get(f"https://amazon.com/dp/{ASIN}")

    amazon_fresh_link = WebDriverWait(driver, 10) \
                        .until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.a-box.almOffer')))
    amazon_fresh_link.click()

    add_to_cart_button = WebDriverWait(driver, 10) \
                         .until(EC.presence_of_element_located((By.ID, 'freshAddToCartButton')))
    add_to_cart_button.click()

    WebDriverWait(driver, 10).until_not(EC.presence_of_element_located((By.ID, 'atfc-spinner-B000RGY5RG')))

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

    def format_address(address, split=False):
        if not split:
            address = address.split(',')[1]
        return address.upper() \
                      .replace('AVENUE', 'AVE') \
                      .replace('LANE', 'LN')
                      # Add more here as you encounter more addresses

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
        if address_text == format_address(ADDRESS):
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
