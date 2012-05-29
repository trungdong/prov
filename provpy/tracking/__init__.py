# Copyright 2012 by Trung Dong Huynh. All Rights Reserved.
# This module is modeled from python's logging module by Vinay Sajip, whose code is partly reused.

from collections import defaultdict
import datetime, weakref, sys, traceback
from model import *
import inspect
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



#
#raiseExceptions is used to see if exceptions during handling should be
#propagated
#
raiseExceptions = 1

# Thread-safe guarantees, borrowed from python's logging module
try:
    import thread
    import threading
except ImportError:
    thread = None
    
if thread:
    _lock = threading.RLock()
else:
    _lock = None
    
def _acquireLock():
    if _lock:
        _lock.acquire()
        
def _releaseLock():
    if _lock:
        _lock.release()

#---------------------------------------------------------------------------
#   Handler classes and functions
#---------------------------------------------------------------------------

_handlers = weakref.WeakValueDictionary()  #map of handler names to handlers
_handlerList = [] # added to allow handlers to be removed in reverse of order initialized

def _removeHandlerRef(wr):
    """
    Remove a handler reference from the internal cleanup list.
    """
    # This function can be called during module teardown, when globals are
    # set to None. If _acquireLock is None, assume this is the case and do
    # nothing.
    if _acquireLock is not None:
        _acquireLock()
        try:
            if wr in _handlerList:
                _handlerList.remove(wr)
        finally:
            _releaseLock()

def _addHandlerRef(handler):
    """
    Add a handler to the internal cleanup list using a weak reference.
    """
    _acquireLock()
    try:
        _handlerList.append(weakref.ref(handler, _removeHandlerRef))
    finally:
        _releaseLock()
        
class Handler(object):
    """
    Handler instances dispatch logging events to specific destinations.

    The base handler class. Acts as a placeholder which defines the Handler
    interface. Handlers can optionally use Formatter instances to format
    records as desired. By default, no formatter is specified; in this case,
    the 'raw' message as determined by record.message is logged.
    """
    def __init__(self):
        """
        Initializes the instance - basically setting the formatter to None
        and the filter list to empty.
        """
        self._name = None
        # Add the handler to the global _handlerList (for cleanup on shutdown)
        _addHandlerRef(self)
        self.createLock()

    def get_name(self):
        return self._name

    def set_name(self, name):
        _acquireLock()
        try:
            if self._name in _handlers:
                del _handlers[self._name]
            self._name = name
            if name:
                _handlers[name] = self
        finally:
            _releaseLock()

    name = property(get_name, set_name)

    def createLock(self):
        """
        Acquire a thread lock for serializing access to the underlying I/O.
        """
        if thread:
            self.lock = threading.RLock()
        else:
            self.lock = None

    def acquire(self):
        """
        Acquire the I/O thread lock.
        """
        if self.lock:
            self.lock.acquire()

    def release(self):
        """
        Release the I/O thread lock.
        """
        if self.lock:
            self.lock.release()

    def emit(self, record):
        """
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        """
        raise NotImplementedError('emit must be implemented '
                                  'by Handler subclasses')

    def handle(self, record):
        """
        Conditionally emit the specified logging record.

        Emission depends on filters which may have been added to the handler.
        Wrap the actual emission of the record with acquisition/release of
        the I/O thread lock. Returns whether the filter passed the record for
        emission.
        """
        self.acquire()
        try:
            self.emit(record)
        finally:
            self.release()

    def flush(self):
        """
        Ensure all logging output has been flushed.

        This version does nothing and is intended to be implemented by
        subclasses.
        """
        pass

    def close(self):
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        _handlers, which is used for handler lookup by name. Subclasses
        should ensure that this gets called from overridden close()
        methods.
        """
        #get the module data lock, as we're updating a shared structure.
        _acquireLock()
        try:    #unlikely to raise an exception, but you never know...
            if self._name and self._name in _handlers:
                del _handlers[self._name]
        finally:
            _releaseLock()

    def handleError(self, record):
        """
        Handle errors which occur during an emit() call.

        This method should be called from handlers when an exception is
        encountered during an emit() call. If raiseExceptions is false,
        exceptions get silently ignored. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        """
        if raiseExceptions:
            ei = sys.exc_info()
            try:
                traceback.print_exception(ei[0], ei[1], ei[2],
                                          None, sys.stderr)
                sys.stderr.write('Logged from file %s, line %s\n' % (
                                 record.filename, record.lineno))
            except IOError:
                pass    # see issue 5971
            finally:
                del ei    


class StreamHandler(Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a stream. Note that this class does not close the stream, as
    sys.stdout or sys.stderr may be used.
    """

    def __init__(self, stream=None):
        """
        Initialize the handler.

        If stream is not specified, sys.stderr is used.
        """
        Handler.__init__(self)
        if stream is None:
            stream = sys.stderr
        self.stream = stream

    def flush(self):
        """
        Flushes the stream.
        """
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            stream = self.stream
            fs = "%s\n"
            stream.write(fs % str(record))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
            
            
