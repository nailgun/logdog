import logdog
import sys
import pickle
import os

state_file = os.path.join(os.path.expanduser('~'), '.logdog.state')
config_file = os.path.join(os.path.expanduser('~'), '.logdog.conf.py')

def save_state(state):
	file = open(state_file, 'w')
	pickle.dump(state, file)
	file.close()

def load_state():
	try:
		file = open(state_file, 'r')
	except IOError:
		return dict()
	else:
		return pickle.load(file)

def load_config():
	import imp
	return imp.load_source('logdog_config', config_file)

def checklog(config, state=None):
	records = logdog.fetch_time_safe(config.SOURCES)
	record = None

	try:
		last_check = state['last_checklog']
	except KeyError:
		pass
	else:
		for record in records:
			if record['ts'] > last_check:
				yield config.OUTPUT.format(record)
				break
	for record in records:
		yield config.OUTPUT.format(record)

	if record:
		state['last_checklog'] = record['ts']

def main():
	state = load_state()
	config = load_config()
	log = checklog(config, state=state)
	for record in log:
		sys.stdout.write(record)
	save_state(state)

if __name__ == '__main__':
	main()
