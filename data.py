from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import DEFAULT_DB, Device, Owner

# If true, dump the data as we get it
DEBUG = True

# boilerplate sqlalchemy stuff
Session = sessionmaker()
engine = create_engine(DEFAULT_DB)
Session.configure(bind=engine)

def get_all_devices():
    """Gets all the devices in the database"""
    session = Session()
    all_devices = session.query(Device).all()
    session.close()

    if DEBUG:
        for device in all_devices:
            print('{}'.format(device, device.owner))

    return all_devices

def get_device_by_mac_addr(mac_addr):
    """Gets a device from the database by its MAC address, or None if it's not in the DB"""
    session = Session()
    device = session.query(Device).filter(mac_addr==mac_addr).first()
    session.close()

    return device


def insert_dummy_devices():
    """Inserts dummy data into the database"""
    session = Session()
    owner = Owner(name='austin', song='Dirty Deeds by AC/DC')
    dummy_device = Device(mac_address='01:02:03:04:05:06', owner=owner, hostname='localhost')
    session.add(owner)
    session.add(dummy_device)
    session.commit()
    session.close()


if __name__ == '__main__':
    print('All devices in the db:')
    #insert_dummy_devices()
    get_all_devices()

    print('Test device:')
    print(get_device_by_mac_addr('01:02:03:04:05:06'))

