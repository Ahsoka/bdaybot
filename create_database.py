import sqlite3
import pickle
import pandas
import datetime
# File used to create all the tables in `bdaybot-data.db`

# Protection so that this file is not accidently run again, only exists for reference
raise RuntimeError(("Do not run this file! This may overwrite the existing database and "
                    "DELETE all data!"))

# connection = sqlite3.connect(':memory:')
connection = sqlite3.connect('bdaybot.db')

# DEBUG: **MUST** include this line in order to use
# FOREIGN KEYS, by default they are **DISABLED**
connection.execute("PRAGMA foreign_keys = 1")

cursor = connection.cursor()

# Creating TABLE guilds
create_guilds_table = """CREATE TABLE guilds(
                        guild_id INT PRIMARY KEY,
                        announcements_id INT,
                        role_id INT,
                        today_names_cycle BLOB,
                        nickname_notice BOOLEAN
                        )"""
cursor.execute(create_guilds_table)

# Creating TABLE student_data and adding data
create_student_data_table = """CREATE TABLE student_data(
                                StuID INT PRIMARY KEY,
                                LastName TEXT,
                                FirstName TEXT,
                                Grd INT
                                )"""
cursor.execute(create_student_data_table)
official_student_df = pandas.concat([pandas.read_csv('Student Locator Spring 2020.csv',
                                    usecols=['StuID', 'LastName', 'FirstName', 'Grd']),
                                    pandas.DataFrame({'StuID': [123456], 'LastName': ['Neat'], 'FirstName': ['Dr.'], 'Grd': [-1]})])
official_student_df.to_sql('student_data', connection, index=False, if_exists='append')

# Creating TABLE discord_users
create_discord_users_table = """CREATE TABLE discord_users(
                                discord_user_id INT PRIMARY KEY,
                                student_id INT UNIQUE,
                                FOREIGN KEY(student_id) REFERENCES student_data(StuID) ON DELETE SET NULL
                                )"""
cursor.execute(create_discord_users_table)

# --- Transfering data from .pickle files to SQL database ---

# Writing to TABLE guilds
with open('announcements.pickle', mode='rb') as file:
    announcements = pickle.load(file)
with open('guilds_info.pickle', mode='rb') as file:
    guilds_info = pickle.load(file)

for (guild_id, (cycler, nickname_notice, role_id)), (_, announcements_id) in zip(guilds_info.items(), announcements.items()):
    cursor.execute("INSERT INTO guilds VALUES(?, ?, ?, ?, ?)",
                    (guild_id, announcements_id, role_id, pickle.dumps(cycler), not nickname_notice))

# Writing to TABLE discord_users
with open('bday_dict.pickle', mode='rb') as file:
    bday_dict = pickle.load(file)
with open('temp_id_storage.pickle', mode='rb') as file:
    temp_id_storage = pickle.load(file)

for wishee_id, wishers in bday_dict.items():
    # print(f"wishee_id: {wishee_id}")
    # Writing to TABLE ?
    # WARNING: Below is NOT A GOOD idea due to the possibility of an SQL injection attack
    # If you will be accepting input from users you **MUST** find a way to prevent
    # this type of attack
    create_id_table = """CREATE TABLE {}(
                        discord_user_id INT,
                        year INT,
                        PRIMARY KEY(discord_user_id, year),
                        FOREIGN KEY(discord_user_id) REFERENCES discord_users(discord_user_id)
                        ON DELETE CASCADE
                        )""".format(f"id_{wishee_id}")
    # cursor.execute(create_id_table, (f"id_{wishee_id}",))
    cursor.execute(create_id_table)
    for discord_id, student_id in wishers.items():
        # WARNING: Line 88 is also a **BAD** idea for the reasons mentioned above
        # print(f"studentID: {student_id}")
        try:
            cursor.execute("INSERT INTO discord_users VALUES(?, ?)", (discord_id, student_id))
        except sqlite3.IntegrityError as error:
            if "UNIQUE constraint failed" not in str(error):
                raise error
        cursor.execute("INSERT INTO id_{} VALUES(?, ?)".format(wishee_id), (discord_id, datetime.date.today().year))

for discord_id, student_id in temp_id_storage.items():
    cursor.execute("INSERT INTO discord_users VALUES(?, ?)", (discord_id, student_id))

# Add all the data to the database
connection.commit()

# Close the connection when finished
connection.close()
