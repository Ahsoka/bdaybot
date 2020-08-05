import pandas
import urllib.request, urllib.error
import os
import datetime
import logs
import sqlite3

logger = logs.createLogger(__name__, fmt='[%(levelname)s] %(name)s.py: %(asctime)s - %(message)s')

windows_vid_url, unix_vid_url = 'https://www.youtube.com/watch?v=IolxqkL7cD8', 'https://www.youtube.com/watch?v=5iWhQWVXosU'

try:
    url = os.environ['bday_data_URL']
except KeyError as error:
    logger.critical("Failed to access environment variable 'bday_data_URL'")
    raise error

logger.info("Sucessfully accessed the environment variable 'bday_data_URL'")
# assert url is not None, ("The data URL could not be found in environment variables.\n"
#                         "See this video on how add the url to the environment variables (name the environment variable 'bday_data_URL' without quotes): "
#                         (f"{windows_vid_url}" if 'nt' in os.name else f"{unix_vid_url}"))

try:
    raw_data = urllib.request.urlopen(url).read().decode('UTF-8')
except (urllib.error.URLError, urllib.error.HTTPError) as error:
    logger.critical("Failed to access the raw data from drneato.com")
    raise error

logger.info('Sucessfully read the raw data from drneato.com')
# data_dict = dict(((column_name, []) for column_name in ['FirstName', 'LastName', 'PeriodNumber', 'Birthdate', 'Birthyear', 'Radio', 'Question#1', 'Question#2', 'Question#3', 'StuID']))
data_dict = dict(((column_name, []) for column_name in ['PeriodNumber', 'Birthdate', 'Birthyear', 'Radio', 'Question#1', 'Question#2', 'Question#3', 'StuID']))

# Eight rows before it's someone elses data
keys = list(data_dict.keys())
for index, attr in enumerate(raw_data.splitlines()):
    index %= 8
    if index == 0:
        continue
        # unparsed_name = attr.split(' ')
        # first_name, last_name = ' '.join(unparsed_name[:-1]), unparsed_name[-1]
        # data_dict[keys[index]].append(first_name.capitalize()); data_dict[keys[index + 1]].append(last_name.capitalize())
    elif index == 2:
        unparsed_date = attr.split('-')
        data_dict[keys[index - 1]].append(datetime.date(*map(int, unparsed_date)).replace(year=datetime.date.today().year))
        data_dict[keys[index]].append(int(unparsed_date[0]))
        # data_dict[keys[index + 1]].append(datetime.date(*map(int, unparsed_date)).replace(year=datetime.date.today().year))
        # data_dict[keys[index + 2]].append(int(unparsed_date[0]))
    else:
        try:
            attr = int(attr)
        except ValueError:
            pass
        data_dict[keys[index - 1 if index == 1 else index]].append(attr)
        # data_dict[keys[index + 1 if index < 2 else index + 2]].append(attr)
logger.info('Sucessfully parsed the raw data from drneato.com')

def timedelta_today(date):
    if hasattr(date, 'to_pydatetime'):
        date = date.to_pydatetime()
    if hasattr(date, 'date'):
        date = date.date()
    delta = date - datetime.date.today()
    # delta = date - datetime.date.today().replace(day=20)
    return delta if delta >= datetime.timedelta() else delta + datetime.timedelta(days=365)

bday_df = pandas.DataFrame(data_dict)
bday_df['Birthdate'] = pandas.to_datetime(bday_df['Birthdate'])
# official_student_df = pandas.concat([pandas.read_csv('Student Locator Spring 2020.csv', usecols=['StuID', 'LastName', 'FirstName', 'Grd']), pandas.DataFrame({'StuID': [123456], 'LastName': ['Neat'], 'FirstName': ['Dr.'], 'Grd': [-1]})])
temp_connection = sqlite3.connect("bdaybot.db")
official_student_df = pandas.read_sql('SELECT * FROM student_data', temp_connection)
temp_connection.close()
print(official_student_df)
logger.info("Sucessfully accessed TABLE student_data in bdaybot.db file")
bday_df = bday_df[bday_df['StuID'].isin(official_student_df['StuID'])]
bday_df.drop_duplicates(['StuID'], inplace=True)
bday_df['StuID'] = pandas.to_numeric(bday_df['StuID'])
bday_df.set_index('StuID', inplace=True); official_student_df.set_index('StuID', inplace=True)
bday_df[['FirstName', 'LastName']] = official_student_df[['FirstName', 'LastName']]
bday_df = bday_df[['FirstName', 'LastName'] + list(bday_df.columns)[:-2]]
logger.info("Sucessfully created and modified the 'bday_df' DataFrame")

def update_data(inplace=True, supress=False):
    # TODO: Pull from the neato website again in case someone added themselves to bdaybot database.
    # Currently the database will never be updated until the bot is run again.
    # Also might want to add some type of check to see if the database has changed so
    # no computation is wasted on parsing the string if the database has not changed.
    bday_df['Timedelta'] = bday_df['Birthdate'].transform(timedelta_today)
    if not supress:
        logger.info(f"Sucessfully updated 'bday_df'")
    return bday_df.sort_values(['Timedelta', 'LastName', 'FirstName'], inplace=inplace)

def get_latest(to_csv=False, supress=False):
    if to_csv:
        logger.info("Sucessfully saved 'bday_df' to 'bdays.csv'")
        bday_df.to_csv('bdays.csv')
    update_data(supress=supress)
    top_person = bday_df.iloc[0]
    if top_person['Timedelta'] == datetime.timedelta():
        return (True, bday_df[bday_df['Timedelta'] == datetime.timedelta()])
    else:
        return (False, bday_df[bday_df['Timedelta'] == top_person['Timedelta']])

update_data()
