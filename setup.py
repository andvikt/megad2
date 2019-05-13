from distutils.core import setup

setup(
    name='megad2',
    python_requires='>3.7',
    install_requirements=['aiohttp'],
    version='0.3.2',
    packages=['megad'],
    url='https://github.com/andvikt/megad2',
    license='BSD',
    author='andrewgermanovich',
    author_email='andvikt@gmail.com',
    description='Simple API for ab-log.ru mega-d'
)
