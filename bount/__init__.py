from datetime import datetime

def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S%f")

def memorize(function):
    memo = {}
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper