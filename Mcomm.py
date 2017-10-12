# test of UDP broadcasting using UDPCommunicator
from udpcommunicator import UDPCommunicator
import time
class UDPCommunicatorReceivedList(list):
	def __init__(self,_udpCommunicator):
		self.udpCommunicator=_udpCommunicator
DEBUG=0 # by default do NOT debug
def setDebug(_debug):
	global DEBUG
	if isinstance(_debug,int):
		DEBUG=_debug
	else: # return to the default
		DEBUG=0
# function to process what was received by a specific UDPCommunicator
udpCommunicatorManager=None # created later on
def processReceived(_udpCommunicator):
	#####print "Processing what was received from "+str(_udpCommunicator)+"..."
	while _udpCommunicator.getSomethingReceivedLeft():
		udpCommunicatorManager.processReceived(_udpCommunicator,_udpCommunicator.getReceived())
class UDPCommunicatorManager(list):
	def __init__(self,_debug=None):
		list.__init__(self)
		self.received=dict()
	def processReceived(self,_udpCommunicator,_received):
		try:
			if DEBUG>1:
				print "Received from "+str(_udpCommunicator)+": '"+str(_received)+"'."
			udpCommunicatorIndex=self.index(_udpCommunicator)
			if udpCommunicatorIndex in self.received: # waiting for it
				self.received[udpCommunicatorIndex].append(_received)
			elif DEBUG>1:
				print "WARNING: '"+str(_received)+"' received from "+str(_udpCommunicator)+" ignored: received out of order."
		except Exception,ex:
			if DEBUG>0:
				print "ERROR: '"+str(ex)+"' processing "+_received+" received from "+str(_udpCommunicator)+"."
	def somethingReceived(self,_brindex):
		try:
			# if not ready to receive something, get ready
			if not _brindex in self.received:
				self.received[_brindex]=list()
			return len(self.received[_brindex])>0
		except Exception,ex:
			if DEBUG>0:
				print "ERROR: '"+str(ex)+"' checking if something received on channel #"+str(_brindex)+"."
		return False
	def mute(self,_brindex): # returns whatever's discarded by removing what was received
		if _brindex in self.received:
			discarded=self.received[_brindex]
			del self.received[_brindex] # quickest way is to simply delete the entry in self.received
		else:
			discarded=None
		return discarded
	def getFirstReceived(self,_brindex):
		if _brindex in self.received and len(self.received[_brindex])>0:
			return self.received[_brindex].pop(0)
		return None
	def getReceived(self,_brindex):
		# returns what was received by the associated UDPCommunicator() and consumes that list
		result=list()
		try:
			if _brindex in self.received:
				while len(self.received[_brindex])>0:
					result.append(self.received[_brindex].pop(0))
		except Exception,ex:
			if DEBUG>0:
				print "ERROR: '"+str(ex)+"' popping off text received."
		return result
	def listen(self,_brindex):
		# let's return the number of messages received that is discarded
		if _brindex in self.received:
			discarded=self.received[_brindex]
		else:
			discarded=None
		self.received[_brindex]=list() # prepare for receiving whatever's coming in (overwriting anything received in the meanwhile that is now lost)
		return discarded
	def appended(self,_udpCommunicator):
		try:
			# NOTE start() returns the UDP Communicator instance itself
			#      TODO should we throw an exception when start() fails?????
			self.append(_udpCommunicator)
			########print "UDP Communicator "+str(self[len(self)-1])+" added..."
			_udpCommunicator.setDebug(DEBUG) # make the appended communicator have the same DEBUG level
			#########self.received[_brindex]=list() # wait with setting the receive list until brin() is called!!!!
			_udpCommunicator.go(processReceived) # get the communicator going!!
			return True
		except Exception,ex:
			if DEBUG>0:
				print "ERROR: '"+str(ex)+"' registering an UDP communicator."
		return False
	def done(self):
		while len(self)>0:
			print "Closing communication channel #"+str(len(self))+"..."
			udpCommunicator=self.pop(0)
			if udpCommunicator is not None:
				udpCommunicator.stop()
	def __destroy__(self):
		self.done()
