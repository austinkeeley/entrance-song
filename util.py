from datetime import datetime

def log(msg):
    now = datetime.now()
    print('[{}-{}-{} {}:{}] {}'.format(now.year, now.month, now.day, now.hour, now.minute, msg))                                                            

