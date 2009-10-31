from distutils.core import setup
setup(
	name='logdog',
	version='0.1',
	description='System log maintenance tools',
	author='Dmitry Bashkatov',
	author_email='nailgunster@gmail.com',
	url='http://wae.org.ru/',
	packages=['logdog'],
	package_dir={'logdog': ''},
	package_data={'logdog': ['testlog.txt']},
)
