import os
import pathlib

from dotenv import load_dotenv, find_dotenv
from fpdf import FPDF

#envelope size: 110 by 145 mm

# Elliot Torres
# 4321 Loser Road
# La Crescenta, CA 91214
#
# Ryan Lee
# 1234 Boomer Road
# La Crescenta, CA 91214

load_dotenv(find_dotenv())

# types out address on envelope

def sendmail(
    FULLNAME,
    ADDRESS_LINE_ONE,
    CITY,
    STATE,
    ZIPCODE,
    PERSON=None,
    ADDRESS_LINE_TWO=None
):
    if PERSON is None:
        sender_name = os.environ['sender_name']
        sender_addr1 = os.environ['sender_addr1']
        sender_addr2 = os.environ['sender_addr2']
    else:
        sender_name = PERSON.fullname
        sender_addr1 = f'{PERSON.addrline1}'
        sender_addr2 = f'{PERSON.city}, {PERSON.state} {PERSON.zipcode}'

    pdf = FPDF('L', 'mm', (110, 145))
    pdf.add_page()
    pdf.set_font('Times', '', 9.8)
    pdf.set_margins(0, 0, 0)

    pdf.text(7, 7.5, sender_name)
    pdf.text(7, 10.5, sender_addr1)
    pdf.text(7, 13.5, sender_addr2)

    pdf.set_font('Times', '', 14)
    if ADDRESS_LINE_TWO is None:
        pdf.text(44, 78, FULLNAME)
        pdf.text(44, 82, ADDRESS_LINE_ONE)
        pdf.text(44, 86, f'{CITY}, {STATE} {ZIPCODE}')
    else:
        pdf.text(44, 78, FULLNAME)
        pdf.text(44, 82, f'{ADDRESS_LINE_ONE}, {ADDRESS_LINE_TWO}')
        pdf.text(44, 86, f'{CITY}, {STATE} {ZIPCODE}')

    # types out message on back fo envelope

    pdf.add_page()
    pdf.set_margins(0, 0, 0)

    pdf.text(10, 78, f"Happy Birthday {FULLNAME}!")
    pdf.text(10, 82, "Have a wonderful day and enjoy your sweet!")
    pdf.text(10, 86, "-CVHS Bday Team")

    envelope_file = pathlib.Path('envelope.pdf')
    if envelope_file.exists():
        envelope_file.unlink()
    pdf.output('envelope.pdf', dest='F').encode('latin-1')
    os.system("lp -d printer envelope.pdf")
