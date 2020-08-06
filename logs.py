import logging, logging.handlers
import datetime
import os

class PrettyFormatter(logging.Formatter):
    def __init__(self, *args, style='%', **kwargs):
        if style != '%':
            raise ValueError(f"__init__() does not currently accept {style} as valid style, please use %")
        super().__init__(*args, style=style, **kwargs)

    def levelname_in_front(self):
        loc = self._fmt.find('%(levelname)s')
        if loc == -1:
            return False
        return ')s' not in self._fmt[:loc]

    def format(self, record):
        unparsed = super().format(record)
        if not self.levelname_in_front():
            return unparsed
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        max_length = max(map(len, levels))
        for index, level in enumerate(levels):
            if level in unparsed:
                break
        end_loc = unparsed.find(level) + len(level)
        end = unparsed[end_loc]
        while end != ' ':
            end_loc += 1
            end = unparsed[end_loc]
        spaces = max_length - len(level)
        returning = (" " * spaces) +  unparsed[:end_loc] + unparsed[end_loc:]
        # print(f"returning == unparsed = {unparsed == returning}")
        return returning

def file_renamer(filename):
    split = filename.split('.')
    return ".".join(split[:-3] + [split[-1], split[-2]])

def createLogger(name, *, fmt, datefmt='%I:%M %p'):
    # Init the logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Init the PrettyFormatter
    pretty = PrettyFormatter(fmt=fmt, datefmt=datefmt)

    if not os.path.isdir('logs'):
        os.mkdir('logs')
    # Create a handler that records all activity
    everything_save = os.path.join('logs', f'bdaybot.{format(datetime.datetime.today(), "%Y-%m-%d")}.log')
    everything = logging.handlers.TimedRotatingFileHandler(everything_save, when='midnight', encoding='UTF-8')
    # Do not use loggging.NOTSET, does not working for some reason
    # use logging.DEBUG if you want the lowest level
    everything.setLevel(logging.DEBUG)
    everything.setFormatter(pretty)

    # Create a handler that records only ERRORs and CRITICALs
    errors_save = os.path.join('logs', f'ERRORS.bdaybot.{format(datetime.datetime.today(), "%Y-%m-%d")}.log')
    errors_only = logging.handlers.TimedRotatingFileHandler(errors_save, when='midnight', encoding='UTF-8')
    errors_only.setLevel(logging.ERROR)
    errors_only.setFormatter(pretty)

    # Rename files so .log is the file extension
    everything.namer, errors_only.namer = (file_renamer,) * 2

    # Create a handler so we can see the output on the console
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(pretty)

    # Add handlers to the logger
    logger.addHandler(everything)
    logger.addHandler(errors_only)
    logger.addHandler(console)

    return logger
