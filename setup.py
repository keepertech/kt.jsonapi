"""\
JSON:API support library.
"""

import setuptools

NAME = 'kt.jsonapi'
VERSION = '1.1.0'
LICENSE = 'file: LICENSE.txt'

packages = [NAME]


metadata = dict(
    name=NAME,
    version=VERSION,
    license=LICENSE,
    author='Keeper Technology, LLC',
    author_email='info@keepertech.com',
    url=f'http://kt-git.keepertech.com/DevTools/{NAME}',
    description=__doc__,
    packages=packages,
    package_dir={'': 'src'},
    namespace_packages=['kt'],
    include_package_data=True,
    install_requires=[
        'Flask',
        'zope.component',
        'zope.interface',
        'zope.schema',
    ],
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)


if __name__ == '__main__':
    setuptools.setup(**metadata)
