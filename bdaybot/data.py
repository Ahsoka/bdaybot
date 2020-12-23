import os
import pandas
import logging
import datetime
import psycopg2
from dotenv import load_dotenv
import urllib.request, urllib.error

logger = logging.getLogger(__name__)

load_dotenv()

class classproperty:
    # NOTE: The `classproperty` class
    # is NOT my (@Ahsoka's) code. See reference below
    # for original source
    # Reference: https://stackoverflow.com/questions/128573/using-property-on-classmethods/13624858#13624858
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)

class values:
    store_student_data_df = True

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
                    data_dict[keys[index - 1]].append(datetime.date(*map(int, unparsed_date)).replace(year=datetime.date.today().year))
                    data_dict[keys[index]].append(int(unparsed_date[0]))
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
                                        'Birthdate': ['2020-11-15'],
                                        'Birthyear': [2020], # Use 2020 since we don't know her birthyear
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
            bday_df.set_index('StuID', inplace=True); student_df.set_index('stuid', inplace=True)
            columns = ['AddrLine1', 'AddrLine2', 'City', 'State', 'Zipcode', 'FirstName', 'LastName']
            bday_df[columns] = student_df[map(lambda text: text.lower(), columns)]
            bday_df = bday_df[['FirstName', 'LastName'] + list(bday_df.columns)[:-2]]
            logger.info("Sucessfully created and modified the 'bday_df' DataFrame")
            cls.og_bday_df = bday_df
        else:
            bday_df = cls.og_bday_df

        def timedelta_today(date):
            if hasattr(date, 'to_pydatetime'):
                date = date.to_pydatetime()
            if hasattr(date, 'date'):
                date = date.date()
            delta = date - datetime.date.today()
            # delta = date - datetime.date.today().replace(day=20)
            return delta if delta >= datetime.timedelta() else delta + datetime.timedelta(days=365)

        bday_df['Timedelta'] = bday_df['Birthdate'].transform(timedelta_today)
        return bday_df.sort_values(['Timedelta', 'LastName', 'FirstName'])

    @classproperty
    def student_data_df(cls):
        # NOTE: With the current implementation we are storing
        # A LOT of data in the background, due to the shear size of the
        # student_data table (it has over 3,000 row). This may or may not
        # be worth it depending on how often this data is utilized
        # Might want to not store if this variable is not called very often

        # INFO: According the `.info()` method for dataframes, the dataframe
        # takes up roughly 233.1KB of memory
        if not hasattr(cls, 'stored_student_data_df'):
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

            if not cls.store_student_data_df:
                return df
            cls.stored_student_data_df = df
        return cls.stored_student_data_df

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
