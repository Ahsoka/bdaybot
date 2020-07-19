## Background
The bdaybot was commissioned by Dr. Neat in an effort to mimic the feel of the in-person classroom.  One of aspect of the in-person classroom
Dr. Neat really cares about is who's birthday it is. Originally, he commissioned [Elliot] to work on the project.  Later on however, [Ryan] and [Andres] were also added to the project.  The three of us would ultimately be responsible for creating the bot and making the bot what it is today.
## What Does the Bdaybot Actually Do?
The bdaybot has two main functions, showing whose birthday it is and increasing interaction in the servers it is in.  

**How it shows whose birthday it is**:
* Nickname
    * The bot changes its name to whoever's birthday is today. If there's no one's birthday today then it will change its name to person with the closest birthday.
    * If there are multiple people's birthday today it will cycle through everyone's birthday. Same applies if there are multiple people's birthday upcoming.
* Roles:
    * The bot's role is a crucial part of it's ability to make the birthday person visible to people in the server.
    * The bot's role will either be the "Upcoming" role which indicates that someone's birthday is upcoming or the "Happy Birthday" role.
    * The "Upcoming" role also includes information about when the upcoming person's birthday is.

**How it increases interaction in the servers it is in**:
<!-- Pretty poor overview of how it helps increase interaction in the server.
Might want to look at this section again -->
* Commands:
    * `+upcoming`: Used for checking whose birthday are upcoming
    * `+wish`: Used for wishing people a happy birthday
* Easters Eggs:
    * There are various words or phrases that can be said to the bot to triggered some type of funny or silly response from the bot

## Programmatic Design Overview:
### Robustness
The bdaybot is designed to be a highly robust piece of software. This means no matter the situation the baybot is put in, the software will run no matter what. The most error-prone sections of code are given the most attention with this philosophy. In pratical terms, this philosophy means accounting for every possible situation and having an appropriate response ready. For example, almost every command has a `try-except` block around it, for robust error-handling. Additionally, almost every possibility is thoroughly tested to ensure that all scenarios are accounted for.
### Loggings
The bdaybot also has a comprehensive logging system in place. The logging system is designed to monitor all the activities of the bdaybot which helps ensure that the bdaybot is functioning properly.  Additionally, if there are ever any issues with the bdaybot, logging will help pinpoint exactly what the issue is and enable a quick patch.  Additionally, all loggings are stored in a file to ensure that any problems causing the bdaybot to terminate unexpectly will still be solvable. In the case of serious issues, the bdaybot has the capacity to message the developers through Discord to notify them of problems.
### Security
The bdaybot uses environment variables which are special variables stored in the computer's operating system.  Using environment variables allows all sensitive data, such as the Discord API key or the source of the birthday database to be only accessible to those who already have these environment variables in their computer.

## Technical Overview:
This section will be an overview of what each package/library is used for the in the bdaybot code
### [Datetime](https://docs.python.org/3/library/datetime.html)
The datetime package allows us to give the bdaybot the ability to know what the time and date are.  As outlined above, the core functionality of the bdaybot is to display birthdays which is inherently linked to the date and time.
### [Pandas](https://pandas.pydata.org/)
Pandas is used as an easy way to manipulated the birthday data.  Pandas has all sort of useful features, one of which allows us to sort the birthday database by whose's birthday is closest to the day today.
### [Pickle](https://docs.python.org/3/library/pickle.html)
Pickle is used to store Python objects as files.  Pickle is used in the bdaybot to store critical data so that even if the bdaybot shuts off expectedly or unexpectedly the critical data will be saved as a file no matter what.
### [Discord.py](https://discordpy.readthedocs.io/en/latest/)
Discord.py allows the bdaybot to actually communicate with the Discord servers.  It allows the bdaybot to do all the discord related operations.
### [Logging](https://docs.python.org/3/library/logging.html)
The logging package allows the bdaybot to have an extremely comprehensive logging system where all the activities of the bdaybot are recorded both on the command line and in files.  This extremely useful for debugging purposes.
### [OS](https://docs.python.org/3/library/os.html)
This is the module that allows the bdaybot to access the environment variables mentioned above.

<!-- Only first names are used in order to enforce some level of privacy -->
[Andres]: https://github.com/TurretAA12
[Elliot]: https://github.com/Falcons-Royale
[Ryan]: https://github.com/ryanlee68

## TODO List:
Although the Bday bot may be the single most greatest, robust, and perfect bot to ever exist in all the multiverses in all past, present, and future spacetime, there are still some tweaks and other important methods we have yet to do.

* Some of the methods can be implemented more efficiently, the functions that need more efficient code are commented in the code itself ctrl + f and search for ```TODO```
* New event named showwish that returns all the wishers for the input e.g ```+showwish Firstname Lastname```
* New event named age that returns the input's age e.g ```+age Firstname Lastname```
* New event named birthday that returns the input's birthday e.g ```+birthday Firstname Lastname```

## The Future of the Birthday Robot
In order to implement these features listed below, we need your help to help progress the bdaybot become better in the future. Us three normies cannot implement these features below by themselves, so if you attend CVHS we ask those who are interested in the future of bdaybot to help us implement even just a small part of the features listed below

* Using natural language processing(ai) to predict the discord username and other info from discord to accurately link the discord name with the irl name (if their discord username is already not their irl name)
* Turn the bdaybot into a robust teacherbot that takes attendance, and maybe create a system that replaces google classroom (ambitious)
* Create more incentives to use the bdaybot e.g: candy every month to the person who wished the most people, etc..
* Instead of renaming the bdaybot to the student's name on his/her birthday, make the bday student's discord user itself show all the way at the top of the server even if he/she is offline on discord
* If you have more ideas for the bdaybot message nayr#2153 on discord
