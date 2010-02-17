'''logdog performance test'''

import logdog
import os
import datetime

now = datetime.datetime.now

pattern = r'^(?P<ts>.{15}) (?P<facil>.+):(?P<level>.+) ' + \
		r'(?P<prog>.+)?\[(?P<pid>\d+)?\] ' + \
		r'(?P<msg>.*)'
ts_format = '%b %d %H:%M:%S'
file1 = os.path.join(os.path.dirname(__file__),
			'testlog2.txt')
file2 = os.path.join(os.path.dirname(__file__),
			'testlog3.txt')

def fetch_1source_original():
	print 'fetch syslog from 1 source, original format'
	source = logdog.LogSource(open(file1, 'r'))
	source.pattern = pattern
	source.fields['ts'] = logdog.TimestampField(ts_format)
	output = logdog.OriginalFormat()

	record_count = 0
	begin = now()
	for record in logdog.fetch([source]):
		out = output.format(record)
		record_count += 1
	end = now()
	duration = end - begin
	speed = float(record_count) / (duration.seconds + \
			float(duration.microseconds) / 1000000.0)
	print '\t%d records in %s: %d records/sec' % \
			(record_count, duration, int(speed))

def fetch_2sources_original():
	print 'fetch syslog from 2 sources, original format'
	source1 = logdog.LogSource(open(file1, 'r'))
	source1.pattern = pattern
	source1.fields['ts'] = logdog.TimestampField(ts_format)
	source2 = logdog.LogSource(open(file2, 'r'))
	source2.pattern = pattern
	source2.fields['ts'] = logdog.TimestampField(ts_format)
	output = logdog.OriginalFormat()

	record_count = 0
	begin = now()
	for record in logdog.fetch([source1,source2]):
		out = output.format(record)
		record_count += 1
	end = now()
	duration = end - begin
	speed = float(record_count) / (duration.seconds + \
			float(duration.microseconds) / 1000000.0)
	print '\t%d records in %s: %d records/sec' % \
			(record_count, duration, int(speed))

def fetch_1source_custom():
	print 'fetch syslog from 1 source, custom format'
	source = logdog.LogSource(open(file1, 'r'))
	source.pattern = pattern
	source.fields['ts'] = logdog.TimestampField(ts_format)
	output = logdog.OutputFormat('%(ts)s test\n')
	output.fields['ts'] = logdog.TimestampField(ts_format)

	record_count = 0
	begin = now()
	for record in logdog.fetch([source]):
		out = output.format(record)
		record_count += 1
	end = now()
	duration = end - begin
	speed = float(record_count) / (duration.seconds + \
			float(duration.microseconds) / 1000000.0)
	print '\t%d records in %s: %d records/sec' % \
			(record_count, duration, int(speed))

def main():
	import cProfile
	cProfile.run('fetch_1source_original()', 'prof1')
	fetch_2sources_original()
	fetch_1source_custom()

if __name__ == '__main__':
	main()
