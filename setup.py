from distutils.core import setup

setup(
    name='megad2',
    python_requires='>3.7',
    tests_require=['pytest', 'pytest-asyncio', 'pytest-mock'],
    install_requires=['aiohttp', 'attrs'],
    version='0.3.4',
    packages=['megad'],
    url='https://github.com/andvikt/megad2',
    license='BSD',
    author='andrewgermanovich',
    author_email='andvikt@gmail.com',
    description='Simple API for ab-log.ru mega-d'
)
