from sqlalchemy import (Column,
                        Text,
                        Integer,
                        Boolean,
                        BigInteger,
                        PickleType,
                        ForeignKey)
from sqlalchemy.orm import declarative_base

class Guilds(Base):
    guild_id = Column(BigInteger, primary_key=True)
    announcements_id = Column(BigInteger)
    role_id = Column(BigInteger)
    today_names_cycle = Column(PickleType)
    nickname_notice = Column(Boolean, default=True)

    def __repr__(self):
        return (f'<Guilds(guild_id={self.guild_id}, '
                f'announcements_id={self.announcements_id} '
                f'role_id={self.role_id})>'
                f'today_names_cycle={self.today_names_cycle}'
                f'nickname_notice={self.nickname_notice}>')

class StudentData(Base):
    __tablename__ = 'student_data'
    StuID = Column(Integer, primary_key=True)
    FirstName = Column(Text)
    LastName = Column(Text)
    Grd = Column(Integer)

    def __repr__(self):
        return (f'<StudentData(StuID={self.StuID}, '
                f'FirstName={self.FirstName}, '
                f'LastName={self.LastName}), '
                f'Grd={self.Grd}>')

class DiscordUsers(Base):
    __tablename__ = 'discord_users'
    discord_user_id = Column(BigInteger, primary_key=True)
    student_id = Column(Integer, ForeignKey('student_data.StuID', ondelete='CASCADE'), unique=True)

    def __repr__(self):
        return (f'<DiscordUsers(discord_user_id={self.discord_user_id}, '
                f'student_id={self.student_id})>')

class Wishes(Base):
    discord_user_id = Column(BigInteger,
                             ForeignKey('discord_users.discord_user_id', ondelete='CASCADE'),
                             primary_key=True)
    year = Column(Integer, primary_key=True)
    wishee_stuid = Column(Integer,
                          ForeignKey('student_data.stuid', ondelete='CASCADE')
                          primary_key=True)

    def __repr__(self):
        return (f'<Wishes(discord_user_id={self.discord_user_id}, '
                f'year={self.year}, '
                f'wishee_stuid={self.wishee_stuid})>')
