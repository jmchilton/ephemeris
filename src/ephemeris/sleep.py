#!/usr/bin/env python
'''Utility to do a blocking sleep until a Galaxy instance is responsive.
This is useful in docker images, in RUN steps, where one needs to wait
for a currently starting Galaxy to be alive, before API requests can be
made successfully.
The script functions by making repeated requests to
``http(s)://fqdn/api/version``, an API which requires no authentication
to access.'''

import sys
import time
from argparse import ArgumentParser

import requests
from galaxy.util import unicodify

from .common_parser import get_common_args

DEFAULT_SLEEP_WAIT = 1


def _parser():
    '''Constructs the parser object'''
    parent = get_common_args(login_required=False)
    parser = ArgumentParser(parents=[parent], usage="usage: %(prog)s <options>",
                            description="Script to sleep and wait for Galaxy to be alive.")
    parser.add_argument("--timeout",
                        default=0, type=int,
                        help="Galaxy startup timeout in seconds. The default value of 0 waits forever")
    parser.add_argument("-a", "--api_key",
                        dest="api_key",
                        help="Sleep until key becomes available.")
    return parser


def _parse_cli_options():
    """
    Parse command line options, returning `parse_args` from `ArgumentParser`.
    """
    parser = _parser()
    return parser.parse_args()


class SleepCondition(object):

    def __init__(self):
        self.sleep = True

    def cancel(self):
        self.sleep = False


def galaxy_wait(galaxy_url, verbose=False, timeout=0, sleep_condition=None, api_key=None):
    """Pass user_key to ensure it works before returning."""
    version_url = galaxy_url + "/api/version"
    if api_key:
        # adding the key to the URL will ensure Galaxy returns invalid responses until
        # the key is available.
        version_url = "%s?%s" % (version_url, api_key)
    if sleep_condition is None:
        sleep_condition = SleepCondition()

    count = 0
    while sleep_condition.sleep:
        try:
            result = requests.get(version_url)
            if result.status_code == 403:
                if verbose:
                    sys.stdout.write("[%02d] Provided key not (yet) valid... %s\n" % (count, result.__str__()))
                    sys.stdout.flush()
            else:
                try:
                    result = result.json()
                    if verbose:
                        sys.stdout.write("Galaxy Version: %s\n" % result['version_major'])
                        sys.stdout.flush()
                    break
                except ValueError:
                    if verbose:
                        sys.stdout.write("[%02d] No valid json returned... %s\n" % (count, result.__str__()))
                        sys.stdout.flush()
        except requests.exceptions.ConnectionError as e:
            if verbose:
                sys.stdout.write("[%02d] Galaxy not up yet... %s\n" % (count, unicodify(e)[:100]))
                sys.stdout.flush()
        count += 1

        # If we cannot talk to galaxy and are over the timeout
        if timeout != 0 and count > timeout:
            sys.stderr.write("Failed to contact Galaxy\n")
            return False

        time.sleep(DEFAULT_SLEEP_WAIT)

    return True


def main():
    """
    Main function
    """
    options = _parse_cli_options()

    galaxy_alive = galaxy_wait(
        galaxy_url=options.galaxy,
        verbose=options.verbose,
        timeout=options.timeout,
        api_key=options.api_key,
    )
    exit_code = 0 if galaxy_alive else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
