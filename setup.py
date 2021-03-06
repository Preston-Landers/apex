import os
import sys

from setuptools import find_packages
from setuptools import setup

py_version = sys.version_info[:2]

version = '0.10.0'

install_requires = [
    "bcrypt>=3.0.0",
    "zope.sqlalchemy",
    "velruse>=1.0.3",
    "pyramid>=1.5.1",
    'pyramid_mako',
    "pyramid_mailer",
    "requests",
    "wtforms",
    "wtforms-recaptcha",
    "six"
]

tests_require = install_requires + ['Sphinx', 'docutils',
                                    'WebTest', 'virtualenv',
                                    'nose']

# coverage doesn't support python 3.2
if py_version == (3, 2):
    tests_require.append('coverage==3.7.1')
else:
    tests_require.append('coverage')

here = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(here, 'README.rst')).read()
    CHANGELOG = open(os.path.join(here, 'CHANGELOG.txt')).read()
except IOError:
    README = CHANGELOG = ''

kwargs = dict(
    version=version,
    name='apex',
    description="""\
Pyramid toolkit to add Velruse, Flash Messages,\
CSRF, ReCaptcha and Sessions""",
    long_description=README + '\n\n' + CHANGELOG,
    classifiers=[
      "Intended Audience :: Developers",
      "Programming Language :: Python",
      "License :: OSI Approved :: MIT License",
    ],
    install_requires=install_requires,
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    tests_require=tests_require,
    test_suite="apex.tests",
    url="http://thesoftwarestudio.com/apex/",
    author="Chris Davies",
    author_email='user@domain.com',
    entry_points="""\
        [paste.paster_create_template]
        apex_routesalchemy=apex.scaffolds:ApexRoutesAlchemyTemplate
    """
)

# to update catalogs, use babel and lingua !
try:
    import babel
    babel = babel  # PyFlakes
    # if babel is installed, advertise message extractors (if we pass
    # this to setup() unconditionally, and babel isn't installed,
    # distutils warns pointlessly)
    kwargs['message_extractors'] = {".": [
        ("**.py",     "lingua_python", None),
        ('**.mako', 'mako', None),
        ("**.pt", "lingua_xml", None), ]
    }
except ImportError:
    pass

setup(**kwargs)
