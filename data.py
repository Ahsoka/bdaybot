import pandas
import urllib.request
import os
import datetime

windows_vid_url, unix_vid_url = 'https://www.youtube.com/watch?v=IolxqkL7cD8', 'https://www.youtube.com/watch?v=5iWhQWVXosU'

url = os.environ.get('bday_data_URL')
assert url is not None, ("The data URL could not be found in environment variables.\n"
                        "See this video on how add the url to the environment variables (name the enviroment variable 'bday_data_URL' without quotes): "
                        f"{windows_vid_url}" if 'nt' in os.name else f"{unix_vid_url}")

raw_data = urllib.request.urlopen(url).read().decode('UTF-8')
data_dict = dict(((column_name, []) for column_name in ['First Name', 'Last Name', 'Period Number', 'Birthdate', 'Birthyear', 'Radio', 'Question #1', 'Question #2', 'Question #3', 'ID Number']))

# Eight rows before it's someone elses data
keys = list(data_dict.keys())
for index, attr in enumerate(raw_data.split('\n')[:-1]):
    index %= 8
    if index == 0:
        unparsed_name = attr.split(' ')
        first_name, last_name = ' '.join(unparsed_name[:-1]), unparsed_name[-1]
        data_dict[keys[index]].append(first_name.capitalize()); data_dict[keys[index + 1]].append(last_name.capitalize())
    elif index == 2:
        unparsed_date = attr.split('-')
        data_dict[keys[index + 1]].append(datetime.date(*map(int, unparsed_date)).replace(year=datetime.date.today().year))
        data_dict[keys[index + 2]].append(int(unparsed_date[0]))
    else:
        try:
            attr = int(attr)
        except ValueError:
            pass
        data_dict[keys[index + 1 if index < 2 else index + 2]].append(attr)

def timedelta_today(date):
    if hasattr(date, 'to_pydatetime'):
        date = date.to_pydatetime()
    if hasattr(date, 'date'):
        date = date.date()
    delta = date - datetime.date.today()
    return delta if delta >= datetime.timedelta() else delta + datetime.timedelta(days=365)

bday_df = pandas.DataFrame(data_dict)
bday_df['Birthdate'] = pandas.to_datetime(bday_df['Birthdate'])
bday_df['Timedelta'] = bday_df['Birthdate'].transform(timedelta_today)
bday_df = bday_df.sort_values(['Timedelta', 'Last Name', 'First Name'])
print(bday_df.info())
print(bday_df[bday_df['Timedelta'] == datetime.timedelta()])
bday_df.to_csv('beta_bdays.csv', index=False)
