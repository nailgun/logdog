# -*- encoding: utf-8 -*-

'''
test suite for logdog
'''

import logdog

import unittest
import time
import tempfile
import random
import os
import datetime

class TestConfig:
	def __init__(self):
		#self.SOURCES = None
		self.OUTPUT = logdog.OriginalFormat()
		pass

msg_list = [
	'warn: log entry 1\n',
	'err: log entry 2\n',
	'err: log entry 3\n',
]

class ChecklogTest(unittest.TestCase):
	pattern = r'^(?P<ts>.{15}) (?P<host>.+) ' + \
			r'((?P<prog>.+)(\[(?P<pid>\d+)\])?: )?' + \
			r'(?P<msg>.*)'
	ts_format = '%b %d %H:%M:%S'
	logfile_path = os.path.join(os.path.dirname(__file__),
			'testlog.txt')

	def setUp(self):
		self.state = dict()

	def test_single_file(self):
		'''checklog should return all lines without change'''

		config = TestConfig()
		logsource = logdog.LogSource(open(self.logfile_path, 'r'))
		logsource.pattern = self.pattern
		logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.SOURCES = [logsource]

		expected = list(open(self.logfile_path, 'r'))
		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(result, expected)
	
	def test_custom_output(self):
		'''checklog should return customized lines'''

		config = TestConfig()
		logsource = logdog.LogSource(open(self.logfile_path, 'r'))
		logsource.pattern = self.pattern
		logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.SOURCES = [logsource]

		output = logdog.OutputFormat('%(ts)s test\n')
		output.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.OUTPUT = output

		file = open(self.logfile_path, 'r')
		expected = [l[:15]+' test\n' for l in file]
		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(result, expected)
	
	def test_several_files(self):
		'''checklog should unite log records in right order''' 

		file_count = 3
		temp_files = []

		while file_count:
			file_count -= 1
			file = tempfile.TemporaryFile('w+')
			temp_files.append(file)

		# fill files in random order
		infile = open(self.logfile_path, 'r')
		for line in infile:
			outfile = random.choice(temp_files)
			outfile.write(line)
		for file in temp_files:
			file.flush()

		config = TestConfig()
		config.SOURCES = []
		for file in temp_files:
			file.seek(0)
			logsource = logdog.LogSource(file)
			logsource.pattern = self.pattern
			logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
			config.SOURCES.append(logsource)

		expected = list(open(self.logfile_path, 'r'))
		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(result, expected)
	
	def test_save_state(self):
		'''checklog should save last viewed timestamp'''

		fd, fname = tempfile.mkstemp()
		file = open(fname, 'w')
		lines = list(open(self.logfile_path, 'r'))
		
		file.writelines(lines[:5])
		file.flush()

		config = TestConfig()
		logsource = logdog.LogSource(open(fname, 'r'))
		logsource.pattern = self.pattern
		logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.SOURCES = [logsource]
		list(logdog.checklog(config, state=self.state))

		logsource.file = open(fname, 'r')
		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(len(result), 0)

		file.writelines(lines[5:])
		file.flush()

		expected = lines[5:]
		logsource.file = open(fname, 'r')
		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(result, expected)
	
	def test_accepts_empty(self):
		'''checklog should accept empty files'''

		file = tempfile.TemporaryFile('r')

		config = TestConfig()
		logsource = logdog.LogSource(file)
		logsource.pattern = self.pattern
		logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.SOURCES = [logsource]

		result = list(logdog.checklog(config, state=self.state))
		self.assertEqual(len(result), 0)
	
	def test_race_condition(self):
		'''checklog should return only new lines even if then done neary at
		same time'''

		fd, fname = tempfile.mkstemp()
		file = open(fname, 'w')
		def logger(msg):
			ts = time.strftime(self.ts_format)
			line = '%s alpha %s\n' % (ts, msg)
			file.write(line)
			file.flush()
			return line

		config = TestConfig()
		logsource = logdog.LogSource(open(fname, 'r'))
		logsource.pattern = self.pattern
		logsource.fields['ts'] = logdog.TimestampField(self.ts_format)
		config.SOURCES = [logsource]

		expected = [logger('hello1')]
		result = list(logdog.checklog(config, state=self.state))

		expected.append(logger('hello2'))
		logsource.file = open(fname, 'r')
		result += list(logdog.checklog(config, state=self.state))

		self.assertEqual(expected, result)

