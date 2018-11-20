from datetime import datetime

DEBUG = False

def log(msg):
    now = datetime.now()
    print('[{}-{}-{} {}:{}] {}'.format(now.year, now.month, now.day, now.hour, now.minute, msg))                                                            

def error(msg):
    log(msg)

def debug(msg):
    if DEBUG:
        log(msg)