class Manager(object):
    def __init__(self, rootnode):
        self.root = rootnode
        self.disable = 0
        self.emittedNoHandlerWarning = 0
        self.loggerDict = {}
        self.loggerClass = None
        
    def getLogger(self, name):
        return self.root

class ProvLogger(object):
    def __init__(self):
        self.prov = ProvContainer()
        self.counters = defaultdict(int)
        self.entity_id_map = dict()
        self.handlers = []
        self.disabled = 0
    
    def handle(self, record):
        """
        Call the handlers for the specified record.

        This method is used for unpickled records received from a socket, as
        well as those created locally. Logger-level filtering is applied.
        """
        if (not self.disabled):
            self.callHandlers(record)

    def addHandler(self, hdlr):
        """
        Add the specified handler to this logger.
        """
        _acquireLock()
        try:
            if not (hdlr in self.handlers):
                self.handlers.append(hdlr)
        finally:
            _releaseLock()

    def removeHandler(self, hdlr):
        """
        Remove the specified handler from this logger.
        """
        _acquireLock()
        try:
            if hdlr in self.handlers:
                self.handlers.remove(hdlr)
        finally:
            _releaseLock()

    def callHandlers(self, record):
        """
        Pass a record to all relevant handlers.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. If no handler was found, output a one-off error
        message to sys.stderr. Stop searching up the hierarchy whenever a
        logger with the "propagate" attribute set to zero is found - that
        will be the last logger whose handlers are called.
        """
        found = 0
        for hdlr in self.handlers:
            found = found + 1
            hdlr.handle(record)
        if (found == 0) and raiseExceptions and not self.manager.emittedNoHandlerWarning:
            sys.stderr.write("No handlers could be found for logger"
                             " \"%s\"\n" % self.name)
            self.manager.emittedNoHandlerWarning = 1
    
    def get_identifier(self, entity_type):
        current_count = self.counters[entity_type] + 1
        self.counters[entity_type] = current_count
        identifier = '%s_%d' % (entity_type, current_count) 
        return self.prov.valid_identifier(identifier)
    
    def get_object_identifier(self, entity):
        identity = id(entity)
        if identity in self.entity_id_map:
            return self.entity_id_map[identity]
        else:
            entity_id = self.get_identifier('entity')
            self.entity_id_map[identity] = entity_id
            return entity_id
    
    def activity(self, activity_type, startTime=None, endTime=None, extra_attributes=None):
        record = self.prov.activity(self.get_identifier(activity_type), startTime, endTime, extra_attributes)
        return record

class RootLogger(ProvLogger):
    pass

root = RootLogger()
ProvLogger.root = root
ProvLogger.manager = Manager(root) 

def getLogger(asserter=None):
    return ProvLogger.manager.getLogger(asserter)

root.addHandler(StreamHandler())

