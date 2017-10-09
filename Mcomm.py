# test of UDP broadcasting using UDPCommunicator
from udpcommunicator import UDPCommunicator
from time import sleep
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
      if not udpCommunicatorIndex in self.received:
        self.received[udpCommunicatorIndex]=list()
      self.received[udpCommunicatorIndex].append(_received)
    except Exception,ex:
      if DEBUG>0:
        print "ERROR: '"+str(ex)+"' processing "+_received+" received from "+str(_udpCommunicator)+"."
  def somethingReceived(self,_brindex):
    try:
      return len(self.received[_brindex])>0
    except:
      pass
    return False
  def getReceived(self,_brindex):
    # returns what was received by the associated UDPCommunicator() and consumes that list
    result=list()
    try:
      while len(self.received[_brindex])>0:
        result.append(self.received[_brindex].pop(0))
    except Exception,ex:
      if DEBUG>0:
        print "ERROR: '"+str(ex)+"' popping off text received."
    return result
  def appended(self,_udpCommunicator):
    # you can't reuse ports so the ports used by _udpcommunicator should not be in use
    for udpCommunicator in self:
      if udpCommunicator.usesPort(_udpCommunicator.getSendPort()) or udpCommunicator.usesPort(_udpCommunicator.getReceivePort()):
        return False
    try:
      self.append(_udpCommunicator)
      _udpCommunicator.setDebug(DEBUG) # make the appended communicator have the same DEBUG level
      _udpCommunicator.go(processReceived)
      return True
    except Exception,ex:
      if DEBUG>0:
        print "ERROR: '"+str(ex)+"' registering an UDP communicator."
    return False
udpCommunicatorManager=UDPCommunicatorManager() # our UDPCommunicators() instance managing the communicators
# main level methods for opening, closing and using UDPCommunicator instances
def brstart(_sendport,_recvport):
  global udpCommunicatorManager
  udpCommunicator=UDPCommunicator(_sendport,_recvport)
  try:
    result=udpCommunicatorManager.index(udpCommunicator)
  except Exception,ex:
    if not isinstance(ex,ValueError) and DEBUG>0:
      print "ERROR: '"+str(ex)+"' starting "+str(udpCommunicator)+"."
    result=len(udpCommunicatorManager)
    if not udpCommunicatorManager.appended(udpCommunicator):
      raise Exception("Failed to register the communicator sending at "+str(_sendport)+" and receiving at "+str(_recvport)+".")
  return result
def brend(_brindex):
  global udpCommunicatorManager
  try:
    udpCommunicator=udpCommunicatorManager[_brindex]
    if udpCommunicator is not None:
      udpCommunicator.stop() # best to stop it
      udpCommunicatorManager[_brindex]=None
    return True
  except Exception,ex:
    if DEBUG>0:
      print "ERROR: '"+str(ex)+"' ending UDP communication #"+str(_brindex+1)+"."
  return False
# send something
def brout(_brindex,_tosend):
  global udpCommunicatorManager
  # are we going to keep waiting until we succeed?
  try:
    sentcount=udpCommunicatorManager[_brindex].sent(_tosend)
    if sentcount>=len(_tosend):
      return True
  except Exception,ex:
    if DEBUG>0:
      print "ERROR: '"+str(ex)+"' outputting '"+_tosend+"' to UDP communicator #"+str(_brindex+1)+"."
  return False
# wait for receiving something, pass 0 for timeout to return immediately with what was received so far, nothing to wait indefinitely...
def brin(_brindex,_timeoutms=None):
  global udpCommunicatorManager
  # something might go wrong e.g. when you're trying to access an UDPCommunicator that
  # was already ended (through brend)
  try:
    if isinstance(_timeoutms,float):
      timeoutms=int(1000*_timeoutms)
    elif isinstance(_timeoutms,(int,long)):
      timeoutms=_timeoutms
    else: # by default do not time out i.e. wait indefinitely (which is dangerous)
      timeoutms=-1
    # wait until something is received
    while timeoutms!=0 and not udpCommunicatorManager.somethingReceived(_brindex):
      if timeoutms>0:
        timeoutms-=1
      sleep(0.001)
    # return whatever's received so far (even if nothing was received!!!)
    return udpCommunicatorManager.getReceived(_brindex)
  except Exception,ex:
    if DEBUG>0:
      print "ERROR: '"+str(ex)+"' waiting for input."
  return None
