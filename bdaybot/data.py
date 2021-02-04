import os
import pandas
import logging
import datetime
import psycopg2
import functools
from dotenv import load_dotenv
from .utils import classproperty
import urllib.request, urllib.error

logger = logging.getLogger(__name__)

if not hasattr(functools, 'cache'):
    # Function below is copied straight
    # from Python 3.9 GitHub
    # Reference: https://github.com/python/cpython/blob/3.9/Lib/functools.py#L650
    def functools_cache(user_function): return functools.lru_cache(maxsize=None)(user_function)
    functools.cache = functools_cache

load_dotenv()

class values:
    @classproperty
    def raw_data(cls):
        try:
            return urllib.request.urlopen(os.environ['bday_data_URL']).read().decode('UTF-8')
        except (urllib.error.URLError, urllib.error.HTTPError):
            logger.critical("Failed to access the raw data from drneato.com")
            raise
        except KeyError:
            logger.critical("Failed to access environment variable 'bday_data_URL'")
            raise

    @classproperty
    def bday_df(cls):
        if not hasattr(cls, 'og_raw_data'):
            cls.og_raw_data = cls.raw_data
        if cls.og_raw_data != cls.raw_data or not hasattr(cls, 'og_bday_df'):
            cls.og_raw_data = cls.raw_data
            data_dict = dict(((column_name, []) for column_name in ['PeriodNumber',
                                                                    'Birthdate',
                                                                    'Birthyear',
                                                                    'Radio',
                                                                    'Question#1',
                                                                    'Question#2',
                                                                    'Question#3',
                                                                    'StuID']))
            # Eight rows before it's someone elses data
            keys = list(data_dict.keys())
            for index, attr in enumerate(cls.raw_data.splitlines()):
                index %= 8
                if index == 0:
                    continue
                elif index == 2:
                    unparsed_date = attr.split('-')
                    try:
                        data_dict[keys[index - 1]].append(datetime.date(*map(int, unparsed_date)).replace(year=datetime.date.today().year))
                        data_dict[keys[index]].append(int(unparsed_date[0]))
                    except ValueError:
                        data_dict[keys[index - 1]].append(None)
                        data_dict[keys[index]].append(0)
                else:
                    try:
                        attr = int(attr)
                    except ValueError:
                        pass
                    data_dict[keys[index - 1 if index == 1 else index]].append(attr)
            logger.info('Sucessfully parsed the raw data from drneato.com')

            bday_df = pandas.concat([pandas.DataFrame(data_dict),
                                     pandas.DataFrame({
                                        'PeriodNumber': [-1],
                                        'Birthdate': [datetime.date.today().replace(month=11, day=15)],
                                        'Birthyear': [0], # Use 0 since we don't know her birthyear
                                        'Radio': [None],
                                        'Question #1': [None],
                                        'Question #2': [None],
                                        'Question #3': [None],
                                        'StuID': [1]
                                     })])
            bday_df['Birthdate'] = pandas.to_datetime(bday_df['Birthdate'])
            student_df = cls.student_data_df
            bday_df = bday_df[bday_df['StuID'].isin(student_df['stuid'])]
            bday_df.drop_duplicates(['StuID'], inplace=True)
            bday_df['StuID'] = pandas.to_numeric(bday_df['StuID'])
            bday_df.set_index('StuID', inplace=True)
            student_df = student_df.set_index('stuid')
            columns = ['AddrLine1', 'AddrLine2', 'City', 'State', 'Zipcode', 'FirstName', 'LastName']
            bday_df[columns] = student_df[map(lambda text: text.lower(), columns)]
            bday_df = bday_df[['FirstName', 'LastName'] + list(bday_df.columns)[:-2]]
            logger.info("Sucessfully created and modified the 'bday_df' DataFrame")
            cls.og_bday_df = bday_df
        else:
            bday_df = cls.og_bday_df

        if bday_df.iloc[0]['Birthdate'].year != datetime.date.today().year:
            bday_df['Birthdate'] = bday_df['Birthdate'].transform(lambda date: date.replace(year=datetime.date.today().year))
            cls.og_bday_df = bday_df

        def timedelta_today(date):
            if hasattr(date, 'to_pydatetime'):
                date = date.to_pydatetime()
            if hasattr(date, 'date'):
                date = date.date()
            delta = date - datetime.date.today()
            if delta == datetime.timedelta(days=-365):
                # Condition for edge case with bdays
                # on Jan 1st
                return datetime.timedelta(days=1)
            return delta if delta >= datetime.timedelta() else delta + datetime.timedelta(days=365)

        bday_df['Timedelta'] = bday_df['Birthdate'].transform(timedelta_today)
        return bday_df.sort_values(['Timedelta', 'LastName', 'FirstName'])

    @classproperty
    @functools.cache
    def student_data_df(cls):
        # NOTE: With the current implementation we are storing
        # A LOT of data in the background, due to the shear size of the
        # student_data table (it has over 3,000 row). This may or may not
        # be worth it depending on how often this data is utilized
        # Might want to not store if this variable is not called very often

        # INFO: According the `.info()` method for dataframes, the dataframe
        # takes up roughly 233.1KB of memory
        try:
            temp_connection = psycopg2.connect(dbname='botsdb')
        except psycopg2.OperationalError:
            temp_connection = psycopg2.connect(dbname='botsdb',
                                               host=os.environ['host'],
                                               user=os.environ['dbuser'],
                                               password=os.environ['password'])
        # NOTE: For some reason using the table name only causes
        # a syntax error even though in the documentation table names
        # are supported.  It might be because we are using an unsupported
        # DBAPI
        df = pandas.read_sql('SELECT * FROM student_data', temp_connection)
        logger.info(f"Sucessfully accessed TABLE student_data in the botsdb database (PostgreSQL)")
        temp_connection.close()
        return df

    @classproperty
    def bday_today(cls):
        # Code translated to english:
        # Find how long until the next closest birthday is (cls.bday_df.iloc[0]['Timedelta'])
        # and check if that value is zero
        # (if it zero then there is a birthday; if it is not then there is no birthday)
        return cls.bday_df.iloc[0]['Timedelta'] == datetime.timedelta()

    @classproperty
    def today_df(cls):
        bday_df = cls.bday_df
        return bday_df[bday_df['Timedelta'] == datetime.timedelta()] if cls.bday_today \
               else bday_df[bday_df['Timedelta'] == bday_df.iloc[0]['Timedelta']]