class LogSourceTest(unittest.TestCase):
	def setUp(self):
		'''prepare test logfile'''

		self.file = tempfile.TemporaryFile('w+')
		self.file.writelines(msg_list)
		self.file.flush()
		self.file.seek(0)
	
	def read_source(self, source):
		while source.next_record():
			yield source.record
	
	def test_next_record_eof(self):
		'''LogSource.next_record should return False if no more records'''

		source = logdog.LogSource(self.file)
		source.pattern = ''

		self.assertEqual(source.next_record(), True)
		self.assertEqual(source.next_record(), True)
		self.assertEqual(source.next_record(), True)
		self.assertEqual(source.next_record(), False)
	
	def test_parse_known_values(self):
		'''LogSource should parse string fields to known values'''

		result_list = [
			('warn', 'log entry 1'),
			('err', 'log entry 2'),
			('err', 'log entry 3'),
		]

		source = logdog.LogSource(self.file)
		source.pattern = r'^(?P<level>\w+): (?P<msg>.*)$'

		records = list(self.read_source(source))
		for i in range(len(result_list)):
			record = records[i]
			expected = result_list[i]
			self.assertEqual(record['level'], expected[0])
			self.assertEqual(record['msg'], expected[1])

	def test_invalid_pattern(self):
		'''LogSource should fail with invalid record pattern'''

		source = logdog.LogSource(self.file)
		source.pattern = r'^qwe: (?P<msg>.*)$'

		self.assertRaises(logdog.InvalidPattern, source.next_record)
	
	def test_record_size(self):
		'''LogSource should return records with same count of elements as
		group count in pattern (if they are not optional)'''

		test_data = [
			(r'', 0),
			(r'^(?P<f1>.*)$', 1),
			(r'^(?P<f1>\w+): (?P<f2>.*)$', 2),
			(r'^(?P<f1>\w+): (?P<f2>.*) (?P<f3>.*)$', 3),
		]

		for data in test_data:
			self.file.seek(0)
			source = logdog.LogSource(self.file)
			source.pattern = data[0]
			source.next_record()
			self.assertEqual(len(source.record), data[1])

	def test_full_match(self):
		'''LogSource should parse message list to record(str) list without
		loosing any characters'''

		source = logdog.LogSource(self.file)
		source.pattern = r'^(?P<msg>.*)$'
		records = list(self.read_source(source))
		for i in range(len(msg_list)):
			record = records[i]
			msg = msg_list[i][:-1]
			self.assertEqual(record['msg'], msg)
	
	def test_custom_field(self):
		'''LogSource should use custom field parse function'''

		class CustomField(logdog.Field):
			def parse(self, string):
				return 'test'

		source = logdog.LogSource(self.file)
		source.pattern = r'^(?P<msg>.*)$'
		source.fields['msg'] = CustomField()

		records = list(self.read_source(source))
		for record in records:
			self.assertEqual(record['msg'], 'test')

class OutputFormatTest(unittest.TestCase):
	def test_original(self):
		'''OriginalFormat should format record as original string'''

		record = logdog.LogRecord('hello world\n', {'a1': 'hello', 'a2': 'world'})
		result = logdog.OriginalFormat().format(record)
		self.assertEqual(result, 'hello world\n')

	def test_template(self):
		'''OutputFormat should format record according to template'''

		record = logdog.LogRecord('\n', {'a1': 'hello', 'a2': 'world'})
		format = logdog.OutputFormat('%(a1)s %(a2)s\n')
		result = format.format(record)
		self.assertEqual(result, 'hello world\n')
	
	def test_custom_field(self):
		'''OutputFormat should use custom field output format'''

		class CustomField(logdog.Field):
			def format(self, value):
				return 'world'

		record = logdog.LogRecord('\n', {'a1': 'hello', 'a2': ''})
		format = logdog.OutputFormat('%(a1)s %(a2)s\n')
		format.fields['a2'] = CustomField()

		result = format.format(record)
		self.assertEqual(result, 'hello world\n')

