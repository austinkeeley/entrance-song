"""SQLAlchemy models"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, ForeignKey

DEFAULT_DB = 'sqlite:///entrance_song.db'

Base = declarative_base()

class Owner(Base):
    """A Device owner"""
    __tablename__ = 'owner'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    devices = relationship("Device", back_populates="owner", lazy='joined')
    song = relationship("Song", uselist=False, lazy='joined')

class Device(Base):
    """A Device that has a MAC address and an owner"""
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True)
    mac_address = Column(String, nullable=False, unique=True)
    hostname = Column(String)
    friendly_name = Column(String)
    owner_id = Column(Integer, ForeignKey('owner.id'))
    owner = relationship("Owner", back_populates="devices", lazy='joined')

    def __str__(self):
        return 'MAC address: {}, hostname: {}, friendly name: {}, owner: {}'.format(
            self.mac_address, self.hostname, self.friendly_name, self.owner.name)

class Song(Base):
    """A song that we can search for along with information about how to play it"""
    __tablename__ = 'song'
    id = Column(Integer, primary_key=True)
    artist = Column(String)
    title = Column(String)
    start_minutes = Column(Integer)
    start_seconds = Column(Integer)
    duration = Column(Integer)
    owner_id = Column(Integer, ForeignKey('owner.id'))

    def __str__(self):
        return '{} by {} (starts at {}:{}, {} seconds long)'.format(
            self.title, self.artist, self.start_minutes, self.start_seconds, self.duration)


if __name__ == '__main__':
    from sqlalchemy import create_engine
    print('Creating tables')
    engine = create_engine(DEFAULT_DB)
    Base.metadata.create_all(engine)
