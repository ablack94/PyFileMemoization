# Andrew Black
# December 3, 2017
# Decorator to support function memoization
# This is specifically designed for functions that return large results, and
#	the results need to be memoized across runs which is why files are used.
#	This should NOT be used for general functional memoization as there are
#	more efficient methods that can be used if memoization is only needed
#	for the life of the interpreter.

import os
import glob
import tempfile
import pickle
import hashlib
import operator as op

from collections import namedtuple

from functools import reduce, wraps

MemoizationEntry = namedtuple('MemoizationEntry', 'file,value')

class MemoizationManager(object):
	def __init__(self, max_size=100, path=tempfile.gettempdir(), lazy=True):
		self.path = path
		self.mapping = {}
		self._lazy = lazy
		# Load mapping from existing .memo files
		for f in glob.glob(os.path.join(self.path, '*.memo')):
			with open(f, 'rb') as fd:
				key = pickle.load(fd)
				print("[MEMO] Loaded {} - {}".format(f, key))
				if lazy:
					def value():
						with open(f, 'rb') as fd:
							pickle.load(fd) # Skip args
							return pickle.load(fd) # Value
				else:
					value = lambda: pickle.load(fd)
				self.mapping[key] = MemoizationEntry(f, value)
	
	def getFilePath(self, key):
		return os.path.join(self.path, '{}.memo'.format(str(key)))

	def get(self, key):
		'''Returns (cached, value)
		cached - boolean representing if the key exists in cache.
		value - the cached value.'''
		# Return value if it's cached
		print("[MEMO] GET - {}".format(key))
		rval = (False, None) # We don't have it
		if key in self.mapping:
			rval = (True, self.mapping[key].value())
		return rval

	def put(self, key, value):
		print("[MEMO] PUT - {}".format(key))
		# Serialize to file
		with tempfile.NamedTemporaryFile('wb', dir=self.path,
				suffix='.memo', delete=False) as fd:
			pickle.dump(key, fd)
			pickle.dump(value, fd)
			fname = fd.name
		# Create memoization entry
		self.mapping[key] = MemoizationEntry(fname, lambda: value)

def memoize(f, manager=None):
	if manager is None:
		manager = MemoizationManager()
	
	@wraps(f)
	def wrapper(*args, **kwargs):
		print("DECORATOR: {}, {}".format(args, kwargs))
		rkwargs = { k:v for k,v in kwargs.items()
			if k is not 'no_memoize' }
		# Get a standard format tuple of the arguments
		# Arguments are stored as (positional, kwargs_keys, kwargs_values)
		_keys = sorted(rkwargs.keys())
		key = (args, tuple(_keys), tuple([rkwargs[x] for x in _keys]))	
		# Check cache
		if 'no_memoize' not in kwargs:
			cached, value = manager.get(key)
			if cached:
				print("[memo] GOT CACHED VALUE")
				return value
		# memoization is either disabled or result is not cached
		result = f(*args, **rkwargs) # evaluate function to get result
		manager.put(key, result) # cache result
		return result
	return wrapper

