'''
logdog - system log maintenance tools
'''

import re
import time
import datetime
import checklog

class LogdogError(Exception):
	pass

class InvalidPattern(LogdogError):
	pass

class InvalidStrftime(LogdogError):
	pass

class LogRecord(dict):
	def __init__(self, line, groups):
		super(LogRecord, self).__init__(groups)
		self.line = line
	
	def __str__(self):
		return self.line

class LogSource(object):
	def __init__(self, file):
		self.fields = dict()
		self.file = file
		self.record = None
		self.regex = None
	
	def parse_line(self, line):
		if line[-1] == '\n':
			linenb = line[:-1]
		else:
			linenb = line
		match = self.regex.search(linenb)
		if not match:
			raise InvalidPattern(
				'pattern /%s/ does not found in line "%s"' % \
					(self.pattern, linenb))

		record = LogRecord(line, match.groupdict())
		for field in self.fields.keys():
			try:
				string = record[field]
			except KeyError:
				pass
			else:
				record[field] = self.fields[field].parse(string)
		return record

	def next_record(self):
		line = self.file.readline()
		if line:
			self.record = self.parse_line(line)
			return True
		else:
			return False

	@property
	def pattern(self):
		try:
			return self.regex.pattern
		except AttributeError:
			return None

	@pattern.setter	
	def pattern(self, value):
		self.regex = re.compile(value)

class OutputFormat(object):
	def __init__(self, template):
		self.template = template
		self.fields = dict()
	
	def format(self, record):
		context = dict(record)
		for field in self.fields.keys():
			try:
				value = context[field]
			except KeyError:
				pass
			else:
				context[field] = self.fields[field].format(value)
		return self.template % context

class OriginalFormat(OutputFormat):
	def __init__(self):
		pass

	def format(self, record):
		return str(record)

class Field(object):
	def parse(self, string):
		return string

	def format(self, value):
		return value

class StringField(Field):
	pass

class TimestampField(Field):
	def __init__(self, strftime):
		self.strftime = strftime
		self.now = datetime.datetime.now()

	def parse(self, string):
		try:
			t = time.strptime(string, self.strftime)
		except ValueError:
			raise InvalidStrftime(
				'invalid timestamp format "%s" for string "%s"' % \
					(self.strftime, string))
		if t.tm_year == 1900:
			ts = datetime.datetime(self.now.year, *tuple(t)[1:6])
			if ts - self.now > datetime.timedelta(minutes=1):
				ts = ts.replace(year=self.now.year-1)
		else:
			ts = datetime.datetime(*tuple(t)[:6])
		return ts

	def format(self, value):
		return time.strftime(self.strftime, value.timetuple())

def fetch(sources):
	sources_work = list(sources)
	for src in sources:
		if not src.next_record():
			sources_work.remove(src)
	while sources_work:
		src = min(sources_work, key=lambda x: x.record['ts'])
		record = src.record
		if not src.next_record():
			sources_work.remove(src)
		yield record

def fetch_time_safe(sources):
	record = None

	for record in fetch(sources):
		yield record

	# after fetching all records wait 1 second for
	# new records, so last returned record will be
	# really last in this second
	if record:
		now = datetime.datetime.now()
		one_sec = datetime.timedelta(seconds=1)
		if now - record['ts'] < one_sec:
			time.sleep(1)
			until = (record['ts'] + one_sec).replace(microsecond=0)
			for record in fetch(sources):
				if record['ts'] >= until:
					break
				yield record
