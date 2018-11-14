from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer

DEFAULT_DB = 'sqlite:///entrance_song.db'

Base = declarative_base()

class Device(Base):
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True)
    mac_address = Column(String)
    hostname = Column(String)
    owner = Column(String)
    song = Column(String)

    def __str__(self):
        return 'MAC address: {}, hostname: {}, owner: {}, song: {}'.format(self.mac_address, self.hostname, self.owner, self.song)


if __name__ == '__main__':
    from sqlalchemy import create_engine
    print('Creating tables')
    engine = create_engine(DEFAULT_DB)
    Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
