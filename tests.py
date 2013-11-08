#!/usr/bin/env python
"""
Unit tests runner for ``prov`` based on the django-guardian project.
setuptools need instructions how to interpret ``test`` command when we run::

    python setup.py test

"""

import os
import sys
from nose.plugins.plugintest import run_buffered as run

os.environ["DJANGO_SETTINGS_MODULE"] = 'prov.testsettings'
from prov import testsettings as settings


def show_settings(settings, action):
    from django.utils.termcolors import colorize
    import prov

    prov_path = prov.__path__[0]
    msg = "prov module's path: %r" % prov_path
    print(colorize(msg, fg='magenta'))
    db_conf = settings.DATABASES['default']
    output = []
    msg = "Starting %s for db backend: %s" % (action, db_conf['ENGINE'])
    embracer = '=' * len(msg)
    output.append(msg)
    for key in sorted(db_conf.keys()):
        if key == 'PASSWORD':
            value = '****************'
        else:
            value = db_conf[key]
        line = '    %s: "%s"' % (key, value)
        output.append(line)
    embracer = colorize('=' * len(max(output, key=lambda s: len(s))),
        fg='green', opts=['bold'])
    output = [colorize(line, fg='blue') for line in output]
    output.insert(0, embracer)
    output.append(embracer)
    print('\n'.join(output))


def runtests(settings):
    from django.test.utils import get_runner

    show_settings(settings, 'tests')

    TestRunner = get_runner(settings)
    test_runner = TestRunner(interactive=False)

    test_runner.setup_test_environment()
    old_config = test_runner.setup_databases()

    # Run tests with whatever argument was passed to the script
    run(argv=sys.argv)

    test_runner.teardown_databases(old_config)
    test_runner.teardown_test_environment()


def main():
    failures = runtests(settings)
    sys.exit(failures)


if __name__ == '__main__':
    main()
