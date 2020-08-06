# Transition To SQL
Currently the bdaybot uses a very unorganized "database" in the form of .pickle files.  Since .pickle files are not designed to act as a database there are a lot of helper methods that are required access the data in the .pickle files.  In fact most of the methods in the `bdaybot_commands` class are just helper methods which allow the bdaybot code to interact with the pickle database.  This is not ideal because every time the bdaybot's functionality is expanded, it will most likely require more helper methods to enable this type of interaction with the .pickle database.  Instead of using a proper database system this code is essentially reinventing the wheel and rewriting code that has already been written for us in the form of SQL.  SQL is an extremely popular and robust framework for creating database and is much easier to work with than the current .pickle database.  Using SQL will allow all the required information to be stored in a single file and additionally, different sections of the data (which pertain to different aspects of the bdaybot, for example, the `temp_id_storage.pickle` pertains to connecting student IDs to Discord accounts while `announcements.pickle` pertains to the announcements channel for each server the bdaybot is in) will be able to be linked seamlessly unlike with the janky links among the .pickle files (denoted by **FOREIGN KEY** below).

### Objectives of the Transition to SQL:
* Move all data stored outside of RAM (aka all the .pickle files) into a **single SQL database**.
* Add all the contents of the `Student Locator Spring 2020.csv` file into the **single SQL database**.
* Link relevant data together using `FOREIGN KEY`
* Remove the database from the GitHub entirely (including .pickle files)

### Database Structure:

| guild_id | announcements_id | today_names_cycle | role_id | nickname_notice |
| -------- | ---------------- | ----------------- | ------- | --------------- |

* `announcement.pickle` **/** `guilds_info.pickle` ➡ `TABLE guilds`
  * `guild_id`: **│ PRIMARY KEY │**  ID for each server the bot is in
  * `announcements_id`: ID for the announcements channel in each server
  * `today_names_cycle`: itertools.cycle object for each server to change names
  * `role_id`: ID for the bot's **bday/upcoming** role
  * `nickname_notice` *(might be deprecated)*: Whether or not the server-owner has received a message from the bot about not being able to change it's nickname


* `Student Locator Spring 2020.csv` ➡ `TABLE student_data`
  * Will remain essentially the same however, it will now be stored in the SQL database.

| discord_user_id | student_id |
| --------------- | ---------- |

* `bday_dict.pickle` **/** `temp_id_storage.pickle` ➡ `TABLE discord_users`
  * `discord_user_id`: **│ PRIMARY KEY │** ID for each discord user
  * `student_id`:  **│ FOREIGN KEY** `TABLE student_data` **│** Corresponding 6-digit student ID

| discord_user_id | year |
| --------------- | ---- |

Preface: This section of the database will work a little different than all the sections above.  The question mark denoted in `TABLE ?` indicates that the table name will be variable due to the nature of this data.  Every one in the birthday database will eventually have a table which lists all the people who have wished them a happy birthday. For example, if **Jaiden** is in the database, then she will have her own table (probably named after her student ID) dedicated to storing all the people who wished her a happy birthday.

* `bday_dict.pickle` (storing who wished who) ➡ `TABLE ?`

  * `discord_user_id`: **│ PRIMARY KEY and FOREIGN KEY `TABLE discord_users` │** ID for each Discord user that wished the given person a happy birthday
  * `year`: **│ PRIMARY KEY │** The year when the wished occurred (so that people can wish every year it's the given person's birthday)
