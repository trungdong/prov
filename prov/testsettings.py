import os
import random
import string

DEBUG = False

INSTALLED_APPS = (
    'prov.db',
)

TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST_NAME': ':memory:',
    },
}

SECRET_KEY = ''.join([random.choice(string.ascii_letters) for x in range(40)])

# Database specific

if os.environ.get('PROV_TEST_DB_BACKEND') == 'mysql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
    DATABASES['default']['NAME'] = 'prov_test'
    DATABASES['default']['TEST_NAME'] = 'prov_test'
    DATABASES['default']['USER'] = os.environ.get('USER', 'root')

if os.environ.get('PROV_TEST_DB_BACKEND') == 'postgresql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
    DATABASES['default']['NAME'] = 'prov'
    DATABASES['default']['TEST_NAME'] = 'prov_test'
    DATABASES['default']['USER'] = os.environ.get('USER', 'postgres')
