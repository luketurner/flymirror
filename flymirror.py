#  -~- flymirror.py -~-
# Tiny fast multithreaded rule-based mirroring
# By Luke Turner

from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from os.path import exists as file_exists
from queue import Queue, Empty
from re import search, finditer
from sys import argv
from time import perf_counter, sleep
import csv

import requests


class SkipException(Exception):
    pass

Config = namedtuple('Config', ['rules', 'vars', 'start', 'workers'])
Rule = namedtuple('Rule', ['urlmatch', 'saveas', 'find', 'transform'])


csv.register_dialect('config',
                     delimiter='\t',
                     quoting=csv.QUOTE_NONE,
                     skipinitialspace=True)


def read_config(fname):
    """Reads a given config file into a Config object."""
    with open(fname) as f:
        reader = csv.reader(f, dialect='config')

        config = {'workers': 5, 'rules': [], 'vars': {}}
        lineintomap(next(reader), config)
        for line in reader:
            if len(line) == 0 or line[0] == "URLMATCH" or "DISCARD" in line[0]:
                continue
            if line[0] == "VARS":
                lineintomap(line, config['vars'])
            else:
                rule = Rule._make(x for x in line if len(x) > 0)
                config['rules'].append(rule)
        config['start'] = formatwith(config['start'], config['vars'])
        return Config(**config)


def lineintomap(line, dict):
    """Reads all `key=value` strings in the line into the given map"""
    for decl in line:
        if '=' not in decl:
            continue
        name, val = decl.split('=', 1)
        dict[name] = val


# Module-global queues used for communication between threads
URLS = Queue()
RESPONSES = Queue()
DONE = Queue()


def main():
    """Main method executed when run"""

    if len(argv) != 2:
        print("Usage: flymirror.py [rules_file]")
        return

    if not file_exists(argv[1]):
        print("Error: rules file", argv[1], "does not exist.")
        return

    config = read_config(argv[1])
    URLS.put(config.start)

    # Start the loops in another thread
    # include 2 extra threads for the loopers
    pool = ThreadPoolExecutor(int(config.workers) + 2)
    perfprint("[START]")
    pool.submit(download_loop, pool)
    pool.submit(handle_response_loop, pool, config)

    # Join on both the queues at once (Yeah, this is hacky -- may break in later versions)
    while URLS.unfinished_tasks or RESPONSES.unfinished_tasks:
        sleep(0.3)

    # Shut everything down (may take 1 second)
    DONE.put(True)
    pool.shutdown()
    perfprint("[END]")


def download_loop(pool):
    """Loop to download urls put on the URLS queue."""
    while DONE.empty():
        try:
            url = URLS.get(timeout=1)
            pool.submit(download_url, url)
        except Empty:
            pass


def handle_response_loop(pool, config):
    """Loop to handle responses put on RESPONSES queue."""
    while DONE.empty():
        try:
            resp = RESPONSES.get(timeout=1)
            pool.submit(handle_response, config, resp)
        except Empty:
            pass


def download_url(url):
    """
    Handles GET-ing a URL, puts the response on RESPONSES queue.
    Runs synchronously, so spawn it in a thread.
    """
    perfprint("[GET]", url)
    RESPONSES.put(requests.get(url))
    URLS.task_done()


def handle_response(config, resp):
    """Handles parsing and/or saving a response, based on given rules."""
    requrl = resp.request.url
    try:
        rule = next((r for r in config.rules
                     if search(formatwith(r.urlmatch, config.vars), requrl)),
                    None)

        if not rule:
            raise SkipException()

        rulevars = search(formatwith(rule.urlmatch, config.vars), requrl).groupdict()
        transform = rule.transform != 'false' and rule.transform or "{url}"

        if rule.saveas != 'false':
            filename = formatwith(rule.saveas, config.vars, rulevars)
            perfprint("[SAVE]", filename)
            with open(filename, 'wb') as fd:
                for chunk in resp.iter_content(2048):
                    fd.write(chunk)

        if rule.find != 'false':
            for m in finditer(rule.find, resp.text):
                url = (formatwith(transform, config.vars, m.groupdict()))
                URLS.put(url)

        perfprint("[OK]", requrl)
    except SkipException:
        perfprint("[SKIP]", requrl)
    except Exception as ex:
        perfprint("[FAIL]", requrl, ex)
    finally:
        RESPONSES.task_done()


def perfprint(*args, **kwargs):
    """Just like print() but with a timer at the front."""
    print("{:6.4f}".format(perf_counter()), *args, **kwargs)


def formatwith(string, *dicts):
    masterDict = {}
    for d in dicts:
        masterDict.update(d)
    return string.format(**masterDict)


if __name__ == "__main__":
    main()