class ActivityLogRecord(object):
    def __init__(self, activity, provlogger):
        self.activity = activity
        self.prov_graph = activity.get_prov_graph()
        self.records = [activity]
        self.provlogger = provlogger
        
    def __str__(self):
        return '\n'.join(map(str, self.records))
    
    def set_time(self, startTime, endTime):
        self.activity.set_time(startTime, endTime)
        
    def add_attributes(self, attributes):
        self.activity.add_extra_attributes(attributes)
        
    def entity(self, identifier, attributes={}):
        entity_record = self.prov_graph.get_record(identifier)
        if entity_record is None:
            entity_record = self.prov_graph.entity(identifier, attributes)
            self.records.append(entity_record)
        return entity_record
    
    def get_entity_id(self, entity, attributes={}):
        entity_id = self.provlogger.get_object_identifier(entity)
        if self.prov_graph.get_record(entity_id) is None:
            self.entity(entity_id, attributes)
        return entity_id

    def uses(self, entity_id, attributes={}):
        time = datetime.datetime.now()
        entity = self.entity(entity_id)
        usage_record = self.prov_graph.used(self.activity, entity, time, other_attributes=attributes)
        self.records.append(usage_record)
        return usage_record
    
    def uses_object(self, entity, attributes={}, entity_attributes={}):
        entity_id = self.get_entity_id(entity, entity_attributes)
        return self.uses(entity_id, attributes)
        
    def generates(self, entity_id, attributes={}):
        time = datetime.datetime.now()
        entity = self.entity(entity_id)
        generation_record = self.prov_graph.wasGeneratedBy(entity, self.activity, time, other_attributes=attributes)
        self.records.append(generation_record)
        return generation_record
    
    def generates_object(self, entity, attributes={}, entity_attributes={}):
        entity_id = self.get_entity_id(entity, entity_attributes)
        return self.generates(entity_id, attributes)
        
    def derives(self, generated_entity_id, used_entity_id, attributes={}):
        time = datetime.datetime.now()
        generated_entity = self.entity(generated_entity_id)
        used_entity_id = self.entity(used_entity_id)
        derivation_record = self.prov_graph.wasDerivedFrom(generated_entity, used_entity_id, self.activity, time=time, other_attributes=attributes)
        self.records.append(derivation_record)
        return derivation_record
    
    def derives_object(self, generated_entity, used_entity, attributes={}, gen_entity_attributes={}, used_entity_attributes={}):
        generated_entity_id = self.get_entity_id(generated_entity, gen_entity_attributes)
        used_entity_id = self.get_entity_id(used_entity, used_entity_attributes)
        return self.derives(generated_entity_id, used_entity_id, attributes)
    
class Activity(object):
    def __init__(self, activity_type=None, extra_attributes=None, provlogger=root):
        self.activity_type = activity_type
        self.extra_attributes = extra_attributes
        self.provlogger = provlogger
        
    def __call__(self, fn):
        if self.activity_type is None:
            self.activity_type = fn.func_name
        
        def activity_wrapper(*args, **kwargs):
            # Create an generic activity log record from the template
            activity = self.new_activity_log_record()
            # Record the start time
            startTime = datetime.datetime.now()
            try:
                # Call the actual function and store the result
                result = fn(*args, **kwargs)
                # Return the result from the function call above
                return result
            finally:
                # Record the end time
                endTime = datetime.datetime.now()
                # Store the timing with the activity
                activity.set_time(startTime, endTime)
                # Handle the activity record
                self.provlogger.handle(activity)
                
        return activity_wrapper
    
    def new_activity_log_record(self):
        # Create an generic activity from the template
        activity = self.provlogger.activity(self.activity_type, extra_attributes=self.extra_attributes)
        return ActivityLogRecord(activity, self.provlogger)
        
    
def current_activity():
    frame = inspect.currentframe().f_back.f_back;
    try:
        # TODO Check for cases where the activity cannot be found
        # (e.g. the main function is wrapped multiple times)
        while True:
            if frame is None:
                # Can't go back any further
                raise Exception
            if 'activity' in frame.f_locals:
                return frame.f_locals.get('activity')
            frame = frame.f_back;
    finally:
        # Delete the frame object to break the reference cycle
        # (allowing it to be garbage collected and avoiding memory leak)
        del frame