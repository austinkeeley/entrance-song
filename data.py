from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from models import DEFAULT_DB, Device, Owner, Song

# If true, dump the data as we get it
DEBUG = False

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
    device = session.query(Device).filter(Device.mac_address==mac_addr).first()
    session.close()

    return device

def insert_device(mac_addr, hostname=None, friendly_name='unknown device', owner=None):
    """Inserts a device into the database."""
    if not owner:
        owner = _get_default_owner()

    device = Device(mac_address=mac_addr, hostname=hostname, friendly_name=friendly_name, owner=owner)
    session = Session()
    try:
        session.add(device)
        session.commit()
    except IntegrityError as e:
        print('[*] Could not add device {}'.format(mac_addr))
        print(e)

    session.close()
    return device

def _get_default_owner():
    session = Session()
    default_owner = session.query(Owner).filter(Owner.name=='unknown owner').first()
    if not default_owner:
        # Create a new default owner
        default_owner = Owner(name='unknown owner')
        session.add(default_owner)
        session.commit()

    session.close()
    return default_owner

def _insert_dummy_devices():
    """Inserts dummy data into the database"""
    session = Session()
    song = Song(artist='AC/DC', title='Dirty Deeds', start_minutes=0, start_seconds=0, duration=30)
    owner = Owner(name='austin', song=song)
    dummy_device = Device(mac_address='d0:50:99:07:6b:d1', owner=owner, hostname='localhost')
    session.add(owner)
    session.add(dummy_device)
    session.commit()
    session.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'p':
        _insert_dummy_devices()
    print('All devices in the db:')

    get_all_devices()

    print('Test device:')
    print(get_device_by_mac_addr('d0:50:99:07:6b:d1'))
    print('Garbage device:')
    print(get_device_by_mac_addr('fart'))

    insert_device('asdf')

