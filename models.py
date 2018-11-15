from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, ForeignKey

DEFAULT_DB = 'sqlite:///entrance_song.db'

Base = declarative_base()

class Owner(Base):
    __tablename__ = 'owner'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    song = Column(String)
    devices = relationship("Device", back_populates="owner", lazy='joined')

class Device(Base):
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True)
    mac_address = Column(String)
    hostname = Column(String)
    friendly_name = Column(String)
    owner_id = Column(Integer, ForeignKey('owner.id'))
    owner = relationship("Owner", back_populates="devices", lazy='joined')

    def __str__(self):
        return 'MAC address: {}, hostname: {}, friendly name: {}, owner: {}'.format(self.mac_address, self.hostname, self.friendly_name, self.owner.name)


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    print('Creating tables')
    engine = create_engine(DEFAULT_DB)
    Base.metadata.create_all(engine)

    Session = sessionmaker()
    Session.configure(bind=engine)

    # Create a default owner for devices that we don't know about
    session = Session()
    default_owner = Owner(name='unknown owner')
    session.add(default_owner)
    session.commit()
    session.close()