udpCommunicatorManager=UDPCommunicatorManager() # our UDPCommunicators() instance managing the communicators
# main level methods for opening, closing and using UDPCommunicator instances
# MDH@12OCT2017: brstart() now returns the position (1-based) of the communication channel (replacing the 0-based index)
def brstart(_sendport,_recvport):
	global udpCommunicatorManager
	for (index,udpCommunicator) in enumerate(udpCommunicatorManager):
		if udpCommunicator is None:
			continue
		if udpCommunicator.getSendPort()==_sendport and udpCommunicator.getReceivePort()==_recvport: # got it
			return (index+1)
		# both ports must not be in use right now
		if udpCommunicator.usesPort(_sendport) or udpCommunicator.usesPort(_recvport):
			return 0
	# NOTE appended() will get the thread started
	if not udpCommunicatorManager.appended(UDPCommunicator(_sendport,_recvport)):
		return -1 #####raise Exception("Failed to register the communicator sending at "+str(_sendport)+" and receiving at "+str(_recvport)+".")
	return len(udpCommunicatorManager)
def brend(_brindex):
	#######print "Ending UDP Communicator #"+str(_brindex)+"..."
	global udpCommunicatorManager
	try:
		udpCommunicator=udpCommunicatorManager[_brindex-1]
		if udpCommunicator is not None:
			udpCommunicator.stop() # stop to force waiting for the thread to die
			udpCommunicatorManager[_brindex-1]=None
		return True
	except Exception,ex:
		if DEBUG>0:
			print "ERROR: '"+str(ex)+"' closing communication channel #"+str(_brindex)+"."
	return False
# send something
def brout(_brindex,_tosend):
	global udpCommunicatorManager
	# are we going to keep waiting until we succeed?
	########print "Sending '"+_tosend+"'"
	if _brindex<=0 or _brindex>len(udpCommunicatorManager):
		print "ERROR: Communication channel #"+str(_brindex)+" does not exist!"
		return False
	try:
		udpCommunicator=udpCommunicatorManager[_brindex-1]
		if udpCommunicator is not None:
			sentcount=udpCommunicatorManager[_brindex-1].sent(_tosend)
		else:
			########print "UDP Communicator vanished!"
			sentcount=0
		#######print str(sentcount)
		if sentcount>=len(_tosend):
			return True
	except Exception,ex:
		####if DEBUG>0:
		print "ERROR: '"+str(ex)+"' outputting '"+_tosend+"' to communication channel #"+str(_brindex+1)+"."
	return False
# wait for receiving something, pass 0 for timeout to return immediately with what was received so far, nothing to wait indefinitely...
def brlisten(_brindex):
	global udpCommunicatorManager
	return udpCommunicatorManager.listen(_brindex-1)
def brmute(_brindex):
	global udpCommunicatorManager
	return udpCommunicatorManager.mute(_brindex-1)
# MDH@12OCT2017: use brfire() to fire a certain message repeatedly until the assumed ack response is received
def brfire(_brindex,_waitseconds,_ackresponse,_tosend):
	# reset listening, 
	result=brlisten(_brindex)
	if result:
		while brout(_brindex,_tosend):
			while udpCommunicationManager.somethingReceived(_brindex-1):
				received=udpCommunicationManager.getFirstReceived(_brindex-1)
				if received==_ackresponse: # and done!!!
					break
			if _waitseconds>0:
				time.sleep(_waitseconds) # wait a bit
	return result
def brin(_brindex,_maxwaitseconds=None):
	global udpCommunicatorManager
	# something might go wrong e.g. when you're trying to access an UDPCommunicator that
	# was already ended (through brend)
	try:
		if isinstance(_maxwaitseconds,float):
			timeoutms=int(1000*_timeoutms)
		elif isinstance(_maxwaitseconds,(int,long)):
			timeoutms=1000*_maxwaitseconds
		else: # by default do not time out i.e. wait indefinitely (which is dangerous)
			timeoutms=-1
		# if a timeout is used, we actually have to wait for something new to come in
		if timeoutms!=0:
			udpCommunicator.mute(_brindex)
		# wait until something is received
		while timeoutms!=0 and not udpCommunicatorManager.somethingReceived(_brindex-1):
			if timeoutms>0:
				timeoutms-=1
				if (timeoutms%100)==0:
					sys.stdout.write('~') # a bit dangerous?????
			time.sleep(0.001)
		# return whatever's received so far (even if nothing was received!!!)
		return udpCommunicatorManager.getReceived(_brindex-1)
	except Exception,ex:
		if DEBUG>0:
			print "ERROR: '"+str(ex)+"' waiting for input."
	return None
def brdone():
	global udpCommunicatorManager
	if udpCommunicatorManager is not None:
		udpCommunicatorManager.done()
		udpCommunicatorManager=None
