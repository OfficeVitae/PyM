import sys,socket,Queue,time
from threading import Thread
# UDPCommunicator allows sending and receiving text with another UDP sender/receiver
class UDPCommunicator(Thread):
	# keep listening for text send by the peer device
	def run(self):
		self.keeplistening=True
		# create the receive socket
		self.recvsocket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.recvsocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		# some non-blocking might be ok, so we can stop it
		if self.recvtimeout is not None:
			self.recvsocket.settimeout(self.recvtimeout) # block no longer than 0.05 seconds
		self.recvsocket.bind(('',self.recvport))
		while self.keeplistening:
			try:
				(recvtext,recvaddress)=self.recvsocket.recvfrom(1024) # blocks (indefinitely)
				if isinstance(recvtext,str):
					######if self.debug>1:
					#####print "Received: '"+recvtext+"'."
					# remember the sender if this is the first time (so we won't keep broadcasting)
					if self.sendhost is None:
						self.sendhost=recvaddress[0]
					self.recvqueue.put(recvtext) # block until we get a free slot
					if callable(self.recvprocessor):
						self.recvprocessor(self)
					elif self.recvprocessor is not None and self.debug>0:
						print "BUG: The text receive processor function apparently is not callable anymore!"
			except socket.timeout: # NOT to output this type of 'error'
				pass
			except Exception,ex:
				if self.debug>0:
					print "ERROR: '"+str(ex)+"' listening for text sent."
			finally:
				time.sleep(0.1) # sleep a bit
		# done listening for incoming messages, so no need for the receive socket anymore!!
		self.recvsocket=None # will close the receive socket at garbage collection
	def getSomethingReceivedLeft(self):
		return not self.recvqueue.empty()
	def getReceived(self):
		if self.recvqueue.empty():
			return None
		return self.recvqueue.get()
	# we should allow to stop receiving
	def stopReceiving(self):
		if self.startedlistening: # we did start the Thread!
			if self.keeplistening:
				self.keeplistening=False
				self.join() # blocks the calling thread until this thread is actually finished (TODO is that good?)
	def stopSending(self):
		self.sendsocket=None
	def setDebug(self,_debug):
		if isinstance(_debug,int):
			self.debug=_debug
	# the receive timeout defaults to 0, in which case the timeout is set to 1 second!
	# if you pass in None it will block indefinitely (not recommended if you want to do
	# other stuff as well (which you would!)
	def __init__(self,_sendport,_recvport,_recvtimeout=0):
		Thread.__init__(self)
		self.debug=0 # do not output anything by default
		self.keeplistening=False
		self.startedlistening=False
		self.sendport=_sendport
		self.recvport=_recvport
		# the timeout seconds needs to be positive (or None)
		if _recvtimeout is None or (isinstance(_recvtimeout,(int,float)) and _recvtimeout>0):
			self.recvtimeout=_recvtimeout
		else:
			self.recvtimeout=1
		self.recvprocessor=None
		self.sendhost=None # start with broadcasting until we receive something
		self.receivesocket=None
		self.recvqueue=Queue.Queue() # a thread-safe queue for storing the texts received
		# no sweat preparing for sending immediately (as we use self.sendsocket is None to indicate finished sending!!!)
		self.sendsocket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
		self.sendsocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1) # initially do broadcasting until we receive something
	def go(self,_recvprocessor=None):
		if callable(_recvprocessor):
			self.recvprocessor=_recvprocessor
		elif _recvprocessor is not None and self.debug>0:
			print "ERROR: Receive processor function ("+str(_recvprocessor)+") not registered: it is not callable."
		# prevent calling Thread.start() more than once (as that would raise an exception)
		if not self.startedlistening:
			self.startedlistening=True
			Thread.start(self)
		return self
	def sent(self,_str):
		# sends _str to (self.sendhost,self.sendport)
		# NOTE after stopSending() (called from stop()) self.sendsocket will be None!!!
		#######print "Sending: '"+_str+"'."
		try:
			result=self.sendsocket.sendto(_str,(('<broadcast>',self.sendhost)[self.sendhost is not None],self.sendport))
			# if not started listening yet, start right away (although preferable to call start() immediately
			if not self.startedlistening:
				self.start()
		except:
			result=-1
		return result
	def stop(self):
		self.stopSending()
		self.stopReceiving() # will block until receiving is finishes...
	def __destroy__(self):
		self.stop()
	def __str__(self):
		return "UDPCommunicator("+str(self.sendport)+","+str(self.recvport)+")"
	def __equals__(self,_udpcommunicator):
		if not isinstance(_udpcommunicator,UDPCommunicator):
			return False
		return self.sendport==_udpcommunicator.sendport and self.recvport==_udpcommunicator.recvport
	def getSendPort(self):
		return self.sendport
	def getReceivePort(self):
		return self.recvport
	def usesPort(self,_port):
		return self.sendport==_port or self.recvport==_port
# testing...
udpCommunicator=None
def processReceived(_udpCommunicator):
	while _udpCommunicator.getSomethingReceivedLeft():
		print "Received from '"+str(_udpCommunicator)+"': '"+_udpCommunicator.getReceived()+"'."
def main(args):
	if len(args)<2:
		print "Two arguments are required: the port to send on and the port to receive on!"
		return
	global udpCommunicator
	udpCommunicator=UDPCommunicator(int(args[0]),int(args[1])).start(processReceived)
	print "UDP Communicator started..."
	while 1:
		try:
			tosend=raw_input("What do you want to send? ")
			if len(tosend)>0:
				print "Number of bytes sent: "+str(udpCommunicator.sent(tosend))+"."
			else:
				print "Exiting: nothing to send!"
				break
		except Exception,ex:
			print "ERROR: '"+str(ex)+"'."
	udpCommunicator.stop()
	print "UDP Communicator stopped..."
	udpCommunicator=None
	sys.exit(0)

if __name__=="__main__":
	main(sys.argv[1:])