class StringField(unittest.TestCase):
	def test_parse_sanity(self):
		'''StringField should parse strings to themselfs'''

		f = logdog.StringField()
		for msg in msg_list:
			self.assertEqual(f.parse(msg), msg)
	
	def test_format_sanity(self):
		'''StringField should format strings to themselfs'''

		f = logdog.StringField()
		for msg in msg_list:
			self.assertEqual(f.format(msg), msg)
	
class TimestampField(unittest.TestCase):
	def test_parse_known_values(self):
		'''TimestampField should parse timestamp strings to known values'''

		ts = datetime.datetime
		known_values = [
			('%d %b %y', [
				('30 Nov 00', ts(2000, 11, 30)),
				('1 Jan 01', ts(2001, 1, 1)),
				('02 Feb 99', ts(1999, 2, 2)),
			]),
			('%Y-%m-%dT%H:%M:%S', [
				('2002-12-25T00:00:00', ts(2002, 12, 25)),
				('1999-01-02T03:04:05', ts(1999, 1, 2, 3, 4, 5)),
			]),
		]

		for format_example in known_values:
			f = logdog.TimestampField(format_example[0])
			log = [example[0] for example in format_example[1]]
			for i in range(len(log)):
				input = log[i]
				expected = format_example[1][i][1]
				self.assertEquals(f.parse(input), expected)
	
	def test_parse_unknown_year(self):
		'''TimestampField should handle unknown year smart'''

		ts = datetime.datetime
		ts_format = '%b %d %H:%M:%S'

		now = ts.now()
		values = [
			['Jan 1 1:01:01', ts(now.year, 1, 1, 1, 1, 1)],
			['Mar 1 1:01:01', ts(now.year, 3, 1, 1, 1, 1)],
			['Apr 02 02:03:04', ts(now.year, 4, 2, 2, 3, 4)],
			['Oct 17 12:30:00', ts(now.year, 10, 17, 12, 30, 0)],
			['Dec 31 23:59:59', ts(now.year, 12, 31, 23, 59, 59)],
		]

		for value in values:
			t = value[1]
			if t > now:
				value[1] = t.replace(year=now.year-1)

		f = logdog.TimestampField(ts_format)
		for string, t in values:
			self.assertEqual(f.parse(string), t)

	def test_parse_invalid_format(self):
		'''TimestampField should fail with invalid format'''

		invalid_formats = [
			('%H', '24'),
			('%M', '60'),
			('%S', '99'),
			('%m', '13'),
			('%b', 'Foo')
		]

		for format in invalid_formats:
			f = logdog.TimestampField(format[0])
			input = format[1]
			self.assertRaises(logdog.InvalidStrftime, f.parse, input)
	
	def test_format_known_values(self):
		'''TimestampField should format timestamps to known strings'''

		ts = datetime.datetime
		known_values = [
			('%d %b %y', [
				('30 Nov 00', ts(2000, 11, 30)),
				('01 Jan 01', ts(2001, 1, 1)),
				('02 Feb 99', ts(1999, 2, 2)),
			]),
			('%b %d %H:%M:%S', [
				('Oct 17 12:30:00', ts(1900, 10, 17, 12, 30, 0)),
				('Mar 01 01:01:01', ts(1900, 3, 1, 1, 1, 1)),
				('Apr 02 02:03:04', ts(1900, 4, 2, 2, 3, 4)),
			]),
			('%Y-%m-%dT%H:%M:%S', [
				('2002-12-25T00:00:00', ts(2002, 12, 25)),
				('1999-01-02T03:04:05', ts(1999, 1, 2, 3, 4, 5)),
			]),
		]

		for format_example in known_values:
			f = logdog.TimestampField(format_example[0])
			log = [example[1] for example in format_example[1]]
			for i in range(len(log)):
				input = log[i]
				expected = format_example[1][i][0]
				self.assertEquals(f.format(input), expected)

if __name__ == '__main__':
	unittest.main()
