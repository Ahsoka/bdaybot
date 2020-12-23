import itertools
from . import values
from sqlalchemy.orm import declarative_base, relationship, backref
from sqlalchemy import (Column,
                        Text,
                        Integer,
                        Boolean,
                        String,
                        BigInteger,
                        PickleType,
                        ForeignKey)

Base = declarative_base()

class Guild(Base):
    __tablename__ = 'guilds'
    guild_id = Column(BigInteger, primary_key=True)
    announcements_id = Column(BigInteger)
    role_id = Column(BigInteger)
    today_names_cycle = Column(PickleType, nullable=False,
                               default=itertools.cycle(values.today_df['FirstName'] + " " + values.today_df['LastName']))
    nickname_notice = Column(Boolean, nullable=False, default=True)

    @property
    def mention_role(self):
        return f'<@&{self.role_id}>'

    @property
    def mention_ann(self):
        return f'<#{self.announcements_id}>'

    def __repr__(self):
        return (f'<Guilds(guild_id={self.guild_id}, '
                f'announcements_id={self.announcements_id}, '
                f'role_id={self.role_id}), '
                f'today_names_cycle={self.today_names_cycle}, '
                f'nickname_notice={self.nickname_notice}>')

class StudentData(Base):
    __tablename__ = 'student_data'
    stuid = Column(Integer, primary_key=True)
    firstname = Column(Text)
    lastname = Column(Text)
    grd = Column(Integer)
    addrline1 = Column(Text)
    addrline2 = Column(Text)
    city = Column(Text)
    state = Column(String(2))
    zipcode = Column(Integer)

    def __repr__(self):
        return (f'<StudentData(stuid={self.stuid}, '
                f'firstname={self.firstname}, '
                f'lastname={self.lastname}), '
                f'grd={self.grd}>')

class DiscordUser(Base):
    __tablename__ = 'discord_users'
    discord_user_id = Column(BigInteger, primary_key=True)
    student_id = Column(Integer, ForeignKey('student_data.stuid', ondelete='CASCADE'),
                        unique=True, nullable=False)
    student_data = relationship(StudentData, backref=backref('discord_user', uselist=False))

    @property
    def mention(self):
        return f'<@{self.discord_user_id}>'

    def __repr__(self):
        return (f'<DiscordUsers(discord_user_id={self.discord_user_id}, '
                f'student_id={self.student_id})>')

class Wish(Base):
    __tablename__ = 'wishes'
    discord_user_id = Column(BigInteger,
                             ForeignKey('discord_users.discord_user_id', ondelete='CASCADE'),
                             primary_key=True)
    year = Column(Integer, primary_key=True)
    wishee_stuid = Column(Integer,
                          ForeignKey('student_data.stuid', ondelete='CASCADE'),
                          primary_key=True)
    discord_user = relationship(DiscordUser, backref='wishes_given')
    wishee = relationship(StudentData, backref='wishes_received')

    def __repr__(self):
        return (f'<Wishes(discord_user_id={self.discord_user_id}, '
                f'year={self.year}, '
                f'wishee_stuid={self.wishee_stuid})>')
