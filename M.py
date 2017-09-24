"""
Marc's expression tokenizer and evaluator
"""
""" History of development:
23SEP2017:
- defined and undefined functions added
22SEP2017:
- allowing continuation of expressions on successive lines (preferably indented with a tab)
- adding DEBUG to Menvironment, so it can be controlled in input mode!!!
21SEP2017:
- function 'sign', 'inch' (e.g. to be used in M.chess)
18SEP2017:
- function 'in' added, to get input from the end user
- bug fix: undiscontinued() called in backspace() method of Token when the suffix ends for non string literals, and otherwise when the last text token character is removed
16SEP2017:
- executecommand() to execute a shell command using the sh function
- execute shell command control mode option
- readvalues function to read values from (e.g. a CSV) text file
15SEP2017:
- functions and variables (dynamic value) environment identifiers, exposing the list of functions and variables respectively
13SEP2017:
- identifier (variable,function) continuation
- finishing storing expressions and functions
12SEP2017:
- naming of files: <owner>[.<functionname>[.<functionname>]].txt where <owner> is either M or any other owner
-									 I guess we could have multiple owners underscore or $ delimited, so instead of user we can have topics as well per user
-									 therefore no periods allowed in user names as well
03SEP2017:
- some personalization by requiring a 'login' by name (only), I suppose we make it
	impersonal if no Musers file is found!!!
02SEP2017:
- ability to start/end a function with a control message
		this is probably the easiest way to create a function and still have text input coloring while doing so
		I might need to adjust the prompt though (which we could change into the name of the function? which makes sense)
		this also allows creating subfunctions i.e. functions in functions
		we should also be able to store a function, I guess M could be considered a function as well
01SEP2017:
- replacing remembering ALL ColoredText instance of the current user input line I remember the TokenChar instance (which should be unendable easily)
31AUG2017:
- we want to change the color of an identifier when it is a known variable or function
18AUG2017:
- I want to be able to use empty lists as well so () should be an allowed construction, ending up with an expression with no tokens
- there should be a constant with value None or something similar, to indicate a No result or no value with a certain text representation
- how about void???? perhaps undefined is better?????
10AUG2017:
- Token constructor can also receive a token character to add immediately
- opening and closing parenthesis moved over to the prefix and suffix of an expression
"""
import copy
import sys
# method to read a single character
def getch():
	try:
		import termios
	except ImportError:
		# Non-POSIX. Return msvcrt's (Windows') getch.
		import msvcrt
		return msvcrt.getch
	# POSIX system. Create and return a getch that manipulates the tty.
	import tty
	fd=sys.stdin.fileno()
	old_settings=termios.tcgetattr(fd)
	try:
		tty.setraw(fd)
		ch=sys.stdin.read(1)
	finally:
		termios.tcsetattr(fd,termios.TCSADRAIN,old_settings)
	return ch

DEBUG_COLOR=8 # light gray
INFO_COLOR=0 # black
ERROR_COLOR=9 # red
IDENTIFIER_COLOR=202 # orange for unknown identifiers (although these would be used for assignments)
##VARIABLE_COLOR=13 # magenta
##FUNCTION_COLOR=93 # something more blueish
LITERAL_COLOR=22 # green
OPERATOR_COLOR=12 # blue
RESULT_COLOR=15 # quite dark
OPTION_COLOR=RESULT_COLOR

# the back colors
DEBUG_BACKCOLOR=255 # light-gray
INFO_BACKCOLOR=231 # white
ERROR_BACKCOLOR=231
IDENTIFIER_BACKCOLOR=231
LITERAL_BACKCOLOR=231
OPERATOR_BACKCOLOR=231
RESULT_BACKCOLOR=69
OPTION_BACKCOLOR=RESULT_BACKCOLOR
PROMPT_COLOR=INFO_COLOR # same as the info color

"""
SAVE_CURSOR_ANSICODE="\033[s"
RESTORE_CURSOR_ANSICODE="\033[u"
"""
# MDH@28AUG2017: how about using 256-color mode?? i.e. instead of using the color code directly behind [ we use 38;5; for foreground
#								 and 48;5; prefix for background colors
#								 getColorText() adapted to allow including a background color code as well!!
def getBackcolorText(_backcolor):
	if isinstance(_backcolor,int) and _backcolor>=0:
		return "\033[48;5;"+str(_backcolor)+"m"
	return ""
def getColorText(_color=None,_backcolor=None):
	backcolortext=getBackcolorText(_backcolor)
	if isinstance(_color,int) and _color>=0:
		if _color>0:
			return backcolortext+"\033[38;5;"+str(_color)+"m"
		return backcolortext+"\033[0m" # resetting all colors
	return backcolortext
# MDH@31AUG2017: if we want to be able to rewrite text in a different color we need to keep track of all colored text written
class ColoredText:
	def __init__(self,_text,_color,_backcolor):
		self.text=_text
		self.color=_color
		self.backcolor=_backcolor
	def length(self):
		return len(self.text)
	def getText(self):
		return self.text
	def __repr__(self):
		return self.getText()
	def __str__(self):
		return getColorText(self.color,self.backcolor)+self.text+"\033[0m" # TODO think about whether we need to append returning to the default color here???
	def setColor(self,_color):
		self.color=_color
	def setBackcolor(self,_backcolor):
		self.backcolor=_backcolor
	def getValue(self):
		return self.text
# convenient to be able to color certain text
def getColoredText(_text,_color,_backcolor=None):
	return str(ColoredText(_text,_color,_backcolor))
# main output method to be used to output any text directly
def output(_tooutput):
	sys.stdout.write(_tooutput)

# methods that write to the console themselves, and should be called by all other output producing functions/methods
# MDH@31AUG2017: it's going to be dificult to keep track of what's written on the same line behind the prompt and to rewrite it
#								 therefore we let write() keep track of all ColoredText instance written, and by separating the token characters by None ColoredText instances
#								 we can remove the last token character entered until None are left on the line!!!
def beep():
	output('\a')
def hidecursor():
	output("\033[?25l")
def showcursor():
	output("\033[?25h")
def emptyline(): # clears the current line and puts the cursor at the beginning of the current line
	output("\033[2K\r")
def backspace(): # means go one position to the left on the current line, and clear the rest of the line
	output("\033[D") # go left one character
	output("\033[K") # clear the rest of the line
########## MDH@01SEP2017 replaced by UserInputLine stuff: linecoloredtexts=[] # keep a list of ColoredText instances written on the current input (behind the prompt line)
# write outputs text to be colored
def write(_towrite,_color=None,_backcolor=None):
	if isinstance(_towrite,str): # if something to write, go ahead and write it
		result=ColoredText(_towrite,_color,_backcolor)
		output(str(result))
	else: # we're appending it as well to linecoloredtexts
		result=None
	########linecoloredtexts.append(result)
	return result # thus allowing manipulation of background and text color later on
# MDH@10SEP2017: sometimes we want to know what we would be written and not actually write it
def writeColoredText(_coloredText,_output):
	if _output:
		output(str(_coloredText))
	return _coloredText
def newline():
	"""
	global linecoloredtexts
	linecoloredtexts=[] # start over collecting linecoloredtext elements
	"""
	output("\n\033[0m") # it makes sense to reset the coloring at the start of each next line!!!
# end of output producing methods
"""
def rewriteline():
	# write the rest on the line again (this would include the prompt!!!)
	emptyline() # clear the current text line...
	for linecoloredtext in linecoloredtexts:
		if linecoloredtext is not None:
			output(str(linecoloredtext))
def removeDeletedTokenchar(): # removes the last token char written from the current line
	# keep popping ColoredText elements until we pop a None object, then write what's remaining
	global linecoloredtexts
	linecoloredtext=linecoloredtexts.pop() # most likely None ending the tokenchar
	while len(linecoloredtexts)>0:
		linecoloredtext=linecoloredtexts.pop()
		if linecoloredtext is None: # separator popped
			break
		# it's an idea to actually put an empty text at the end of the prompt to prevent to remove any of the prompt characters!!
		if linecoloredtext.length()==0: # oeps shouldn't happen!!!
			linecoloredtexts.append(linecoloredtext)
			beep()
			break
	rewriteline()
"""
# helper functions for outputting text
def writeln(_linetowrite,_backcolor=None,_color=None): # writes a line in black
	write(_linetowrite,_color,_backcolor) #####write(_linetowrite+'\n',_color,_backcolor)
	newline()
def lnwrite(_linetowrite,_backcolor=None,_color=None):
	# NOTE whatever's left of the current line we want to use the standard background color
	newline()
	write(_linetowrite,_color,_backcolor) # NOT using write assuming the newline will undo any coloring defined!!!
def lnwriteleft(_linetowrite,_width=120,_color=DEBUG_BACKCOLOR,_backcolor=None):
	dwidth=_width-len(_linetowrite)
	if dwidth>0:
		_linetowrite+=" "*dwidth
	lnwrite(_linetowrite,_color,_backcolor)
def writelnleft(_linetowrite,_width=120,_color=DEBUG_BACKCOLOR,_backcolor=None):
	dwidth=_width-len(_linetowrite)
	if dwidth>0:
		_linetowrite+=" "*dwidth
	writeln(_linetowrite,_color,_backcolor)

# \r at the start forces the cursor to be at the beginning of the line
# but it is a bit of a nuisance that the line might not be empty so can we do that here as well????
# as such it should either be preceded by newline() or emptyline()
# MDH@27AUG2017: allowing two modes of operation
modechars=":=" # the two mode characters (: in declaration mode and = in evaluation mode)
prompt=None
environment=None
def updateprompt():
	global prompt,environment
	prompt=environment.getPrompt()
def continueprompt():
	global prompt,environment
	prompt=(" "*(len(prompt)-2))+modechars[environment.mode]+" "
def writeprompt():
	write(prompt,PROMPT_COLOR)
	showcursor() # show the cursor for sure
def reprompt():
	emptyline()
	writeprompt()
def newprompt():
	#########lnwrite('Press Ctrl-D anytime to exit M, Ctrl-C to cancel any input.')
	updateprompt() # MDH@27AUG2017: we need a new prompt
	writeprompt()
def note(_note):
	writeln('\t'+_note)
def writeerror(_error):
	write(" "*len(prompt)) # go to a new line and start with as many blanks as the length of the prompt
	# write the error followed by a newline so we can show the user input line immediately
	if isinstance(_error,str) and len(_error)>0:
		writeln(_error,None,ERROR_COLOR) # we have to go to a new line afterwards because prompt(False) will clear the current line
	else:
		writeln(str(_error),None,ERROR_COLOR)

# MDH@16SEP2017: let's do some OS stuff
import subprocess
# explicit execution through the shell (which does NOT protect from shell injection and
# should only be used processing input from an actual user
def executeshellcommand(_command):
	return subprocess.call(_command,stderr=subprocess.STDOUT,shell=True)
# call executecommand to return the output as a list of text elements
def executecommand(_command):
	result=list()
	commandparts=_command.split(' ')
	process=subprocess.Popen(commandparts,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	(output,errors)=process.communicate()
	result.append(process.returncode) # first element is the return code
	if isinstance(output,str) and len(output)>0:
		result.append(map(enquote,output.strip().split(opsys.linesep)))
	else:
		result.append(None)
	if isinstance(errors,str) and len(errors)>0:
		result.append(map(enquote,errors.strip().split(opsys.linesep)))
	else:
		result.append(None)
	return result
	"""
	cmd=(commandparts[0],commandparts[1:]) # redirecting output to stderr to stdout
	p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	def is_end(p,type):
		msg=type.readline()
		if len(msg)==0 and p.poll() is not None:
				return True
		if len(msg)>0:
				lnwrite("the msg is >>" + msg)
		return False
	## start displaying output immediately ##
	while not is_end(p,p.stdout):
		pass
	"""
def debugnote(_debugnote):
	#####note(_debugnote) # comment out when done
	pass
# let's given all the token types a constant, so we will be able to change them more easily
OPERATOR_TOKENTYPE=11
SIGN_TOKENTYPE=12
INTEGER_TOKENTYPE=13
REAL_TOKENTYPE=14
SINGLEQUOTED_TOKENTYPE=15
DOUBLEQUOTED_TOKENTYPE=16
EXPRESSION_TOKENTYPE=17
# MDH@31AUG2017: all identifiers have a token type with bit 5 set
IDENTIFIER_TOKENTYPE=32
VARIABLE_TOKENTYPE=64
FUNCTION_TOKENTYPE=160
USERFUNCTION_TOKENTYPE=192
###OPENINGPARENTHESIS_TOKENTYPE=18
###CLOSINGPARENTHESIS_TOKENTYPE=19
###COMMENT_TOKENTYPE=20 # MDH@07AUG2017: any expression can end with a comment

## some utility functions
def isIterable(_obj):
	try:
		return not isinstance(_obj,str) and hasattr(_obj,'__iter__')
	except Exception,ex:
		note("ERROR: '"+str(ex)+"' checking on the iterability of "+str(_obj)+".")
	return False
# MDH@13SEP2017: join list elements with a given separator
def join(_sep,_list):
	try:
		result=""
		for listelement in _list:
			if isinstance(listelement,str) and len(listelement)>0:
				result+=_sep+listelement
		return result[1:]
	except:
		pass
	return None
def isIndexable(_obj):
	try:
		return hasattr(_obj,'__getitem__')
	except Exception,ex:
		note("ERROR: '"+str(ex)+"' checking on the indexability of "+str(_obj)+".")
def getText(_obj):
	if _obj is not None:
		###print "To print: "+str(_obj)+"."
		# NOTE a list is a list is a list, even if it has a single element!!!!
		if isinstance(_obj,list): # get rid of the blanks behind the comma's
			"""
			if len(_obj)==1:
				return getText(_obj[0])
			"""
			return "("+",".join(map(getText,_obj))+")"
		if isinstance(_obj,str):
			return _obj
		return str(_obj)
	return ""
def group(_by,_list):
	if isinstance(_by,int) and isIterable(_list):
		if _by>0:
			result=[]
			l=[]
			if len(list)>0:
				for el in _list:
					if len(l)==_by:
						result.append(l)
						l=[]
					l.append(el)
				if len(l)>0:
					result.append(l)
			return result
	return None
# helper classes Function, Identifier and Token
class Identifier:
	def setValue(self,_value=None):
		if self.name is None:
			raise Exception("Cannot change the value of a constant.")
		self.value=_value
		####note("Value of identifier '"+self.name+"' set to '"+str(self.value)+"'.")
		return self
	def __init__(self,_name=None,_value=None):
		self.name=_name
		self.value=_value
	def getName(self):
		return self.name
	def getValue(self):
		####note("Returning value ("+str(self.value)+") of "+("?",self.name)[self.name is not None]+".")
		return self.value
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
DEBUG=Identifier('debug',1) # MDH@22SEP2017: let's make debug accessible to the expressions
def getDebug():
	return DEBUG.getValue()
# MDH@19SEP2017: _executable signifies whether or not the expressions should be immediately executable
# MDH@22SEP2017: by allowing to pass in an expression it's possible to continue that expression with the given expression text!!!!
def getNewExpression(_environment,_immediatelyexecutable,_debug=None,_output=False):
	return Expression(_environment,None,(DEBUG,_debug)[isinstance(_debug,int)],_output).setImmediatelyExecutable(_immediatelyexecutable) # do not show any debug information while constructing the expression from the expression text!!!
def continueExpression(_expression,_expressiontext): # continues the given expression with the given expression text
	error=None
	if isinstance(_expressiontext,str): # text required
		expression=_expression # start out with the given expression
		# MDH@62ND_BIRTHDAY: QUICK FIX we have to skip any character auto-inserted on parsing the expression!!
		autoinserted=None
		for ch in _expressiontext:
			# MDH@21SEP2017: a quick hack to skip the situation where the expression inserted additional characters like the = behind a !
			#								 it's better if the expression exposes what it inserted automatically...
			if autoinserted is not None and ch==autoinserted:
				continue
			if expression is None:
				break
			new_expression=expression.add(ch) # MDH@12SEP2017: passing _output is essential BUT TODO have to find out why!!!!
			error=expression.getError()
			if error is not None:
				lnwrite("\t'"+error+"' evaluating '"+_expressiontext+"'.")
				break
			autoinserted=expression.getAutoInserted() # remember any character auto-inserted
			expression=new_expression # which hopefully is not None!!!!
	else:
		expression=None
	return (expression,error)
# MDH@22SEP2017: any single-line text expression can be obtained calling getExpression()
def getExpression(_expressiontext,_environment,_debug=None):
	return continueExpression(getNewExpression(_environment,True,_debug),_expressiontext)
def getExpressionValue(_expressiontext,_environment,_debug=None):
	# 1. parse the expression from the given expression text
	(expression,expressionerror)=getExpression(_expressiontext,_environment,_debug)
	# 2. check for invalid expression text (expression would be None) and completeness (which it should be)
	if expression is None:
		expressionerror="Failed to parse '"+str(_expressiontext)+"'."
	elif expressionerror is None: # no error so far
		expressionerror=expression.ends()
	# if an error occurred somehow, raise an exception, alternatively we could return None to indicate no result (and therefore some error)
	if expressionerror is not None:
		raise Exception(expressionerror)
	return expression.evaluatesTo(_environment)
def concatenate(_texts,_enquoted=True):
	if not isIterable(_texts):
		return dequote(_texts)[0]
	result=""
	quotechar=None
	#######note("Concatenating '"+str(_texts)+"'.")
	for text in _texts:
		######note("To show: '"+text+"'.")
		(dqtext,dqchar)=dequote(text)
		if quotechar is None and dqchar is not None:
			quotechar=dqchar
		result+=dqtext
	if not _enquoted:
		return result
	return enquote(result,(quotechar,ts[0])[quotechar is None])
def valueof(_valuetext):
	if isinstance(_valuetext,str) and len(_valuetext)>0:
		if _valuetext[0] in ts:
			return _valuetext # as is (i.e. text)
		# either a integer or a float
		try:
			return int(_valuetext)
		except:
			try:
				return long(_valuetext)
			except:
				try:
					return float(_valuetext)
				except:
					pass
	return None
class ReturnException(BaseException):
	def __init__(self,args):
		BaseException.__init__(self,None)
		######note("Return exception arguments: "+str(args)+".")
		self.value=args[0]
	def getValue(self):
		return self.value
	def __str__(self):
		return str(self.value)
class JumpException(ReturnException):
	def __init__(self,args):
		ReturnException.__init__(self,args)
# MDH@05SEP2017: excluding the execution of for, while, if and eval function because
#								 they need to know there execution environment
class Function:
	def __init__(self,_functionindex):
		self.functionindex=_functionindex
		self.debug=DEBUG # the default to use the global debug mode...
	def getIndex(self):
		return self.functionindex
	def getName(self):
		return "funct#"+str(self.functionindex)
	def __str__(self):
		return self.getName()
	def setDebug(self,_debug):
		self.debug=_debug
		return self
	def apply(self,_args): # the function to be applied to the arguments presented as a list
		#######note("Function #"+str(self.functionindex)+" to be applied to "+str(_args)+".")
		if isIterable(_args): # should be a list
			arguments=map(getValue,_args) # get all arguments evaluated
			if self.functionindex<0: # a list function
				if isIterable(arguments): # as it should be
					########note("Applying list function #"+str(self.functionindex)+" to "+str(arguments)+".")
					if self.functionindex==-1: # list
						return list(arguments) # wrap the list of arguments in a List, to prevent it from being recognized as a single-item list that might be devaluated!
					if self.functionindex==-2: # sum
						i=len(arguments)-1
						if i>=0:
							try:
								sum=arguments[i]
								while i>0:
									i=i-1
									sum+=arguments[i]
								return sum
							except Exception,ex:
								pass
						return undefined.getValue()
					if self.functionindex==-3: # product
						i=len(arguments)-1
						if i>=0:
							try:
								product=arguments[i]
								while i>0:
									i=i-1
									product*=arguments[i]
								return product
							except Exception,ex:
								pass
						return undefined.getValue()
					if self.functionindex==-4: # length
						# length is a single-argument function that works on lists, so every argument needs to be a list, otherwise we return -1 as the length!!!
						i=len(arguments)
						note("Determining the length of "+str(arguments)+".")
						# MDH@20SEP2017: if a single argument string, we return the length of that string (dequoted)
						if i==1:
							if isinstance(arguments[0],str):
								return len(dequote(arguments[0])[0])
							if not isinstance(arguments[0],list):
								return -1
							arguments=arguments[0] # a single list
							i=len(arguments)
						while i>0 and arguments[i-1]==undefined.getValue():
							i-=1
						return i
					if self.functionindex==-5: # size
						i=len(arguments)
						if i==1:
							if isinstance(arguments[0],str):
								return len(dequote(arguments[0])[0])
							if isinstance(arguments[0],list):
								return len(arguments[0])
							return -1
						return i
					if self.functionindex==-6: # sorti
						# it's possible to have a single argument that is a list
						if len(arguments)==1 and isIterable(arguments[0]): # quick fix
							arguments=arguments[0]
						return [i[0]+1 for i in sorted(enumerate(arguments), key=lambda x:x[1])] # do NOT forget to add 1 to the index (zero-based in Python, one-based in M)
					if self.functionindex==-7: # concat
						# it's possible to have a single argument that is a list
						if len(arguments)==1 and isIterable(arguments[0]): # quick fix
							return concatenate(arguments[0])
						return concatenate(arguments)
					if self.functionindex==-10: # isalist
						#####note("Is '"+str(arguments)+"' a list?")
						return (0,1)[isinstance(arguments,list)]
					if self.functionindex==-8: # out (turned into a list function more convenient)
						# it's possible to have a single argument that is a list
						if len(arguments)==1 and isIterable(arguments[0]): # quick fix
							arguments=arguments[0]
						write(concatenate(arguments,False)) # do not enquote, and the result of out remains undefined!!!
					elif self.functionindex==-9: # outc i.e. colored output
						# the first argument should be the foreground and background color value, the remainder the elements to show
						if len(arguments)>1 and isinstance(arguments[0],list) and len(arguments[0])>1:
							write(concatenate(arguments[1:],False),arguments[0][0],arguments[0][1])
			else: # a fixed-argument function
				# application of a scalar function to a list, means applying the function to each element of the list (and return the list of it)
				if self.functionindex<100: # a scalar function
					if len(arguments)==1:
						value=arguments[0] # the single scalar argument to apply the function to
						# some of these 1-argument functions work on list arguments
						if self.functionindex==29: # MDH@22SEP2017: len function
							if isinstance(value,str):
								return len(dequote(value)[0])
							if isinstance(value,list):
								i=len(value)
								while i>0 and value[-1]==undefined.getValue():
									i-=1
								return i
							return -1
						elif self.functionindex==30: # MDH@22SEP2017: size function
							if isinstance(value,list):
								return len(value)
							return -1 # not a list
						# if the single argument is still list-like, we again have to use map on it!!!!
						if isIterable(value):
							return [self.apply([x]) for x in value] # map(self.apply,map(listify,arguments[0])) didn't work
						if self.functionindex==7:
							return ~value
						elif self.functionindex==8: # NOT unary operator (which is !)
							return (0,1)[value==0]
						elif self.functionindex==9: # = which means evaluate the expression behind it, which we already did!!!
							return value
						elif self.functionindex==10: # minus unary operator
							return -value
						elif self.functionindex==11:
							return value
						elif self.functionindex==12:
							######debugnote("Returning the square root!")
							return math.sqrt(value)
						elif self.functionindex==13:
							return abs(value)
						elif self.functionindex==14:
							return math.cos(value)
						elif self.functionindex==15:
							return math.sin(value)
						elif self.functionindex==16:
							return math.tan(value)
						elif self.functionindex==17:
							return 1/math.tan(value)
						elif self.functionindex==18:
							return random.uniform(0,value)
						elif self.functionindex==19:
							return math.log(value)
						elif self.functionindex==20:
							return math.log10(value)
						elif self.functionindex==21: # eval
							# __value is supposed to be a string which is a bit of an issue if it isn't
							# nevertheless we should treat __value as an expression that we need to evaluate
							expressiontext=dequote(value)[0]
							####note("To evaluate: '"+expressiontext+"'.")
							return getExpressionValue(expressiontext,_environment) # don't show debug information
						elif self.functionindex==22: # error
							raise Exception(value) # generate an error
						elif self.functionindex==24: # chr
							return chr(value)
						elif self.functionindex==25: # ord
							expressiontext=dequote(value)[0]
							return [ord(ch) for ch in expressiontext]
						elif self.functionindex==26: # readlines
							textfile=open(dequote(value)[0],'r')
							if textfile:
								textlines=list()
								textline=textfile.readline()
								while len(textline)>0:
									try:
										textlines.append(enquote(textline.rstrip('\r\n')))
									finally:
										textline=textfile.readline()
								textfile.close()
								return textlines
						elif self.functionindex==27: # sh
							return executecommand(dequote(value)[0])
						elif self.functionindex==28: # readvalues
							textfile=open(dequote(value)[0],'r')
							if textfile:
								valuelines=list()
								textline=textfile.readline()
								while len(textline)>0:
									try:
										linetext=textline.rstrip(opsys.linesep) # TODO can we do this if opsys.linesep is more than one character?
										# because the values can be enclosed in quotes, we need to parse the values
										# treating tabs and commas as value separators (not blanks)
										linevalues=list()
										valuetext='' # the composed value text!!!
										intextvalue=False
										behindvalue=False # ignore everything until the first non-whitespace character
										quotechar=''
										linevalues=list()
										for ltch in linetext:
											if intextvalue: # in a (quoted) text value
												if ltch==quotechar: # the same character ends the text literal
													intextvalue=False
												valuetext+=ltch
											elif ltch in w: # all whitespace not inside text is to be ignored
												if len(valuetext)>0: # in some value, that the whitespace ends
													behindvalue=True # ends any value entered
											elif ltch=='\t' or ltch==',': # a tab or comma not inside the value
												linevalues.append(valueof(valuetext))
												# prepare for new value
												valuetext=''
												quotechar='' # no text literal
												behindvalue=False
												intextvalue=False
											elif not behindvalue: # any non-whitespace character not behind the value is part of the value
												if len(valuetext)==0 and ltch in ts: # starts a text literal
													quotechar=ltch
													intextvalue=True
												# any character is part of the value text
												valuetext+=ltch
										# if unclosed text literal end it anyway
										if intextvalue and not behindvalue:
											valuetext+=quotechar
										linevalues.append(valueof(valuetext))
										valuelines.append(linevalues) # append to the result
									finally:
										textline=textfile.readline()
								textfile.close()
								return valuelines
						elif self.functionindex==31: # defined
							return (1,0)[value==undefined.getValue()]
						elif self.functionindex==32: # undefined
							return (0,1)[value==undefined.getValue()]
						elif self.functionindex==45: # MDH@21SEP2017: sign function
							return ((-1,1)[value>0],0)[value==0]
						elif self.functionindex==46: # MDH@18SEP2017: int function
							try:
								return int(dequote(value)[0])
							except:
								try:
									return long(dequote(value)[0])
								except:
									pass
						elif self.functionindex==47: # MDH@18SEP2017: jump only allowed in a function
							raise JumpException(value)
						elif self.functionindex==48: # MDH@18SEP2017: get input from the user
							intext=raw_input(dequote(value)[0])
							return enquote(intext)
						elif self.functionindex==49: # inch
							# how about letting the argument represent the characters getch() should return??????
							possiblechars=dequote(value)[0]
							if len(possiblechars)>0:
								while 1:
									ch=getch()
									if ord(ch) in (3,4,9,10,13): # break anyway on Ctrl-C, Ctrl-D, Enter or Tab
										return undefined.getValue()
									if possiblechars.find(ch)>=0:
										output(ch) # echo the character input
										return enquote(ch)
					elif len(arguments)>1: # shouldn't happen though
						return [self.apply([x]) for x in arguments] # we have to listify the arguments because self.apply expects an argument list (even a single one)
				elif self.functionindex<200: # the two-argument functions
					if self.functionindex==105: # MDH@21SEP2017: find text in string
						if len(arguments)>1 and isinstance(arguments[0],str) and isinstance(arguments[1],str):
							findtext=dequote(arguments[0])[0]
							searchtext=dequote(arguments[1])[0]
							return 1+searchtext.find(findtext)
					elif self.functionindex==104: # MDH@19SEP2017: get integer from user
						if len(arguments)>1 and isinstance(arguments[1],(int,long)):
							prompttext=dequote(arguments[0])[0]
							while 1:
								try:
									inttext=raw_input(prompttext).strip() # removing whitespace
									########note("IN: '"+inttext+"'")
									if len(inttext)==0: # no input, so return the default!!!!
										break
									return int(inttext)
								except:
									writeln("Integer (or no) input required. Please try again!")
							return arguments[1] # the default
					elif self.functionindex==103: # MDH@18SEP2017: replicate
						# the second argument should be a positive integer telling us how many times to replace the first argument
						if len(arguments)>1 and isinstance(arguments[1],(int,long)):
							replicatecount=arguments[1]
							replicates=list()
							while replicatecount>0:
								if isinstance(arguments[0],list):
									replicates.append(list(arguments[0])) # wrap the list so we use a copy
								else:
									replicates.append(arguments[0])
								replicatecount-=1
							return replicates
					elif self.functionindex==101 or self.functionindex==102: # ls/dir
						if len(arguments)>0:
							directory=dequote(arguments[0])[0] # the name of the directory requested
						else:
							directory=''
						if not isinstance(directory,str) or len(directory)==0:
							directory='.'
						# directory specified
						filter=''
						if len(arguments)>1:
							filter=dequote(arguments[1])[0]
						else:
							filter=''
						if len(filter)==0:
							filter=("*","*.*")[self.functionindex==102] # Unix or Windows style
						import glob
						return map(enquote,glob.glob(opsyspath.join(directory,filter)))
					elif self.functionindex==199: # join
						if len(arguments)==2:
							if isIterable(arguments[0]) and isinstance(arguments[1],(int,long)) and arguments[1]>0:
								listl=arguments[1]
								########note("Will join "+str(listl)+" successive elements of the input list.")
								if listl<len(arguments[0]):
									inputlist=arguments[0]
									outputlist=list()
									outputelement=list()
									while len(inputlist)>0:
										outputelement.append(inputlist.pop(0))
										if len(outputelement)>=listl:
											outputlist.append(outputelement)
											outputelement=list()
									if len(outputelement)>0:
										while len(outputelement)<listl:
											outputelement.append(undefined.getValue())
										outputlist.append(outputelement)
									return outputlist
								note("ERROR: Invalid second input argument ("+str(arguments[1])+") to the join() function!")
								return arguments[0] # no change to the list
							note("ERROR: The arguments supplied to the join() function are not a list and a positive integer!")
				elif self.functionindex<300: # the three-argument functions
					if self.functionindex==211: # function
						if len(arguments)==3:
							if isinstance(arguments[0],str) and isIterable(arguments[1]) and isIterable(arguments[2]):
								# first argument name, second argument parameters, third argument contents of function
								userfunctionname=dequote(arguments[0])[0]
								# second and third arguments should be lists with text elements
								functionparameterdefaults=list()
								if isIterable(arguments[1]):
									functionresultidentifiername=None
									for functionparameter in arguments[1]:
										functionparametertext=dequote(functionparameter)[0]
										functionparameterparts=functionparametertext.strip().split('=') # get rid of any whitespace before or after
										if len(functionparameterparts[0].rstrip())==0: # no parameter name specified
											continue
										if functionparameterparts[0]=='$':
											if len(functionparameterparts)>1 and len(functionparameterparts[1])>0:
												functionresultidentifiername=functionparameterparts[1]
										else:
											if len(functionparameterparts)>1:
												functionparameterdefaults.append(tuple(functionparameterparts))
											else:
												functionparameterdefaults.append((functionparameterparts[0],None))
								# create user function within the current (global) environment (i.e. not a standalone function)
								userfunction=UserFunction(userfunctionname,environment,functionresultidentifiername,functionparameterdefaults,environment)
								functiondefinitionenvironment=userfunction.getDefinitionEnvironment() # read the expressions in the definition environment (exposing parameters)
								# now we need to populate the user function with the (tokenized) expressions but we need to register the function with the environment immediately
								if isIterable(arguments[2]):
									for expressionliteral in arguments[2]:
										expressiontext=dequote(expressionliteral)[0]
										if len(expressiontext.strip())==0:
											continue
										(expression,error)=getExpression(expressiontext.strip(),functiondefinitionenvironment,False,0) # not immediately executable
										if expression is None or error is not None:
											continue
										functiondefinitionenvironment.addExpression(expression) # these will be the expressions used by the user function when being called
								return environment.addFunction(userfunction) # ESSENTIAL obviously...
							else:
								note("The arguments supplied to the function() function are not a text, a list with parameters, and a body list with expressions.")
						else:
							note("Exactly 3 arguments required by the function() function: "+str(len(arguments))+" provided.")
		# if we get here the function result is undefined
		return undefined
	def getValue(self,_arglist):
		""" it's easier if we let apply consume the argument list by popping arguments (already being done, see below)
		functionvaluelist=list()
		while len(_arglist)>0:
			self.apply(_arglist)
		if len(functionvaluelist)==1:
			return functionvaluelist[0]
		return functionvaluelist
		"""
		##########note("Applying function #"+str(self.functionindex)+" to '"+str(_arglist)+"'.")
		# every function has a fixed number of arguments it requires (except for the list functions which consume the argument list as a whole)
		# for single-argument functions we can use Python's map() to take care of generating the results
		# for all others we apply the function to as many arguments it needs until all arguments are consumed
		if self.functionindex==47: # the jump function
			raise JumpException(_arglist)
		if self.functionindex==0: # the return function
			raise ReturnException(_arglist)
		if self.functionindex==-1:
			return List(_arglist)
		if self.functionindex<-1: # assumed list function TODO can we somehow process these as any other 'normal' function??????
			return self.apply(_arglist) # but we want to apply the list function to each of the arguments
		argcount=1+(self.functionindex/100) # the number of arguments the function requires
		# the function needs to be applied at least once
		functionvaluelist=list() # the list containing the successive results of the function application
		# construct the first argument list
		functionarglist=list()
		while len(_arglist)>0 and len(functionarglist)<argcount: # as long as there's arguments to pop, and we do not have enough arguments yet
			functionarglist.append(_arglist.pop(0))
		functionvalue=self.apply(functionarglist)
		########note("Result of applying function "+str(self)+" to "+str(functionarglist)+": '"+str(functionvalue)+"'.")
		functionvaluelist.append(functionvalue) # the result of the first application of the function
		while len(_arglist)>0: # additional function calls to make
			functionarglist=list()
			while len(_arglist)>0 and len(functionarglist)<argcount: # as long as there's arguments to pop, and we do not have enough arguments yet
				functionarglist.append(_arglist.pop(0))
			functionvalue=self.apply(functionarglist)
			##note("Result of applying function "+str(self)+" to "+str(functionarglist)+": '"+str(functionvalue)+"'.")
			functionvaluelist.append(functionvalue)
		return functionvaluelist # the list of results
# MDH@02SEP2017: have to think about how to implement the user functions though
# the user functions defined should be kept in the current Environment which makes sense
# as we can have subfunctions
import os as opsys # os is already used as variable name, so we have to change the name
import os.path as opsyspath
# MDH@13SEP2017: the definition environment hosts the inner functions and expressions
#								 therefore there's no need to
class UserFunction(Function):
	def setupEnvironment(self,_environment):
		# define the result identifier
		if len(self.resultidentifiername)>0:
			_environment.addIdentifier(Identifier(self.resultidentifiername))
		# setup the parameter identifiers
		for (parametername,parameterdefault) in self.parameterdefaults:
			_environment.addIdentifier(Identifier(parametername).setValue(parameterdefault))
	# MDH@07SEP2017: as Environment subclasses UserFunction re-arranged the parameters so that it's easy to call the super constructor in Environment
	def __init__(self,_name,_hostenvironment,_standalone,_parameterdefaults=None,_resultidentifiername=None):
		Function.__init__(self,-1) # back to using 0 as function index
		self.name=_name
		self.hostenvironment=_hostenvironment
		### now stored in the value of self.M!!! self.expressions=list()
		if isinstance(_resultidentifiername,str) and len(_resultidentifiername)>0:
			self.resultidentifiername=_resultidentifiername
		else: # let's use $ as default
			self.resultidentifiername="$"
		self.parameterdefaults=_parameterdefaults # this should be a dictionary of parameter names and default values
		self.standalone=_standalone
		self.hostexecutionenvironment=(self.hostenvironment,Menvironment)[self.standalone]
		######note("Function="+self.name+" host environment="+self.hostenvironment.getName()+" host execution environment="+self.hostexecutionenvironment.getName())
		self.expressionfile=None
		# MDH@13SEP2017: this is the only situation where the environment naming might differ from the environment structure...
		self.definitionenvironment=Environment(self.name,self.hostexecutionenvironment,self.hostenvironment)
		self.definitionenvironment.addFunction(self) # to allow recursive calls
		self.setupEnvironment(self.definitionenvironment) # the definition environment needs the parameter and result variables
	def getDefinitionEnvironment(self):
		return self.definitionenvironment
	def setExpressionFile(self,_expressionfile):
		self.expressionfile=_expressionfile
	def writeDefinition(self,_definitionfilename):
		functionline=self.name
		if self.standalone:
			functionline+='*' # marks this user functions as being standalone!!!
		if self.resultidentifiername!='$':
			functionline+="\t$="+self.resultidentifiername
		if isinstance(self.parameterdefaults,list):
			for (parametername,parameterdefault) in self.parameterdefaults:
				functionline+="\t"+parametername
				if parameterdefault is not None:
					parameterdefaulttext=str(parameterdefault)
					if len(parameterdefaulttext)>0:
						functionline+="="+parameterdefaulttext
		functionline+=opsys.linesep
		result=False
		try:
			functionf=open(_definitionfilename,'a')
			functionf.write(functionline) # ready for the next function!!!
			functionf.close()
			result=True
		except:
			pass
		return result
	def getHostEnvironment(self): # the environment to return to when done begin defined
		return self.hostenvironment
	# MDH@07SEP2017: the user function is the base storage bag of associated expressions
	def setExpressions(self,_expressions):
		if isIterable(_expressions):
			self.expressions=_expressions
			note("Number of expressions in function "+self.name+": "+str(len(self.expressions))+".")
		else:
			self.expressions=None
	# exposes a method to return a (sub)environment to use in entering function body expressions
	def getExecutionEnvironment(self,_arglist=None):
		# create a subenvironment below the definition environment, which contains the expressions and inner functions
		result=Environment(self.name,self.definitionenvironment) # when standalone NO access to the root environment
		# add the result identifier name immediately as local variable!!
		if len(self.resultidentifiername)>0:
			result.addIdentifier(Identifier(self.resultidentifiername))
		# use arguments when available and the defaults otherwise
		for (parameterindex,(parametername,parameterdefault)) in enumerate(self.parameterdefaults):
			if isIterable(_arglist) and parameterindex<len(_arglist) and _arglist[parameterindex] is not None:
				argumentvalue=getValue(_arglist[parameterindex])
				####note("Value of argument #"+str(parameterindex)+": "+str(argumentvalue)+".")
				result.addIdentifier(Identifier(parametername).setValue(argumentvalue))
			else:
				###note("Using default "+str(parameterdefault)+" of parameter "+parametername+".")
				# MDH@20SEP2017: essential to evaluate the default AS expression, otherwise it would be stored as string
				#								 and fuck up stuff (like using it in certain binary operations like .. that expect numbers)
				#								 as you can see this JIT evaluation of the parameter default is BEST
				parameterdefaultvalue=getExpressionValue(parameterdefault,self.definitionenvironment)
				result.addIdentifier(Identifier(parametername).setValue(parameterdefaultvalue))
		return result
	def getName(self):
		return self.name
	# a user function executes its expressions (but note that an Environment's getValue() returns one of the expressions
	def getValue(self,_arglist): # already knows it's environment (the one it was created in plus the argument list)
		# execute the expressions present in the definition environment
		result=None
		expressions=self.definitionenvironment.getExpressions()
		if expressions is not None:
			l=len(expressions)
			if l>0:
				######note("Number of expressions to evaluate "+str(l)+"...")
				executionenvironment=self.getExecutionEnvironment(_arglist)
				expressionindex=0
				while expressionindex<len(expressions):
					# MDH@19SEP2017: TODO do we need to change immediately executable to True here anyway?????
					#											as I think evaluatesTo does not use it!!!!
					expression=expressions[expressionindex]
					if expression is not None and not expression.isEmpty(): # MDH@19SEP2017: skip 'comment' lines
						try:
							#####note("Evaluating '"+expression.getText()+"'...")
							expressionvalue=expression.evaluatesTo(executionenvironment) # evaluate the expression in the execution environment
							#####note("Value of "+str(expression)+": "+str(expressionvalue)+".")
						except JumpException,jumpException:
							deltaexpressionindex=jumpException.getValue()
							if isinstance(deltaexpressionindex,(int,long)):
								expressionindex+=deltaexpressionindex
								if expressionindex<0:
									break
								continue
							note("Invalid jump result: '"+str(deltaexpressionindex)+"'.")
						except ReturnException,returnException:
							result=returnException.getValue()
							#######note("Return result of function: "+str(result)+".")
							break
					expressionindex+=1 # normal continuation i.e. next expression to execute next
				# what have we got in this execution environment???
				if result is None: # no explicitly returned value using the return function
					if len(self.resultidentifiername)>0: # there's a regular result variable
						result=executionenvironment.getIdentifierValue(self.resultidentifiername)
				if isIterable(result) and len(result)==1:
					result=result[0]
		else:
			note("ERROR: No expressions to evaluate!")
		return (undefined,result)[result is not None]
# keep track of the identifier (that have a value)
undefined=Identifier(_value='?') # the identifier with None value is used to indicate an undefined value and is to be returned as value when non-computable/computed
# MDH@30AUG2017: an 'environment is basically a dictionary of identifiers
# MDH@02SEP2017: we're gonna let Environment keep a list of user functions being created
#								 as it otherwise would need to keep a list of pending function creations
#								 I've changed this to have Environment
# MDH@06SEP2017: problem is that an Environment is not something on which getValue() can be called
#								 unless you want to be able to execute the Environment as a function????
#								 as such an environment could be considered a parameter-less function
class EnvironmentIdentifier(Identifier):
	def __init__(self,_environment):
		Identifier.__init__(self) # not giving the identifier a name (so it is treated as a constant)
		self.environment=_environment
class FunctionsIdentifier(EnvironmentIdentifier):
	def getValue(self):
		return map(enquote,self.environment.getFunctionNames())
class VariablesIdentifier(EnvironmentIdentifier):
	def getValue(self):
		return map(enquote,self.environment.getIdentifierNames())
class Environment:
	# MDH@15SEP2017: dynamic identifiers, to expose the list of available functions and variables
	def getNumberOfExpressions(self):
		return len(self.M.getValue())
	def getExpression(self,_index):
		#######note("Expression #"+str(_index)+" requested...")
		expressions=self.M.getValue()
		if expressions is not None and _index>=0 and _index<len(expressions):
			return expressions[_index]
		return None
	def addExpression(self,_expression):
		self.M.getValue().append(_expression)
		if self.expressionfile:
			# write the value first, then the expression (if it is)
			# MDH@19SEP2017: str(_expression) replaced by _expression.getText() to force showing any comment as well
			if isinstance(_expression,Expression):
				self.expressionfile.write(str(_expression.getValue())+"\t"+_expression.getText()+opsys.linesep)
			else: # we cannot write more than the value
				self.expressionfile.write(str(_expression)+opsys.linesep)
			self.expressionfile.flush()
			opsys.fsync(self.expressionfile) # hmmm, clumsy
	def addUser(self,_user):
		if not _user in self.users:
			self.users.append(_user)
			if self.usersfile:# for appending a new user
				self.usersfile.write(_user+opsys.linesep)
				self.usersfile.flush()
				opsys.fsync(self.usersfile)
		return _user in self.users
	def getUsers(self):
		return self.users
	def setUsersFile(self,_usersfile):
		self.usersfile=_usersfile
	def setup(self): # to be called on a new function
		self.expressionfile=open(self.getExpressionsFilename(),'a') # TODO append or write or what
	def loadExpressions(self,_evaluate=False): # MDH@19SEP2017: replacing readExpressions()
		self.M.value=list() # initialize the list of expressions (this is a bit of cheating as we cannot use setValue() on a constant like M)
		expressionsfilename=self.getExpressionsFilename()
		if opsyspath.exists(expressionsfilename):
			#######note("Reading expressions from "+expressionsfilename+".")
			expressionsfile=open(expressionsfilename,'r')
			if expressionsfile:
				expression=None # the current expression
				expressionline=expressionsfile.readline()
				expressionlineindex=0
				while len(expressionline)>0:
					try:
						expressionlineindex+=1
						expressiontext=expressionline.rstrip('\r\n')
						# there's either a value or a value and an expression on the line
						if len(expressiontext)>0: # not an expression declaration (probably the value of the expression)
							tabpos=expressiontext.find('\t')
							if tabpos>=0: # expression available
								expressiontext=expressiontext[tabpos+1:]
							#######note("\tParsing '"+expressiontext+"'...")
							# MDH@10SEP2017: essential to pass 0 for the debug value!!!
							# MDH@22SEP2017: we're going to allow expression continuation on the next line
							if expression is None: # not an expression continuation
								expression=getNewExpression(self,_evaluate,0)
							elif tabpos!=0: # how about letting every continuation (preferably) start with a tab????
								note("WARNING: Not indented expression continuation '"+expressiontext+"' encountered on line #"+str(expressionlineindex)+" of "+expressionsfilename+".")
							# 'continue' the expression with the expression text
							(new_expression,error)=continueExpression(expression,expressiontext)
							if expression.isEmpty(): # the expression is empty
								self.addExpression(None)
								expression=None # can't be continued on the next line!!
							elif error is None: # no error
								if expression.ends() is None: # a completed expression, ready to add
									try:
										self.addExpression(expression)
										if _evaluate:
											try:
												expression.evaluatesTo(self) # return statements throw the return exception, which we want to catch
											except ReturnException,returnException:
												expression.setValue(returnException.getValue()) # TODO an IdentifierElementExpression also has a setValue but that one requires an environment as well
										else: # MDH@20SEP2017: ok, if this expression initializes identifier not yet existing in this environment, we're going to declare them!!!
											expressioninitializes=expression.initializes(self)
											if len(expressioninitializes)>0:
												#######note("Initialized in '"+expressiontext+"': "+getText(expressioninitializes)+".")
												for expressioninitialize in expressioninitializes:
													self.addIdentifier(Identifier(expressioninitialize))
									finally:
										expression=None # ready to start a new expression
								else: # expression, not yet complete, we'll end up with the original expression in the end (hopefully)
									note("WARNING: Expression '"+expressiontext+"' does not end on line #"+str(expressionlineindex)+" of "+expressionsfilename+".")
									expression=new_expression # continue with the (sub)expression
							else: # some error, add None
								note("ERROR: '"+error+"' in processing expression text '"+expressiontext+"' on line #"+str(expressionlineindex)+" of "+expressionsfilename+".")
								self.addExpression(None)
					finally:
						expressionline=expressionsfile.readline() # read the next line
				expressionsfile.close()
			else:
				note("ERROR: Failed to open expressions file '"+expressionsfilename+"'.")
		else:
			note("NOTE: Expressions file '"+expressionsfilename+"' does not exist!")
		return self.M.getValue() # returning the list of loaded expressions
	def getExpressions(self):
		# MDH@19SEP2017: let's do just-in-time (JIT) loading of the expressions
		expressions=self.M.getValue()
		if expressions is not None:
			return expressions
		# expressions not yet loaded
		return self.loadExpressions()
	# MDH@13SEP2017: naming uses the host (which may differ from the parent for standalone functions)
	def getHostName(self):
		host=self.getHost()
		if host is not None:
			return host.getName()
		return ''
	def getName(self):
		# MDH@12SEP2017: the name comes first
		return join('.',(self.name,self.getHostName()))
	def getFilename(self): # reverses the parent and own name
		# MDH@22SEP2017: let's only use lowercase in filenames (except for the leading M of course), thus allowing functions to use uppercase characters in the name
		return join('.',(self.getHostName().lower(),self.name.lower()))
	def getFunctionFilename(self,_functionname):
		return join('.',("M",self.getFilename(),_functionname,'txt'))
	def getExpressionsFilename(self):
		return join('.',("M",self.getFilename(),'txt'))
	def getFunctionsFilename(self):
		return join('.',("M",self.getFilename(),'functions'))
	def getUsersFilename(self):
		return join('.',("M",self.getFilename(),'users'))
	def getPrompt(self):
		return join(".",(self.getName(),"M"))+"("+str(len(self.M.getValue())+1)+")"+modechars[self.mode]+" "
	def getParent(self):
		return self.parent
	def getHost(self):
		if self.host is not None:
			return self.host
		return self.parent
	def __init__(self,_name="",_parent=None,_host=None):
		###########UserFunction.__init__(self,_name,_parent)
		self.expressionfile=None
		self.usersfile=None
		self.users=list() # initialize no users defined in this environment
		self.name=_name
		self.host=_host
		self.parent=_parent
		if isinstance(self.parent,Environment):
			self.mode=self.parent.getMode()
		else:
			self.mode=0
		#######self.externalidentifiernames=list() # the list of external variables used by this environment that cannot be created locally
		self.startedUserFunctions=list() # MDH@06SEP2017: list of started user functions
		self.identifiers=dict()
		self.functions=dict()
		# MDH@19SEP2017: how about not initializing self.M to a list so that it can read the expressions from the expressions filename at the moment the expressions are requested???
		#								 as a sort of JIT reading of the expressions (in particular applicable for reading user function expressions)
		self.M=Identifier() ########_value=list()) # host the expressions in an nameless identifier (to make it unassignable)
		self.addIdentifier(self.M,"M") # M identifier has no name of it's own (to prevent editing), self.M is passed by 'reference'
		# MDH@15SEP2017: adding the functions and variables (dynamic) value identifiers
		self.addIdentifier(FunctionsIdentifier(self),"functions")
		self.addIdentifier(VariablesIdentifier(self),"variables")
		""" MDH@08SEP2017: returned to defining M as identifier and NOT as function
		# we ascertain to have a function with the same name BUT then we can't call the function recursively buggers
		self.addFunction("M",self) # MDH@07SEP2017: with Environment now also a UserFunction we can register itself as a function for access to the expressions
		"""
	def startUserFunction(self,_userFunction):
		self.startedUserFunctions.append(_userFunction)
	def endUserFunction(self):
		if len(self.startedUserFunctions)==0:
			return None
		userfunction=self.startedUserFunctions.pop()
		###### MDH@13SEP2017: no need for this anymore... userfunction.setExpressions(self.M) # whatever expressions we collected, pass them into userfunction immediately
		return userfunction
	def getNumberOfStartedUserFunctions(self):
		return len(self.startedUserFunctions)
	def getMode(self):
		return self.mode
	# Environment posing as a function overrides the getValue() to return one of its expressions instead of actually executing them
	# (therefore you cannot use a UserFunction as Environment itself)
	def getValue(self,_arglist):
		result=list()
		for argument in _arglist:
			if isinstance(argument,(int,long)):
				if argument<0:
					result.append(self.M(argument+len(self.M)))
				elif argument>0:
					result.append(self.M(argument-1))
				else:
					result.append(None)
		return result
	def __str__(self):
		return self.getName()
	def __repr__(self):
		return str(self)
	def setMode(self,_mode):
		self.mode=_mode
	def functionExists(self,_functionname):
		###note("Looking for '"+_functionname+"' in functions "+str(self.getFunctionNames())+" of "+self.name+".")
		result=_functionname in self.functions
		if not result:
			if self.parent is not None and self.parent.functionExists(_functionname):
				result=True
			else:
				pass ###note("Does not exist in parent.")
		else:
			pass ####note("Exists in "+self.name+"!")
		return result
	def getIdentifierNames(self,_sort=True):
		identifiernames=self.identifiers.keys()
		if self.parent is not None:
			parentidentifiernames=self.parent.getIdentifierNames()
			for parentidentifiername in parentidentifiernames:
				if not parentidentifiername in identifiernames:
					identifiernames.append(parentidentifiername)
		if _sort:
			return sorted(identifiernames)
		return identifiernames
	def getFunctionNames(self,_sort=True):
		functionnames=self.functions.keys()
		if self.parent is not None:
			parentfunctionnames=self.parent.getFunctionNames()
			for parentfunctionname in parentfunctionnames:
				if not parentfunctionname in functionnames:
					functionnames.append(parentfunctionname)
		if _sort:
			return sorted(functionnames)
		return functionnames
	# MDH@13SEP2017: for implementing the identifier continuation
	def getAllIdentifierNames(self):
		allidentifiernames=list()
		allidentifiernames.extend(self.getFunctionNames(False)) # no need to sort these
		allidentifiernames.extend(self.getIdentifierNames(False)) # no need to sort these
		return allidentifiernames
	def getFunction(self,_functionname):
		if _functionname in self.functions:
			return self.functions[_functionname]
		if self.parent is not None:
			return self.parent.getFunction(_functionname)
		return None # not a function
	def functionsExistStartingWith(self,_functionprefix):
		for functionname in self.functions:
			if functionname.startswith(_functionprefix):
					return True
		if self.parent is None:
			return False
		return self.parent.functionsExistStartingWith(_functionprefix)
	def identifiersExistStartingWith(self,_identifierprefix):
		for identifier in self.identifiers:
			if identifier.startswith(_identifierprefix):
				return True
		# I haven't got them!!!
		if self.parent is None:
			return False
		# parent could have it!!!
		return self.parent.identifiersExistStartingWith(_identifierprefix)
	def identifierExists(self,_identifiername):
		if _identifiername in self.identifiers:
			return True
		if self.parent is not None:
			return self.parent.identifierExists(_identifiername)
		return False # can't find it
	def getExistingLocalIdentifier(self,_identifiername):
		if _identifiername in self.identifiers:
			return self.identifiers[_identifiername]
		return None
	def getIdentifier(self,_identifiername):
		# creates the identifier if it does not exist anywhere
		####note("Looking for identifier '"+_identifiername+"' in environment '"+self.getName()+"'.")
		identifier=self.getExistingIdentifier(_identifiername)
		# create it if not found!!
		if identifier is None: # not defined anywhere
			####note("Identifier '"+_identifiername+" not found!")
			identifier=Identifier(_identifiername)
			self.identifiers[_identifiername]=identifier
		else:
			pass ####note("Current value of identifier '"+_identifiername+"': "+str(identifier.getValue())+".")
		return identifier
	def getExistingIdentifier(self,_identifiername):
		# check whether 'locally' defined first
		if _identifiername in self.identifiers:
			return self.identifiers[_identifiername]
		# go up the chain...
		if self.parent is not None:
			return self.parent.getExistingIdentifier(_identifiername)
		return None # can't find it
	def deleteIdentifier(self,_identifiername): # for now allow only deleting 'local' identifiers
		del self.identifiers[_identifiername]
	def getIdentifierValue(self,_identifiername):
		result=undefined
		identifier=self.getExistingIdentifier(_identifiername) # no sense to look for a non-existing one
		if identifier is not None:
			result=identifier.getValue()
			debugnote("Value of '"+_identifiername+"': '"+(str(result),"?")[result is None]+"'.")
		else:
			debugnote("Identifier '"+_identifiername+"' not found!")
		return result
	def getIdentifierValues(self,_exclude):
		result=dict()
		for identifiername in self.identifiers:
			if _exclude is None or not identifiername in _exclude:
				result[identifiername]=self.identifiers[identifiername].getValue()
		return result
	def addIdentifier(self,_identifier,_name=None):
		identifiername=(_name,_identifier.getName())[_name is None]
		if identifiername is None:
			return None
		self.identifiers[identifiername]=_identifier
		return self
	def addFunction(self,_function,_name=None):
		functionname=(_name,_function.getName())[_name is None]
		if functionname in self.functions:
			return 0
		self.functions[functionname]=_function
		return len(self.functions) # to indicate success!!!
	# MDH@02SEP2017: addFunctionGroup() changed to provide a shortcut for adding M functions
	def addFunctions(self,_functionindexdict):
		for functionname in _functionindexdict:
			self.addFunction(Function(_functionindexdict[functionname]),functionname)
	# MDH@15AUG2017: the way we're pushing the elements of the expression on the stack, we're always popping the second operand first, then the operator, then the first argument
	def getOperationResult(self,argument2,operator,argument1):
		#####note("Computing "+str(argument1)+" "+str(operator)+" "+str(argument2)+"...")
		result=None
		if argument2 is not None and argument1 is not None:
			def getElementValue(_element):
				if isinstance(_element,list):
					if len(_element)==0: # nothing to evaluate...
						return _element
					return map(getElementValue,_element)
				if isinstance(_element,Expression):
					return _element.evaluatesTo(self)
				return getValue(_element)
			# determine whether or not a shortcutter operator, noting that != <= >= and == are not shortcut assignments
			shortcutting=(operator[-1]==assignmentchar and (len(operator)>2 or not operator[0] in '!=<>'))
			if shortcutting:
				#######note("Shortcut operator "+operator+" encountered.")
				if not isinstance(argument1,Identifier) and not isinstance(argument1,IdentifierElementExpression):
					raise Exception("Please report this bug. Shortcut assignment operator cannot be applied to a non-variable.")
				operator=operator[:-1]
			if operator==declarationchar: # the expression assignment operator (which is very special indeed)
				if getDebug()&8:
					note("Declaring "+str(argument2)+" as "+str(argument1)+".")
				if isinstance(argument1,Identifier):
					return argument1.setValue(argument2).getValue()
				if isinstance(argument1,IdentifierElementExpression):
					########note("Evaluating identifier element expression "+str(argument1)+".")
					return argument1.setValue(argument2,self).getValue()
				raise Exception("Expression destination of type "+str(type(argument1))+" of "+str(argument1)+" not an identifier (element)!") # TODO this error should've been identified by the tokenizer
			# MDH@27AUG2017: all other operations require evaluation of the RHS expression!!!
			operand2=getElementValue(argument2) # could be a list containing expressions (which hide themselves!!!)
			#####note("Operand 2: "+str(operand2)+".")
			if getDebug()&8:
				note("Computing "+str(argument1)+" "+str(operator)+" "+str(argument2)+"...")
			# with an assignment the left-hand side will not be a 'list' but the right-hand side can be a list to assign
			# so it's easist to deal with the assignment separately
			if operator==assignmentchar:
				if isinstance(argument1,list) and len(argument1)==1:
					operand1=argument1[0]
				else: # which could be an empty list!!!
					operand1=argument1
				if getDebug()&8:
					note("Assigning "+str(operand2)+" to "+str(operand1)+".")
				if isinstance(operand1,Identifier):
					return operand1.setValue(operand2).getValue()
				if isinstance(argument1,IdentifierElementExpression):
					#######note("Evaluating identifier element expression "+str(operand1)+".")
					return operand1.setValue(operand2,self).getValue()
				raise Exception("Assignment destination of type "+str(type(argument1))+" of "+str(argument1)+" not an identifier (element)!") # TODO this error should've been identified by the tokenizer
			# if assigning do not evaluate the left-hand side
			operand1=getElementValue(argument1)
			#####note("Operand 1: "+str(operand1)+".")
			# both operands need not be None
			if operand1 is not None and operand2 is not None:
				# with the period also defined as list concatenation operand we should simply extend operand1 with (listified) operand2
				if operator==periodchar: # the list concatenation operator
					# MDH@22SEP2017: ah, we have to be careful here because the original list might be empty
					######note("Concatenating lists '"+str(operand1)+"' and '"+str(operand2)+"'.")
					result=list()
					result.extend(listify(operand1))
					result.extend(listify(operand2))
					######note("Result list: '"+str(result)+"'.")
				# ok, both elements should be either lists or scalars, at least to apply the non-assignment binary operators to
				# although we should always obtain two list or two items, we make a list of either if need be
				elif isinstance(operand2,list):
					####note("Operand 2 is a list.")
					if len(operand2)==0:
						return operand1
					if not isinstance(operand1,list):
						return self.getOperationResult(operand2,operator,[operand1])
					# delist if both arguments are one-element lists
					if len(operand1)==1 and len(operand2)==1:
						result=self.getOperationResult(operand2[0],operator,operand1[0])
					else:
						result=list()
						for i in range(0,max(len(operand1),len(operand2))):
							result.append(self.getOperationResult(getItem(operand2,i),operator,getItem(operand1,i)))
				elif isinstance(operand1,list):
					####note("Operand 1 is a list.")
					if len(operand1)==0:
						result=operand2
					else:
						result=self.getOperationResult([operand2],operator,operand1)
				elif operator=="..": # MDH@27AUG2017: replaced : because : is now the operator to defined a block of (unevaluated) expressions
					if isinstance(operand1,(int,long,float)) and isinstance(operand2,(int,long,float)):
						result=[operand1]
						if operand1<operand2:
							while operand1+1<=operand2:
								operand1+=1
								result.append(operand1)
						elif operand1>operand2:
							while operand1-1>=operand2:
								operand1-=1
								result.append(operand1)
						#####note("Range result: "+str(result)+".")
				elif operator=="-":
					result=operand1-operand2
				elif operator=="+":
					# a bit of an issue if we have string concatenation which we should or should not allow
					if isinstance(operand1,(int,long,float)) and isinstance(operand2,(int,long,float)):
						result=operand1+operand2
					else:
						result=textconcatenate(operand1,operand2)
				elif operator=="*":
					if isinstance(operand1,(int,long,float)) and isinstance(operand2,(int,long,float)):
						result=operand1*operand2
					else:
						result=repeat(operand1,operand2)
				elif operator=="%" or operator=="%%": # modulo operators but the latter forces the result to be integer
					if operand2!=0:
						result=operand1%operand2
						# second operator forces the result to be an integer (if not already)
						if len(operator)>1 and isinstance(result,float):
							result=math.trunc(result)
					else:
						raise Exception("Division by zero in an attempt to apply the modulo operator (%).")
				elif operator=="\\" or operator=="//": # two styles of requesting integer division
					if operand2!=0:
						# integer division is something that returns an integer
						# which means truncating the result to an integer
						if isinstance(operand1,(int,long)) and isinstance(operand2,(int,long)):
							result=operand1/operand2
						else: # Python has a math.trunc() which seems to do just what we want!!
							result=math.trunc(operand1/operand2)
					else:
						raise Exception("Integer division by zero attempted.")
				elif operator=="/": # non-integer division
					if operand2!=0:
						# we'll have to force Python to do non-integer division
						if isinstance(operand1,(int,long)) and isinstance(operand2,(int,long)):
							result=float(operand1)/operand2
						else:
							result=operand1/operand2
					else:
						result=undefined ####raise Exception("Division by zero attempted.")
				elif operator=="^":
					result=(falsevalue,truevalue)[operand1^operand2]
				elif operator=="|":
					result=(falsevalue,truevalue)[operand1|operand2]
				elif operator=="||":
					result=(falsevalue,truevalue)[operand1 or operand2]
				elif operator=="&":
					result=(falsevalue,truevalue)[operand1&operand2]
				elif operator=="&&":
					result=(falsevalue,truevalue)[operand1 and operand2]
				elif operator=="<":
					result=(falsevalue,truevalue)[operand1<operand2]
				elif operator==">":
					result=(falsevalue,truevalue)[operand1>operand2]
				elif operator=="<=":
					result=(falsevalue,truevalue)[operand1<=operand2]
				elif operator==">=":
					result=(falsevalue,truevalue)[operand1>=operand2]
				elif operator=="==":
					# here we have to deal with undefined as well (which is now defined as None
					result=(falsevalue,truevalue)[operand1==operand2]
				elif operator=="!=":
					result=(falsevalue,truevalue)[operand1!=operand2]
				elif operator=="<<":
					result=shift(operand1,operand2)
				elif operator==">>":
					result=shift(operand1,-operand2)
				elif operator=="**":
					result=operand1**operand2
			else: # one or either operands are None (i.e. undefined)
				# comparison operators can still return something that is not None!!!
				# basically anything that should return True (1) or false (0) should
				# typically the || and && operators required boolean operands, I suppose we can map undefined to false, and anything else to true
				# although zero should map to false, and 1 to true, I suppose if it's not 1 it's false
				if operator=="||":
					result=(falsevalue,truevalue)[operand1==truevalue or operand2==truevalue]
				elif operator=="&&":
					result=(falsevalue,truevalue)[operand1==truevalue and operand2==truevalue]
				elif operator=="<":
					result=(falsevalue,truevalue)[operand1<operand2]
				elif operator==">":
					result=(falsevalue,truevalue)[operand1>operand2]
				elif operator=="<=":
					result=(falsevalue,truevalue)[operand1<=operand2]
				elif operator==">=":
					result=(falsevalue,truevalue)[operand1>=operand2]
				elif operator=="==":
					# here we have to deal with undefined as well (which is now defined as None
					result=(falsevalue,truevalue)[operand1==operand2]
				elif operator=="!=":
					result=(falsevalue,truevalue)[operand1!=operand2]
			if getDebug()&8:
				note("Result of applying "+str(operator)+" to "+str(operand1)+" and "+str(operand2)+"="+str(result))
			# MDH@05SEP2017: when a shortcut assignment place the result in the argument1 variable as well!!!
			if shortcutting:
				#######note("Shortcutting!")
				argument1.setValue(result)
		#######note("Operation result: "+str(result)+".")
		return result

# create the main M environment
import math
# create the root environment
Menvironment=Environment() # MDH@03SEP2017: the root M environment containing the M identifiers and functions always accessible
# populate the M environment with the predefined constants/variables
Menvironment.addIdentifier(DEBUG) # MDH@07SEP2017: using a question mark is probably a good idea for something undefined!!
Menvironment.addIdentifier(undefined,'?') # MDH@07SEP2017: using a question mark is probably a good idea for something undefined!!
Menvironment.addIdentifier(Identifier(_value=0),'false')
Menvironment.addIdentifier(Identifier(_value=1),'true')
Menvironment.addIdentifier(Identifier(_value="'\n'"),'lf') # MDH@18SEP2017
Menvironment.addIdentifier(Identifier(_value="'\r'"),'cr') # MDH@18SEP2017
Menvironment.addIdentifier(Identifier(_value=math.pi),'pi')
Menvironment.addIdentifier(Identifier(_value=math.e),'e')
# MDH@31AUG2017: let's add the function groups as well
Menvironment.addFunctions({'return':0,'list':-1,'sum':-2,'product':-3,'sorti':-6,'concat':-7,'out':-8,'outc':-9,'isalist':-10}) # special functions (0=return,negative ids=list functions)
Menvironment.addFunctions({'sqr':12,'abs':13,'cos':14,'sin':15,'tan':16,'cot':17,'rnd':18,'ln':19,'log':20,'eval':21,'error':22,'exists':23,'chr':24,'ord':25,'readlines':26,'exec':27,'readvalues':28,'len':29,'size':30,'defined':31,'undefined':32,'sign':45,'int':46,'jump':47,'in':48,'inch':49})
Menvironment.addFunctions({'while':100,'ls':101,'dir':102,'replicate':103,'intin':104,'find':105,'function':150,'join':199})
Menvironment.addFunctions({'if':200,'select':201,'case':202,'switch':203,'for':210,'function':211})

environment=None # MDH@03SEP2017: wait for the user name to be known!!!

def getTokentypeRepresentation(_tokentype,_ignoresign=False):
	tokentype=abs(_tokentype)
	result=str(tokentype)
	if tokentype==0:
		result="?"
	elif tokentype<OPERATOR_TOKENTYPE:
		result=os[tokentype-1]+"."
	elif tokentype==OPERATOR_TOKENTYPE:
		result="op"
	elif tokentype==SIGN_TOKENTYPE:
		result="sign"
	elif tokentype==INTEGER_TOKENTYPE:
		result="int"
	elif tokentype==REAL_TOKENTYPE:
		result="real"
	elif tokentype==SINGLEQUOTED_TOKENTYPE or tokentype==DOUBLEQUOTED_TOKENTYPE:
		result="str"
	elif tokentype==EXPRESSION_TOKENTYPE:
		result="expr"
	elif tokentype==IDENTIFIER_TOKENTYPE:
		result="id"
	elif tokentype==VARIABLE_TOKENTYPE:
		result="var"
	elif tokentype==FUNCTION_TOKENTYPE:
		result="fun"
	elif tokentype==USERFUNCTION_TOKENTYPE:
		result="ufun"
	if _ignoresign:
		return result
	return ("-","")[_tokentype>=0]+result
def getOperatorPrecedence(_operator):
	if _operator==declarationchar: # TODO I have to think about this...
		return 15
	if _operator==assignmentchar: # = also is part of soro and we do not want it to come out there!!!
		return 14
	if _operator=="..":
		return 2
	if _operator in ("**","**="):
		return 3
	if _operator in ("*","/","%","\\","//","%%","*=","/=","%=","\\=","//=","%%="): # all single-character operators (accidently?)
		return 4
	if _operator in (".","-","+",".=","-=","+="): # the bisexual operators
		return 5
	if _operator in ("<<",">>","<<=",">>="):
		return 6
	if _operator in ("<","<=",">",">="):
		return 7
	if _operator in ("==","!="):
		return 8
	if _operator in ("&","&="):
		return 9
	if _operator in ("^","^="):
		return 10
	if _operator in ("|","|="):
		return 11
	if _operator=="&&":
		return 12
	if _operator=="||":
		return 13
	raise Exception("Unknown operator "+str(_operator)+" encountered!")

# strings to be recognized as certain predefined tokens representing
# whitespace, unary operators, binary operators, functions, alphabetic characters, digits, period, quotes
# start with two-character operators, followed by unary and binary
# NOTE let's allow integer division with \ as well
# MDH@25AUG2017: we'll be using the period character for list concatenation as well (similar to what PHP does)
newlinechar="\n" # MDH@31AUG2017: the character used for separating lines in multiline expressions
periodchar="." # integer fraction part separator MDH@27AUG2017 now also a one- and two-character binary operator
declarationchar=":" # for 'declaring' an expression (or a list of expression that can be considered a block)
o=periodchar+"\^"+declarationchar # all one-character binary operators that are not also unary operators
# NOTE more convenient to put ! (possible part of != as binary operator) in the soro operator list, and to remove it from the os list!!!
# MDH@27AUG2017: it's also very convenient to be able to use = as a unary operator which means that the expression that is following should be evaluated
soro="!=-+" # single-character binary or unary operators
ls="(" # starts an argument list
le=")" # ends an (argument) list
ld="," # separates list arguments
w=" "+newlinechar # whitespace between tokens (include the newline character now)
commentchar=";" # any comment starts behind a semicolon
# also allowing underscores in identifiers and dollar signs and pound signs (forget about the pound signs we might need it for other stuff
a="_$abcdefghijklmnopqrstuvwxyz"
A="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
d="0123456789" # digits
# NOTE removing ! from the pure signs here, just like we did with - and + which are binary operators depending on where they are used!!!
s="~" # unary operators ('signs'), + represents identity so should be ignored where, the other three map to Function(9) and Function(10) respectively
# TODO I have to allow for the && and || two character binary operators as well
#			 in which case I have to remove & and | from o and move them over to os
equalchar="="
assignmentchar=equalchar # what is considered to be the single-character assignment operator
# I've set the first two-character binary operator character to ! which can also be a unary operator (this way it's more easily recognized!!!!
# NOTE better to use a string with the characters that can start a two-character binary operator, so we can use find to locate the character
# MDH@27AUG2017: we allow . to become a two-character operator as well (for creating a list of integers)
#								 which means adding to os, to so and to o2
os=equalchar+"<>"+periodchar+"*&|/%" # start of two-character operators (which by themselves can also be single-character operators (except ! which would constitute a unary operator))
# TODO only the ! operator is NOT an single-character binary operator as the others are!
#			 and you shouldn't be allowed to start an expression with a binary operator character
so=(('=',),('>','='),('<','='),(periodchar,),('*',),('&',),('|',)) # the tokens we allow behind the first character of the two character operator
# in order to quickly check two-character operators we can put all two-character operators in o2
o2=" != << <= >> >= == .. ** && || // %%" # the result of o2.find() should be non-negative to indicate a two-character operator i.e. a continuation of a single-character operator
ts="'"+'"' # starts a string literal
te="'"+'"' # ends a string literal
# we have some predefined identifiers which are all functions of a fixed number of arguments
# and here's the dictionary in which the identifiers themselves are stored
# we allow using M as variable, referring to the previously executed commands, given that the value is a list you can change elements (not recommended though)
class List(tuple): # wraps a list, to prevent de-listing
	def __init__(self,_list):
		tuple.__init__(self,_list)
	def getValue(self):
		return self
def getInteger(_value):
	if isinstance(_value,(int,long)):
		return _value
	if isinstance(_value,str) and len(_value)>0:
		if _value[0]=='~': # starts with complement 'sign'
			return ~getInteger(_value[1:])
		return int(_value)
	return None
def getValue(_value):
	if getDebug()&8:
		note("Obtaining the value of "+str(_value)+"...")
	if _value is not None:
		if isinstance(_value,list):
			return map(getValue,_value)
		if isinstance(_value,(int,long,float)):
			return _value
		if isinstance(_value,str):
			return _value
		# everything else is assumed to have a getValue() method (like Identifier and Expression)
		#####note("Calling getValue() on the value of type "+str(type(_value))+".")
		return _value.getValue()
	return _value
def listify(t):
	if isinstance(t,list):
		return t
	return list(t)
def stringify(t):
	if isinstance(t,str):
		return t
	return str(t)
def dequote(t):
	if t is None:
		return ('?',None)
	if isinstance(t,str) and len(t)>1:
		if t[:1] in ts and t[-1:] in te:
			return (t[1:-1],t[:1])
	return (str(t),None) # something not representing enquoted text!!
def enquote(t,quotechar="'"):
	return quotechar+t+quotechar
def textconcatenate(operand1,operand2):
	##note("Concatenating '"+str(operand1)+"' and '"+str(operand2)+"'.")
	(o1,qc1)=dequote(operand1)
	(o2,qc2)=dequote(operand2)
	##note("Concatenating texts '"+o1+"' and '"+o2+"'.")
	return enquote(o1+o2,(qc1,(qc2,ts[0])[qc2 is None])[qc1 is None])
def repeat(operand1,operand2):
	if isinstance(operand1,(int,long,float)):
		return repeat(operand2,operand1)
	if isinstance(operand2,(int,long,float)):
		(o,quotechar)=dequote(stringify(operand1))
		return quotechar+(o*operand2)+quotechar
	return None
def shift(operand,by):
	if by==0:
		return operand
	# MDH@14AUG2017: if operand is alphanumeric we rotate it
	if by<0:
		if isinstance(operand,(int,long)):
			return operand>>-by
		(operandtext,quotechar)=dequote(stringify(operand))
		# shift right means cut off the right-hand side and move it to the left-hand side
		l=len(operandtext)
		if l<=1 or ((-by)%l)==0:
			return operand
		shiftby=(-by)%l
		return quotechar+operandtext[-shiftby:]+operandtext[:l-shiftby]+quotechar
	if isinstance(operand,(int,long)):
		return operand<<by
	(operandtext,quotechar)=dequote(stringify(operand))
	# shift right means cut off the right-hand side and move it to the left-hand side
	l=len(operandtext)
	if l<=1 or (by%l)==0: # at most a single-character, result is the operand itself
		return operand
	shiftby=by%l # remove multiples of l
	return quotechar+operandtext[shiftby:]+operandtext[:shiftby]+quotechar
def getItem(_list,_index):
	if hasattr(_list,'__getitem__') and len(_list)>0:
		return _list[_index%len(_list)]
	return _list
# let's define two constants representing the value to use for true and the one for false
truevalue=1
falsevalue=0
# MDH@05SEP2017: by moving getOperationResult into Environment, it always knows the environment it is operating in
import random
# list of token types:
# 0=unknown
# 1=unfinished operator (i.e. < or > or =)
# 2=finished operator
# 3=integer literal
# 4=real literal
# 5=text literal
# 6=identifier
# let's use negative values for operators
def getTokentypeColor(_tokentype):
	tokentype=abs(_tokentype)
	if tokentype>0 and tokentype<=OPERATOR_TOKENTYPE: # an operator
		return OPERATOR_COLOR
	elif tokentype>=IDENTIFIER_TOKENTYPE: # an identifier
		return IDENTIFIER_COLOR
	else: # a sign, integer, real or string literal
		return LITERAL_COLOR
	return 0 # the default is black
# MDH@15AUG2017: we need an Operator class to distinguish operators from operands
class Operator:
	def __init__(self,_text,_precedence):
		self.text=_text
		self.precedence=_precedence
	def getPrecedence(self):
		return self.precedence
	def getText(self):
		return self.text
	def __repr__(self):
		return self.text
	def __str__(self):
		return self.text
####newlinechar='\n' # the newline character for use in multiline expressions
# MDH@01SEP2017: keep track of the TokenChars on a single line, so it's easy to remove one!!!
userInputLine=None # predefinition so we can use it in updateUserInputLine()
# updateUserInputLine() is typically called after every successful backspace!!!
def updateUserInputLine(_emptyline):
	if _emptyline: # supposed to clear the current line????
		reprompt() # clear the current line
	else:
		writeprompt() # output the prompt (alone) again
	output(str(userInputLine)) # write all input line token chars (not through write() of course because all color formatting is already in there!!)
class UserInputLine(list):
	# given that we descend from list there's not much that we need to do in this class
	def removeLastCharacter(self,_emptyline=True):
		if len(self)>0:
			result=self.pop()
		else:
			result=None
		if result is not None:
			updateUserInputLine(_emptyline)
		return result
	def __str__(self):
		result=""
		for character in self:
			result+=str(character)
		return result
	def append(self,_character):
		list.append(self,_character)
		if getDebug()&128:
			write("$",DEBUG_COLOR)
	def extend(self,_characters):
		list.extend(self,_characters)
		if getDebug()&128:
			write("$",DEBUG_COLOR)
	def reset(self,_characters=None):
		del self[:]
		if isinstance(_characters,list) and len(_characters)>0:
			self.extend(_characters)
		if getDebug()&128:
			write("@",DEBUG_COLOR) # for testing purposes
userInputLine=UserInputLine() # we only need a single instance

# MDH@22AUG2017: also more reliable to keep any token character is a separate class instance
#								 this can be a character that is to be written (when _color is given) or not
# MDH@23AUG2017: TokenChar is to be used to store a single user input token character exactly
#								 and as much debug information text as one wants
#								 setText should fail if
class TokenChar:
	# write allows additional colored text to be written (even if there's no token character
	# append() is doing all the writing!!!
	def append(self,_towrite,_color=None):
		if not isinstance(_towrite,str):
			return None
		self.color=(0,_color)[isinstance(_color,int)]
		# if this is the first write of anything of this TokenChar (no matter where it came from), we should register
		# this would be the safest place to do so (we could have did it in the constructor or even better start though)
		if len(self.writtentext)==0:
			userInputLine.append(self)
			if self.debug&128:
				self.writtentext.append(write('<'+str(len(userInputLine))+'>',DEBUG_COLOR))
		#########output(("@","!")[self.echo])
		self.writtentext.append(writeColoredText(getColoredText(_towrite,_color),self.echo))
		return self
	# you can only define significant character text once
	def start(self):
		if self.debug&2:
			self.append("(",DEBUG_COLOR)
	def __init__(self,_debug,_echo):
		self.debug=_debug
		self.echo=_echo
		self.text=""
		self.writtentext=[]
		self.ended=-1 # keep track of how many characters were had before writing the end of tokenchar characters
		self.color=None
		self.error=None
		self.start()
	def end(self):
		if self.ended<0:
			self.ended=len(self.writtentext)
			# MDH@31AUG2017: we want to be able to return to just before the ) is written (as would be the effect of calling unend() on the
			#								 last written token
			#######write(None) # by writing None (i.e. no text), write will insert a None ColoredText instance, that will be used to remove this token char from what it wrote on the current line
			# keep track of the number of characters actually written (so we can remove them on unend)
			if self.echo:
				if self.debug&2:
					self.append(")",DEBUG_COLOR)
	def unend(self):
		if self.ended>=0: # return to whatever we had when we ended!!!
			self.writtentext=self.writtentext[:self.ended]
		self.ended=-1
	def isEnded(self):
		return self.ended>=0
	def __str__(self):
		result=""
		for coloredtext in self.writtentext:
			result+=str(coloredtext)
		return result
	def getColor(self):
		return self.color
	def getText(self):
		return self.text
	def isEmpty(self): # return True if no text is as yet defined
		return len(self.text)==0
	def getError(self):
		return self.error
	def set(self,_tokenchar,_color):
		if not isinstance(_tokenchar,str): # invalid input
			self.error="Token character not of type string but "+("of type "+str(type(_tokenchar)),"undefined")[_tokenchar is None]+"."
		elif len(_tokenchar)>0:
			if len(self.text)>0:
				self.error="Not allowed to set the token character more than once."
			elif self.append(_tokenchar,_color) is not None: # success
				self.text=_tokenchar
				return self
		return None
# MDH@19SEP2017: convenience class to easily get the text property
class TokenChars(list):
	def getText(self):
		result=""
		for tokenchar in self:
			result+=tokenchar.getText()
		return result
	def __str__(self):
		return self.getText()
# a bit of a nuisance to implement a token without a written prefix, infix and postfix
# for storing the debug information of where the token starts, is split in significant token characters and non-significant token characters
# and a postfix where it ends
class Token:
	# NOTE do NOT call write unless self.output is True
	def write(self,_towrite,_color=None):
		# append it to the current TokenChar (not part of the token character text!!)
		if len(self.suffix)==0:
			self.text[-1].write(_towrite,(self.color,_color)[isinstance(_color,int)])
		else:
			self.suffix[-1].write(_towrite,(self.color,_color)[isinstance(_color,int)])
	def getLastWrittenColor(self): # this would be the color in which the last written token character was written
		if len(self.text)==0:
			return None
		return self.text[-1].getColor()
	# there's either appending to self.text or self.suffix (unfortunately)
	# _any means doesn't have to be empty (when adding debug information)
	# I think it's a good idea to immediately append the new token char
	def getTextTokenchar(self,_any):
		if len(self.text)>0: # we have tokenchars
			if _any or self.text[-1].isEmpty(): # if anything goes, or the last token char is empty return that
				return self.text[-1]
			# if we get here, we're going to create a new tokenchar, so we should end the last one
			self.text[-1].end()
		tokenchar=TokenChar(self.debug,self.echo)
		try:
			self.text.append(tokenchar)
		except Exception,ex:
			tokenchar=None
		return tokenchar
	def getSuffixTokenchar(self,_any):
		tokenchar=None
		if len(self.suffix)>0: # we have tokenchars
			if _any or self.suffix[-1].isEmpty(): # if anything goes, or the last token char is empty return that
				return self.suffix[-1] # I guess I should return that!!!
			# if we get here, we're going to create a new tokenchar, so we should end the last one
			self.suffix[-1].end()
		tokenchar=TokenChar(self.debug,self.echo)
		try:
			self.suffix.append(tokenchar)
		except Exception,ex:
			tokenchar=None
		return tokenchar
	# but whatever is to be appended in some color
	def append(self,_tokenchar,_color=None):
		# if not of the right type throw an exception
		# I need to rewrite self.color if the previous tokenchar used another color
		if not isinstance(_tokenchar,str):
			self.error="Type of item to append to token text not text."
		elif len(_tokenchar)>0: # something to append for real
			# we need a token char that is not empty (so we pass False into _any)
			tokenchar=self.getTextTokenchar(False)
			if tokenchar is not None: # success!!!
				color=(None,((_color,self.color)[_color is None],-1)[self.color==self.getLastWrittenColor()])[self.echo]
				tokenchar.set(_tokenchar,color)
				return self
			self.error="Failed to store "+_tokenchar+"."
		return None
	def start(self):
		# NOTE by NOT producing any debug output when _tokenchar is NOT defined (typically None), as is the case with expressions
		#			 there's no initial expression token prefix
		if self.echo:
			if self.debug&6: # something to write immediately
				if self.debug&2: # immediately write the start of token text
					self.writtenprefix.append(write('[',DEBUG_COLOR)) # an empty token character
				if self.debug&4:
					self.writtenprefix.append(write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR))
		else: # no need to keep track of the written text
			pass
	def __init__(self,_tokentype,_debug=0,_echo=True,_tokenchar=None):
		# MDH@10SEP2017: essential that debug is integer!!!!!
		self.debug=(0,_debug)[isinstance(_debug,int)]
		self.echo=(False,True)[_echo] # MDH@10SEP2017: a default output
		self.color=0 # MDH@10SEP2017: TODO do I need this????????
		self.error=None # MDH@21AUG2017: the backspace() method requires the use of self.error here as well
		self.text=TokenChars() # replacing: "" # the meaningful text
		self.suffix=[] # replacing: "" # what's appended to the token AFTER it ends (typically whitespace or a comment)
		self.continuable=True # assume to be continuable to start with
		self.ended=False # not ended until end() is actually called!!!
		self.setType(_tokentype)
		# what used to go in start
		### added: prefix / infix / postfix written stuff initialized to empty strings
		# MDH@31AUG2017: now contain all colored text in separate ColoredText instances
		self.writteninfix=[]
		self.writtenprefix=[]
		self.writtenpostfix=[]
		self.start()
		if isinstance(_tokenchar,str):
			self.append(_tokenchar)
		# append whatever token we received
	# MDH@21AUG2017: support for error reporting
	def getError(self):
		return self.error
	def isEmpty(self):
		return len(self.suffix)==0 and len(self.text)==0
	def discontinued(self): # call whenever meaningful text can no longer be entered (e.g. when adding whitespace)
		# allow discontinuation once
		result=self.continuable
		if result:
			self.continuable=False
			if len(self.text)>0:
				self.text[-1].end()
			if self.echo:
				if self.debug&2: # indicates the start of the suffix (if any)
					self.writteninfix.append(write("|",DEBUG_COLOR)) ###self.write("|",DEBUG_COLOR)
		return result
	def unendText(self):
		if len(self.text)>0:
			self.text[-1].unend()
	def undiscontinued(self): # we might want to undiscontinue (when the suffix is removed)
		result=not self.continuable
		if result:
			self.continuable=True
			self.unendText() # e.g. to be overridden by subclasses
			if self.echo:
				if self.debug&2: # indicates the start of the suffix (if any)
					self.writteninfix=[]
			# this could be the first character of a possible two-character operator
		return result
	def end(self):
		if not self.ended: # once suffices!!
			self.ended=True # mark as discontinuable although perhaps it's better not to if I'm not discontinued somehow, in which case it remains continuable even though it ended!!!
			if len(self.suffix)>0:
				self.suffix[-1].end()
			elif len(self.text)>0:
				self.text[-1].end()
			# any operator that might have been continued, register it as operator immediately, so one cannot continue it with the second character!!!
			if self.type>0 and self.type<OPERATOR_TOKENTYPE:
				self.type=OPERATOR_TOKENTYPE
			if self.echo:
				if self.debug&2:
					self.writtenpostfix.append(write(']',DEBUG_COLOR))
			# MDH@23AUG2017: end the last token characters
		return self
	def unend(self): # which undo any assumed end (what we'll do with the last token in an expression), so it can be continued again
		# unending doesn't change the continuability (anymore)
		# MDH@24AUG2017: BUT it should if we can make this token continuable again
		#								 most tokens can be made continuable again
		#								 as long as we have a suffix we cannot make the token continuable again
		#								 but if we do not have a suffix, most tokens except the two-character operators, 1-character operators not in os, and string literals are not continuable again
		if self.ended: # something to unend, therefore we have to remove the ] written at the end
			self.ended=False
			# we should make the last token continuable again if needed, I guess we can simply call unend on it
			if len(self.suffix)>0: # I suppose this means it's discontinuable, but we do not want to undo that actually just to unend the suffix token
				self.suffix[-1].unend()
			elif len(self.text)>0:
				# MDH@24AUG2017: here we should attempt to make the token continuable again, if we succeed we can unend the last significant token char
				#								 NOTE if we manage to get make it continuable again
				#								 NOTE unend() is called when the token behind it is cleared, and removed
				#											then the user could add a new character which may or may not be a continuation of this token
				#											or the user could do a backspace as well
				if not self.continuable: # not currently continuable
					# string literals and (single-character) signs cannot be made continuable themselves
					# there's ONE exception with operators i.e. the assignment operator
					# BUT we do NOT have access to the token in front of the assignment operator token, which means that the caller should take care of that situation
					if self.type!=SINGLEQUOTED_TOKENTYPE and self.type!=DOUBLEQUOTED_TOKENTYPE and self.type!=SIGN_TOKENTYPE and self.type!=OPERATOR_TOKENTYPE:
						self.undiscontinued() # succeeded in making this token continuable again
				else: # already continuable, TODO check if this is really possible when the thingie is ended, well it is possible to end without discontinuing?????
					# when dealing with an already continuable operator
					if self.type==OPERATOR_TOKENTYPE:
						# can only be continuable, when it allows a second operator character in which case we have to reset it
						self.type=1+os.find(self.text[-1].getText())
					self.text[-1].unend()
			# NOTE perhaps we can empty the writtenpostfix no matter?????
			if self.echo:
				if self.debug&2:
					self.writtenpostfix=[]
		return self
	def getSuffix(self): # to return the suffix text
		result=""
		for tokenchar in self.suffix:
			result+=tokenchar.getText()
		return result
	def getWrittenText(self):
		writtentext=""
		for tokenchar in self.text:
			writtentext+=tokenchar.getWritten()
		return writtentext
	def getWrittenSuffix(self):
		writtensuffix=""
		for tokenchar in self.suffix:
			writtensuffix+=tokenchar.getWritten()
		return writtensuffix
	def getWrittenPrefix(self):
		writtenprefix=""
		for coloredtext in self.writtenprefix:
			writtenprefix+=str(coloredtext)
		return writtenprefix
	def getWrittenInfix(self):
		writteninfix=""
		for coloredtext in self.writteninfix:
			writteninfix+=str(coloredtext)
		return writteninfix
	def getWrittenPostfix(self):
		writtenpostfix=""
		for coloredtext in self.writtenpostfix:
			writtenpostfix+=str(coloredtext)
		return writtenpostfix
	# MDH@01SEP2017: now we have getCharacters() we should be able to make getWritten() obsolete at some point!!!
	def getCharacters(self):
		characters=[]
		characters.extend(self.writtenprefix)
		characters.extend(self.text)
		characters.extend(self.writteninfix)
		characters.extend(self.suffix)
		characters.extend(self.writtenpostfix)
		return characters
	def getWritten(self):
		return self.getWrittenPrefix()+self.getWrittenText()+self.getWrittenInfix()+self.getWrittenSuffix()+self.getWrittenPostfix()
	# getRepresentation() returns the type in gray and the text itself in black
	def getRepresentation(self):
		return getColorText(INFO_COLOR)+' '+self.getText()+getColorText(DEBUG_COLOR)+":"+getTokentypeRepresentation(self.type)
	def ignore(self,_tokenchar): # any whitespace that's in the token needs to be displayed but does not change the type
		# TODO perhaps it's better to change this is making this thing discontinuable, and then add it
		# we'll be appending at least one character
		if isinstance(_tokenchar,str) and len(_tokenchar)>0: # TODO this should be an assertion
			self.discontinued() # the discontinuation debug text should come in front of the first suffix token char
			# MDH@05SEP2017: any whitespace in an 'unfinished' binary operator should also be promoted to a finished binary operator
			if self.type>0 and self.type<OPERATOR_TOKENTYPE:
				self.type=OPERATOR_TOKENTYPE
			self.getSuffixTokenchar(False).set(_tokenchar,(-1,self.color)[self.echo]) # TODO what color????
			if len(self.suffix)>0: # very likely though
				return self
			self.error="Failed to 'ignore' "+_tokenchar+"."
		return None
	def isEnded(self):
		return self.ended
	def isContinuable(self):
		return self.continuable
	# add() should raise an Exception if some low-level error occurs (like memory problems)
	def add(self,_tokenchar):
		# ASSERTION _tokenchar should be of type String
		# returns any error that might occur, when attempting to add the
		if _tokenchar is None:
			raise Exception("Undefined input character.")
		if not self.continuable: # if not continuable, the character cannot be added
			raise Exception("Cannot add "+_tokenchar+" to a finished token.")
		# MDH@27AUG2017: we're going to do some mumbo jumbo here in case the given token character ends with the period char
		#								 which in the case of an integer type switches to real type and writes the period char
		#								 which could still turn into a double period operator (which the same color!!!)
		#								 unless we wait for the first character behind the period and NOT show the period until that next character is processed!!
		if len(_tokenchar)>0:
			if self.type==INTEGER_TOKENTYPE and _tokenchar[-1]==periodchar: # the decimal separator
				if len(_tokenchar)>1:
					self.append(_tokenchar[:-1])
				self.setType(REAL_TOKENTYPE)
				self.append(periodchar) # MDH@03SEP2017: no need for that anymore because it will be removed when followed by another period char!!!,OPERATOR_COLOR) # show in the operator color
			else: # something else, so we'll do an ordinary append
				self.append(_tokenchar)
		return self
	# MDH@21AUG2017: removing the last character is fun
	def backspace(self):
		# NOTE ALL token characters now contain at least one token character (the significant ones in self.text, the insignificant ones in self.suffix)
		# NOTE it's possible that we're NOT continuable AND there's no suffix!!!
		#			 it's also possible that a character is not whitespace in which case we need to remove another character
		# MDH@23AUG2017: NOT until we're removing a significant token character, do we force the token to be discontinued
		#								 i.e. make it continuable again, the problem is that even when that happens it is still possible to add whitespace
		#								 which means that when that happens we would remove the continuable
		# MDH@31AUG2017: any newline character will always be in the suffix of a token i.e. it is a whitespace character
		if len(self.suffix)>0:
			self.suffix.pop() # very convenient
			# NOTE never force continuability until actually removing a significant token
			#			 BUT that's a problem because sometimes the thing is not continuable AND there's no suffix
			if len(self.suffix)>0:
				self.suffix[-1].unend()
			else:
				# suffix is removed, which means that most types need to become continuable again
				if not self.isContinuable():
					if self.type!=SINGLEQUOTED_TOKENTYPE and self.type!=DOUBLEQUOTED_TOKENTYPE:
						self.undiscontinued()
			return self
		l=len(self.text)-1 # index of the last tokenchar
		if l>=0:
			removedtokenchar=self.text.pop() # very convenient
			# we might need to change the token type depending on what is removed...
			# MDH@18SEP2017: we need to undo the discontinuation for sure
			if not self.isContinuable():
				self.undiscontinued()
			if self.type==REAL_TOKENTYPE:
				# removing the tokenchar that contains the period?
				if removedtokenchar.getText()[-1]==periodchar:
					self.type=INTEGER_TOKENTYPE
			elif self.type==OPERATOR_TOKENTYPE:
				# removing the second character of a two-character operator???
				if l>0: # still tokens left, so reset the type
					# MDH@18SEP2017: beware when removing the period from .. should remove the
					#								 entire token and append the period to the integer token
					#								 but we cannot do that here as I don't know about other tokens
					self.type=1+os.find(self.text[-1].getText())
			if l>0:
				self.text[-1].unend()
			return self
		self.error="Please report the following bug: No character left in token to remove!"
		return None
	def getText(self):
		result=""
		for tokenchar in self.text:
			result+=tokenchar.getText()
		return result
	def getType(self):
		return self.type
	def assigns(self):
		if self.type!=OPERATOR_TOKENTYPE: # not an operator
			return False
		if len(self.text)==0 or self.text[-1].getText()!=assignmentchar: # last essential character NOT the assignment character
			return False
		# all operator tokens that end with the assignment char and are of length unequal to two always are assignments
		# operators of length 2 ending with assignment char only are when not starting with < > ! or = which would make it a comparison operator!!!
		return len(self.text)!=2 or not self.text[0].getText() in ('<','>','!','=')
	# NOTE setType() won't change the coloring...
	# MDH@31AUG2017: let's see whether we can actually change the coloring if the type changes
	#								 assuming that this is the current token being written actively i.e. it is not ended or discontinued
	def setType(self,_tokentype):
		self.type=_tokentype
		if self.echo:
			self.color=getTokentypeColor(self.type) # initiate the color to use when writing once
		# TODO how do we want to treat whitespace?????
		if self.type<=0: # only whitespace characters allowed, so everything that follows is whitespace!!
			self.discontinued()
		# rewrite the entire text in the new color if the type changed
		return self.type
	def __repr__(self):
		return self.getText()
	def __str__(self):
		return self.getText()
# we have to either choose to append a token immediately when it is created, or until it ends (as we used to)
# nevertheless we can keep track of the current token in self.token (which is the active token)
# and as long as we let the token's add method to do the writing, and the constructor to write the tokens color
# it's going to be OK
# NOTE by making Token.add() method return the token itself, we can replace self.token=tokenchar by self.token=Token(<type>).add(tokenchar) conveniently
# if we make Expression a Token as well, we can store subexpression as tokens itself
# we simply need to override some of the simple Token methods
class Expression(Token):
	def reset(self):
		# no need to keep track of the expression and/or written expression anymore with the tokens in place
		self.tokens=[]
		# alternatively we can start with a 'whitespace' token (all the other whitespace is appended to the token)
		self.token=None # which also starts the optional whitespace token!!!
	# how about using the Expression itself to store the whitespace at the beginning????
	def start(self):
		# NOTE overrides Token.start() i.e. should be called through the Token constructor
		#			 there's no initial expression token prefix
		if self.echo:
			if self.debug&6: # something to write immediately
				if self.debug&2: # immediately write the start of token text
					self.writtenprefix.append(write('{',DEBUG_COLOR)) # an empty token character
				if self.debug&4:
					self.writtenprefix.append(write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR))
		else: # no need to keep track of the written text
			pass
	# MDH@10SEP2017: _debug to default to 0 not None (as an integer required!!)
	# MDH@12SEP2017: BEWARE now by default does NOT echo (i.e. output) what is input (which I had to find out the hard way!!!!)
	# MDH@19SEP2017: _executable determines whether or not the expression should be immediately executable
	def isImmediatelyExecutable(self):
		return self.immediatelyexecutable
	def setImmediatelyExecutable(self,_immediatelyexecutable):
		self.immediatelyexecutable=_immediatelyexecutable
		return self
	def __init__(self,_environment,_parent=None,_debug=0,_echo=False,_tokenchar=None):
		Token.__init__(self,EXPRESSION_TOKENTYPE,_debug,_echo,_tokenchar)
		self.value=None # MDH@07SEP2017: value unknown...
		self.declared=False # initially assumably not declared...
		self.parent=_parent # supposedly the parent expression to revert to when receiving the ld or le character
		if self.parent is not None: # MDH@19SEP2017: the parent provides the executability
			self.immediatelyexecutable=self.parent.isImmediatelyExecutable()
		else:
			self.immediatelyexecutable=True
		self.environment=_environment # MDH@30AUG2017: knows it's environment, so it can check for the existance of certain variables, when being composed
		self.newidentifiers=[] # MDH@30AUG2017: keep track of any identifiers declared in subexpressions
		self.allidentifiernames=_environment.getAllIdentifierNames() # for the continuation
		#####write(('X','Y')[self.parent is not None])
		#######self.evaluatedexpression=None # MDH@15AUG2017: the result of evaluating the expression (which might well be a single token)
		self.reset()
	# MDH@30AUG2017: any subexpression should register any identifier initialization, so that further subexpression can check whether it was created before on that level
	def initializesIdentifier(self,_identifiername):
		if not _identifiername in self.newidentifiers:
			self.newidentifiers.append(_identifiername)
	# treated as a Token instance, we can return the text representation (without output formatting colors)
	def initializedIdentifier(self,_identifiername):
		# did I initialize this identifier?
		if _identifiername in self.newidentifiers:
			return True
		# is this identifier initialized in the parent?
		if self.parent is not None:
			return self.parent.initializedIdentifier(_identifiername)
		return False # neither
	# 'overriding' the global identifierExists() function that only looks at identifiers created before, with also looking at the identifiers that are initialized in this expression
	# NOTE that this is not fail-safe because sometimes certain expressions will NOT get evaluated, so it's still possible that the variable will NOT exist before it is used
	def identifierExists(self,_identifiername):
		# always look in the global pool first (that's quickest)
		if self.environment is not None and self.environment.identifierExists(_identifiername):
			return True
		return self.initializedIdentifier(_identifiername)
	def getIdentifier(self,_identifiername): # MDH@31AUG2017: this is basically about existing identifier of which we want to check the value
		if self.environment is None:
			return None
		return self.environment.getExistingIdentifier(_identifiername)
	def identifiersExistStartingWith(self,_identifierprefix):
		# if in the global pool, we're done immediately
		if self.environment is not None and self.environment.identifiersExistStartingWith(_identifierprefix):
			return True
		# I might have them
		for newidentifier in self.newidentifiers:
			if newidentifier.startswith(_identifierprefix):
				return True
		# my parent might have them
		if self.parent is not None:
			if self.parent.identifiersExistStartingWith(_identifierprefix):
				return True
		# NOPE nobody
		return False
	def functionsExistStartingWith(self,_functionprefix):
		# if in the global pool, we're done immediately
		if self.environment is not None and self.environment.functionsExistStartingWith(_functionprefix):
			return True
		# my parent might have them
		if self.parent is not None:
			if self.parent.functionsExistStartingWith(_functionprefix):
				return True
		# NOPE nobody
		return False
	def functionExists(self,_identifiername):
		if self.environment is not None and self.environment.functionExists(_identifiername):
			return True
		if self.parent is None:
			return False
		return self.parent.functionExists(_identifiername)
	def getFunction(self,_identifiername):
		function=self.environment.getFunction(_identifiername)
		if function is None and self.parent is not None:
			function=self.parent.getFunction(_identifiername)
		return function
	def getText(self):
		result=Token.getText(self) ###self.text # this would be the whitespace at the beginning...
		# NOTE if the token is a subexpression, the subexpression will enclose it's text in parenthesis (so I won't have to check for that type of token myself)
		for token in self.tokens:
			result+=token.getText()
		return result
	def getTokentype(self):
		# will either return the type of the current token (not yet finished and registered)
		# or the negative value of the last token
		result=0
		if self.token is not None:
			result=self.token.getType()
			if self.token.isEnded() or not self.token.isContinuable(): # supposedly finished
				result=-result
		return result
	def endToken(self):
		toend=None
		if self.token is not None: # a previous token to end
			toend=self.token
		elif len(self.text)>0: # some insignificant text at the beginning of the expression to end
			toend=self.text[-1]
		if toend is None:
			return
		toend.end()
	# newToken changed a bit so it doesn't require a character to add per se
	def newToken(self,_token):
		self.tokens.append(_token)
		self.token=self.tokens[-1] # ascertain that self.token equals the last token on the tokens list
		return self.token
	def addToken(self,_tokentype,_tokenchar,_echo=None):
		self.endToken() # end whatever token is pending FIRST i.e. BEFORE actually creating the new token (which might be writing debug info)
		####output("**"+_tokenchar+"**")
		echo=(self.echo,_echo)[isinstance(_echo,bool)]
		if _tokentype<=0: # expression to add
			token=Expression(self.environment,self,self.debug,echo,_tokenchar)
		else:
			token=Token(_tokentype,self.debug,echo,_tokenchar) # immediately push the new token on top of the stack
		####output("%%"+str(token)+"%%")
		return self.newToken(token)
	# we can make add return the active expression, to replace the active expression
	# NOTE only whitespace tokens can return a negative value??? this makes it harder to know when a token is still active????
	# we might consider returning None when an error occurs
	def getError(self):
		return self.error
	def getErrorText(self):
		if self.error is None:
			return None
		return str(self.error)
	# ending an Expression token is a little different than ending a Token token
	def end(self):
		if not self.ended: # once suffices!!
			self.ended=True # mark as discontinuable although perhaps it's better not to if I'm not discontinued somehow, in which case it remains continuable even though it ended!!!
			# should 'end' whatever needs ending...
			if len(self.suffix)>0:
				self.suffix[-1].end()
			elif len(self.tokens)>0:
				self.tokens[-1].end()
			elif len(self.text)>0:
				self.text[-1].end()
			if self.echo:
				if self.debug&2:
					self.writtenpostfix.append(write('}',DEBUG_COLOR))
		return self
	def unend(self): # call this method to be able to continue the last token
		# there's no COMMENT token at the end anymore but there might be a suffix, and the thing is likely to NOT being continuable anymore!!
		if self.ended:
			self.ended=False
			if len(self.suffix)>0:
				self.suffix[-1].unend()
			elif len(self.tokens)>0:
				self.tokens[-1].unend()
			elif len(self.text)>0:
				self.text[-1].unend()
			if self.echo:
				if self.debug&2:
					self.writtenpostfix=[]
		""" replacing:
		if self.parent is None: # only the suffix at the top level should be removed (which always is the comment)
			if not self.continuable:
				self.suffix=[] ####replacing: "" # remove any comment (because we want to be able to continue the expression)
				self.continuable=True # assume continuable again of course
		if len(self.tokens)>0: # which should be the case
			self.token=self.tokens[-1].unend() # unend the token so it can be continued (if it was continuable to start with!!)
		else: # no starting token yet (should not be allowed though, storing empty expressions)
			self.token=None
		"""
		return self
	def ends(self): # checks the end of the expression
		# ASSERTION self.error needs to be None
		# according to the scheme of Aug 1, 2017 in a lot of situations we cannot end the expression
		# first of all we can only end the top expression
		# we cannot end when we're in a current token that's not finishable, e.g. a string literal
		result=None
		tokentype=self.setTokentype(self.getTokentype())
		# if negative either in whitespace or behind a finished token
		# I guess a person could have entered whitespace itself, which we should consider as incomplete
		if tokentype>0: # still inside a token
			# any operator cannot end an expression
			if tokentype<OPERATOR_TOKENTYPE: # possibly incomplete operator
				result="Expression incomplete: you still need to either enter the second character of the operator or the second operand."
			elif tokentype==OPERATOR_TOKENTYPE: # I suppose this should not happen as well because any operator should be finished
				result="Please report this bug: you have an unfinished operator in your expression."
			elif tokentype==SIGN_TOKENTYPE:
				result="Please report this bug: you have an unfinished unary operator in your expression."
			elif tokentype>=IDENTIFIER_TOKENTYPE: # an identifier
				# given that we're not assigning the given identifier should exist
				# it might be the function name but without an opening parenthesis a user can still change it
				if not self.identifierExists(self.token.getText()): # MDH@30AUG2017: benefit of the doubt it it looks like the variable is initialized, somewhere in this expression itself
					# MDH@30AUG2017: it makes sense to allow declaring a variable without initializing it if it's the only token in an expression
					#								 in which case it is allowed to end the expression here and now
					if self.parent is None or len(self.tokens)>1:
						result="You cannot end an expression with an uninitialized variable."
					else: # we may assume that the variable will be created when the expression is evaluated!!!
						self.parent.initializesIdentifier(self.token.getText())
			elif tokentype==SINGLEQUOTED_TOKENTYPE or tokentype==DOUBLEQUOTED_TOKENTYPE:
				result="Expression incomplete: first of all you need to enter a quote to finish text."
		elif tokentype<0: # negative token types
			if tokentype+OPERATOR_TOKENTYPE==0:
				result="Expression incomplete: second operand to which the operator should be applied to yet to be entered."
			elif tokentype+SIGN_TOKENTYPE==0:
				result="Expression incomplete: Operand to which the unary operator should be applied yet to be entered."
		return result
	def setTokentype(self,_tokentype):
		if self.debug&8:
			write("{"+str(_tokentype)+"}",DEBUG_COLOR)
		return _tokentype
	# MDH@08AUG2017: with all token types having positive types now, no need to check the type anymore
	def getLastTokenText(self): # returns the last non-whitespace token text
		if self.token is None:
			return ""
		return self.token.getText()
	def isDeclared(self):
		return self.declared
	def flagAsDeclared(self):
		self.declared=True
		return self
	# MDH@20SEP2017: it makes sense to collect all identifier names assigned to that do not yet exist????
	def initializes(self,_environment):
		result=list()
		behindassigningoperator=False
		behindidentifiername=None # the name of the non-existing identifier we are behind
		for token in self.tokens:
			# first look at the conditions that will prevent further searching
			if behindassigningoperator: # something being assigned to
				# only accept iff the given identifier does not yet exist, and is therefore initialized...
				if not _environment.identifierExists(behindidentifiername):
					result.append(behindidentifiername)
				# start over
				behindassigningoperator=False
				behindidentifiername=None
			tokentype=token.getType()
			if tokentype==EXPRESSION_TOKENTYPE:
				# theoretically one could initialize variables in the indices of an IdentifierElementExpression as well
				subexpressioninitializes=token.initializes(_environment)
				if len(subexpressioninitializes)>0:
					result.extend(subexpressioninitializes)
			elif tokentype==IDENTIFIER_TOKENTYPE:
				# careful the identifier might be a function
				identifiername=token.getText()
				if not _environment.functionExists(identifiername):
					behindidentifiername=identifiername
			else: # neither expression nor identifier, so could be an operator (but also a literal of course)
				if behindidentifiername is not None: # previous token was an identifier
					if token.assigns(): # if this is an assigning operator token almost there!!!
						behindassigningoperator=True
		return result
	def assigns(self):
		# an expression assigns when it contains an assignment or any of it's expression assigns
		# an assignment operator can only occur behind an identifier so we can speed up testing this way
		# and there needs to be something behind the assignment operator as well that can be assigned
		behindidentifier=False
		behindassigningoperator=False
		for token in self.tokens:
			# first look at the conditions that will prevent further searching
			if behindassigningoperator: # look no further
				return True
			tokentype=token.getType()
			if tokentype==EXPRESSION_TOKENTYPE:
				if token.assigns():
					return True
			else: # not an expression
				# behind an identifier????
				if behindidentifier: # previous token was an identifier
					if token.assigns(): # if this is an assigning operator token almost there!!!
						behindassigningoperator=True
			# update behindidentifier in ALL situations
			if tokentype==IDENTIFIER_TOKENTYPE: # absolutely
				behindidentifier=True
			elif tokentype!=EXPRESSION_TOKENTYPE: # certainly not
				behindidentifier=False
			else: # for expressions, only when denoting an identifier element expression
				behindidentifier=isinstance(token,IdentifierElementExpression)
		return False
	def getContinuation(self):
		return self.continuation
	def getAutoInserted(self):
		return self.autoinserted
	def add(self,_tokenchar,_echo=None):
		echo=(self.echo,_echo)[isinstance(_echo,bool)]
		# default result is the current expression itself
		self.value=None # MDH@07SEP2017: recomputation would be needed afterwards for sure
		self.error=None # to store the error in
		self.autoinserted=None # MDH@21SEP2017: what was automatically inserted by add()
		self.continuation=None # MDH@12SEP2017: we are going to compute a continuation
		result=self # the default result is self
		try:
			# STEP 0. IF NO LONGER CONTINUABLE THERE'S NOT MUCH TO DO (but 'ignore' _tokenchar)
			if self.isContinuable():
				# STEP 1. DETERMINE WHETHER _tokenchar IS A CONTINUATION OF THE CURRENT TOKEN (as stored in self.token)
				#					NOTE that some situations are dealt with completely in itself i.e. take care of adding _tokenchar to the current token as well, whereas many situations determine whether to create a new token not the addition of _tokenchar
				tokentype=self.setTokentype(self.getTokentype()) # given that we're NOT keeping track of the token type in self, we reconstruct it from self.token and self.tokens
				# within certain tokens almost any character is a continuation, so we should deal with those situations first
				# MDH@10AUG2017: we need to distinguish between a comment suffix (which cannot be ended) and a closing parenthesis (subexpression) suffix which can be ended with any character
				#								 NO we don't because any whitespace behind a subexpression will end up in the parent's subexpression token suffix instead of the suffix of the subexpression itself
				if tokentype==SINGLEQUOTED_TOKENTYPE or tokentype==DOUBLEQUOTED_TOKENTYPE: # inside a string literal (if we were in the string literal suffix tokentype whould be negative!!!
					# we append the token that possibly ends the string literal as well
					self.token.add(_tokenchar) # raises an exception on some unexpected (low-level) error
					if _tokenchar==te[tokentype-SINGLEQUOTED_TOKENTYPE]:
						self.token.discontinued() ## replacing: tokentype=self.setTokentype(self.tokenends()) # finishes the string literal
				elif _tokenchar in w: # a whitespace character not inside a string literal
					# a token never ends until a new character starts a new token
					if self.token is None: # append it to the text property of the superclass (which will contain the prefix of the expression (before the start of the first actual token)
						Token.add(self,_tokenchar)
					else:
						self.token.ignore(_tokenchar)
				else: # not inside a string literal or a whitespace input character
					# switching over to looking at some special characters first
					if _tokenchar==commentchar: # starts a comment
						# only allowed in the top expression
						if self.parent is not None:
							self.error="You cannot start a comment in a subexpression."
						else: # the expression was finishable, and was finished
							self.error=self.ends()
							if self.error is None: # yes, allowed
								self.ignore(_tokenchar)
					# how about taking care of the meta characters first?????
					# TODO it's NOT so elegant to return results here and now!!!
					elif _tokenchar in ld or _tokenchar in le: # ) ends the current expression, but shouldn't happen on the top-most expression though
						# we can make this more compact because end() will check whether we can end this expression
						if self.parent is None:
							self.error="You can only end a subexpression this way."
						else:
							self.error=self.ends()
							if self.error is None:
								# ends() used to do this, suppose I need it again!!!
								if self.token is not None:
									self.token.end()
								# MDH@10AUG2017: makes sense to store the closing parenthesis as suffix in the current expression instead of as a separate token in the parent expression
								#								 assuming for now that the last token was ended by self.ends() as it should be
								# MDH@10AUG2017: then the problem is that a user should still be allowed to add whitespace to the suffix of the current expression until (s)he enters something else
								#								 so we cannot end this (sub)expression until that non-whitespace character is entered next!!!
								#								 SOLUTION we can add the whitespace to the suffix of the subexpression token of the parent, so there's no need to store it in the suffix of the subexpression itself!!!
								#								 QUESTION when will the subexpression itself need to be ended????? I guess the parent will do that
								#####self.end() # we want to end the subexpression here and now as a token and not wait until later, this is an issue though
								result=self.parent
								if _tokenchar in ld: # a comma should also start a new expression operand in the parent (similar to what the response to ls does), meaning we can now have multiple subexpressions in a row (as to create a list of values)
									result=result.addToken(0,_tokenchar,echo) # we're appending a new expression to the parent (effectively ending this expression token), and continuing with the new subexpression
									""" replacing:
									# but if the current expression is an IdentifierElementExpression, so should the next one be
									if isinstance(result,IdentifierElementExpression):
										result.endToken() # end me
										result=self.newToken(IdentifierElementExpression(self.getIdentifier(),self.environment,result,self.debug,echo,_tokenchar)) # pretty neat (if it works)
									else: # a normal expression to be added to the parent
										result=result.addToken(0,_tokenchar,echo) # we're appending a new expression to the parent (effectively ending this expression token), and continuing with the new subexpression
									"""
								else:
									self.ignore(_tokenchar) # append the closing parenthesis token in the suffix of this expression (so no longer ends up as a separate token)
									# if we're ending the last index token of an identifier element expression, we should end the identifier element expression as well
									if isinstance(result,IdentifierElementExpression):
										result.discontinued()
										result=result.parent
					elif _tokenchar in ls: # opening parenthesis: start of a new sub-expression
						# deal with invalid stuff first
						# tokentype 0 and all operators and signs are good and identifiers that are functions
						# but careful, the current token could be the whitespace token in which case the token text should be obtained from the token in front of the whitespace token
						# but also NOT allowed behind ) which is an expression token
						if tokentype!=0 and abs(tokentype)>SIGN_TOKENTYPE:
							if abs(tokentype)==EXPRESSION_TOKENTYPE:
								self.error="Cannot start a subexpression right behind another subexpression."
							elif abs(tokentype)>=IDENTIFIER_TOKENTYPE: # in/behind an identifier
								tokentext=self.token.getText()
								if not self.functionExists(tokentext): # not a function therefore NOT allowed
									# now allowed to index an existing variable of which the current value is a list (i.e. list)
									if self.immediatelyexecutable:
										identifier=self.getIdentifier(tokentext)
									if not self.immediatelyexecutable or identifier is not None: # an existing variable # MDH@30AUG2017: allow for 'locally' defined identifiers as well
										# MDH@19SEP2017: if not supposed to be immediately executable, don't check whether the current value is a list because it should be (when the expression is executed)
										if not self.immediatelyexecutable or isinstance(identifier.getValue(),list) or isinstance(identifier.getValue(),str): # can be indexed
											# we're going to replace the identifier by an IdentifierElementExpression
											self.tokens.pop() # popping off the identifier token (so we can replace it with the IdentifierElementExpression
											# MDH@19SEP2017: the IdentifierElementExpression has to set it's text to the text of the identifier token
											result=self.newToken(IdentifierElementExpression(self.token.text,self.environment,self,self.debug,echo)) #,_tokenchar)) # have it use the same debug level!!!
											""" MDH@09SEP2017: don't know why it was added here BEFORE: replacing:
											self.endToken() # have to do this explicitly here because I removed it from newToken() (and into addToken())
											result=self.newToken(IdentifierElementExpression(tokentext,self.environment,(None,self.debug)[],self,_tokenchar)) # have it use the same debug level!!!
											"""
											# MDH@18SEP2017: we DO want to start a subexpression!!!! _tokenchar=None # prevents creation of an expression below
										else:
											self.error="Cannot index a variable which value (of type "+str(type(identifiervalue))+") is not a list."
									else:
										self.error=_tokenchar+" not allowed behind a non-existing variable."
							else:
								self.error=_tokenchar+" not allowed behind a literal."
						if self.error is None and _tokenchar is not None:
							result=result.addToken(0,_tokenchar,echo) # MDH@18SEP2017: replacing self. by result. to the right of =
					elif _tokenchar in ts:
						# starting a string literal is not allowed in most situations because most operators do not operate on string literals
						# basically a string literal can only occur behind the + and * binary operator and the comparison operators
						# or the assignment operator, so that's + *	 < <= > >= != == and =, and the rest is prohibited
						# and also not behind any of the signs
						if abs(tokentype)>=SIGN_TOKENTYPE: # everything starting at signs can never precede a string literal
							self.error="String literal not allowed behind token of type "+getTokentypeRepresentation(tokentype,True)+"!"
						elif tokentype!=0: # this leaves the operators
							# only the first four unfinished operator are acceptable i.e. < or > or = or * but not the rest i.e. & | / and %
							# we might consider ending the operator token if need be so that all have the same type
							# alternatively, it's easiest to just look at the token text
							# which should be < > = * + (as single character operators) or <= >= == != which is anything that ends with =
							tokentext=self.token.getText()
							if tokentext[-1]!="=" and tokentext!="<" and tokentext!=">" and tokentext!="+" and tokentext!="*":
								self.error="String literal not allowed behind operator "+tokentext+"."
						if self.error is None:
							self.addToken(SINGLEQUOTED_TOKENTYPE+ts.index(_tokenchar),_tokenchar,echo)
					elif _tokenchar==periodchar: # MDH@12AUG2017: also a character that we can deal with pretty easily
						# MDH@27AUG2017: until now we did NOT accept .. as binary operator but now we do (replacing : which became another operator altogether)
						#								 which means that it might already be an operator in it's own right
						#								 all the situations where . turns into .. we have dealt with before what we used to have (i.e. abs(tokentype)<=SIGN_TOKENTYPE)
						# with periodchar also being the list concatenation binary operator
						# let's be liberal about it and allow it in identifiers as well
						# allowed to start a number literal, so no error if behind an operator
						if tokentype==OPERATOR_TOKENTYPE and self.token.getText()==periodchar:
							self.token.add(periodchar).discontinued() # definitely done with the operator!!!
						elif tokentype==REAL_TOKENTYPE and self.token.getText().endswith(periodchar): # MDH@27AUG2017: we thought the previous period created a real, but it shouldn't
							# it's going to be difficult to remove the period out of the assumed real number literal
							if self.token.backspace() is not None: # i.e. remove the last token (which is the decimal separator)
								# we can go one left on the screen
								if echo: # too bad we have to do that here!!
									userInputLine.removeLastCharacter(True)
								self.addToken(OPERATOR_TOKENTYPE,periodchar,echo).add(periodchar).discontinued()
							else: # backspace() on the token failed somehow...
								self.error=self.token.getError()
						elif abs(tokentype)<=SIGN_TOKENTYPE: # behind a unary or binary operator (or when tokentype equals 0 at start of expression)
							# starts a number literal immediately BUT only with a zero in front of it
							# NOTE I cannot use our special trick to indicate an automatic insert here (i.e. by putting it in the suffix)
							self.addToken(INTEGER_TOKENTYPE,"0",echo).add(periodchar)
						elif tokentype==INTEGER_TOKENTYPE: # in an integer, thus a number literal continuation
							########self.token.setType(REAL_TOKENTYPE) # switch over to being a number MDH@27AUG2017: the token should now take care of switching to REAL_TOKENTYPE!!!
							self.token.add(_tokenchar)
						elif abs(tokentype)>=IDENTIFIER_TOKENTYPE or abs(tokentype)==EXPRESSION_TOKENTYPE: # in/behind an identifier or expression, as list concatenation operator
							# MDH@25AUG2017: if we use the period as list concatenation operator as well, the current token needs to evaluate to a list
							#								 the question is whether we actually want to evaluate what's in front of this thing here
							self.addToken(OPERATOR_TOKENTYPE,_tokenchar,echo) #### MDH@27AUG2017: do NOT discontinue because another period character defines the .. operator!!!!.discontinued()
							#### replacing allowing the period as part of the identifier: self.token.add(_tokenchar)
						else:
							self.error="Period not allowed here."
					elif _tokenchar==declarationchar: # MDH@31AUG2017: also quite easy to interpret, as it's only allowed behind an identifier that is not a function name
						if abs(tokentype)<IDENTIFIER_TOKENTYPE:
							self.error="The declaration operator needs to be preceded by a variable name."
						elif self.functionExists(self.token.getText()):
							self.error="The declaration operator cannot follow a function name, a variable name is required."
						else:
							self.addToken(OPERATOR_TOKENTYPE,_tokenchar,echo).discontinued() # nothing else goes
							result=self.addToken(0,"",echo).flagAsDeclared() # mark as being declared, so we can end it with Enter
					else: # not the start (end) of string literal, the start or end of a subexpression, whitespace
						# ALL CODE ABOVE SHOULD BE SELF_CONTAINED BECAUSE ALL CODE BELOW FIRST CHECKS CONTINUATION FOLLOWED BY CREATING NEW TOKENS
						# it's probably best to deal with some of the possible input characters first and determine when they are not allowed
						# you can typically NOT start a string literal in a lot of places e.g. there are not very many operations allowed on it
						# NOTE do NOT forget to end any current token (this would be when the token type is positive)
						if abs(tokentype)>0 and abs(tokentype)<=OPERATOR_TOKENTYPE: # behind a binary operator (if an unfinished single-character operator this might be the second character)
							# MDH@05SEP2017: review of how to deal with the entered token character
							#								 ok, we want to know whether the current token character will end this operator if it is not yet finished
							#								 1. TOKENCHAR COULD CONTINUE THE UNFINISHED BINARY OPERATOR IE BE PROMOTED TO THE TWO-CHARACTER BINARY OPERATOR
							if tokentype>0: # the token character can still be part of this operator in which case we add it and None it
								operatortext=self.token.getText() # what the operator would become
								# can this be the second order character????
								secondoperatorchar=tokentype<OPERATOR_TOKENTYPE and o2.find(" "+operatortext+_tokenchar)>=0
								if secondoperatorchar:
									operatortext+=_tokenchar # the two-character binary operator
									# we should NOT allow using == as operator behind an identifier that has not yet been defined
									# although it's not always true that the == operator is applied to the value of this non-existing identifier per se
									if len(self.tokens)>1 and self.tokens[-2].getType()==IDENTIFIER_TOKENTYPE and not self.identifierExists(self.tokens[-2].getText()):
										self.error="It is not allowed to apply the equal comparison operator to a non-existing variable."
									elif tokentype<=2 and len(self.tokens)>1 and (operatortext=='<<' or operatortext=='>>') and self.tokens[-2].getType()==REAL_TOKENTYPE:
										# someone is trying to apply the shift operator to a real number
										self.error="It is not possible to shift a real number."
									else:
										if self.token.add(_tokenchar) is not None:
											_tokenchar=None
											# is this operator shortcuttable???? if not discontinue the token (we can still have whitespace after it!!!
											if operatortext[-1]==assignmentchar or operatortext=='||' or operatortext=='&&' or operatortext=='..':
												self.token.discontinued()
												tokentype=-tokentype
										else:
											self.error="Failed to create two-character operator "+operatortext+"!"
								elif _tokenchar==assignmentchar and (self.tokens[-2].getType()==IDENTIFIER_TOKENTYPE or (self.tokens[-2].getType()==EXPRESSION_TOKENTYPE and isinstance(self.tokens[-2],IdentifierElementExpression))) and operatortext[-1]!=assignmentchar and operatortext!='||' and operatortext!='&&' and operatortext!='..': # yes, the shortcutter
									# MDH@24SEP2017: BUG FIX an IdentifierElementExpression should also be considered an 'identifier' to which one may assign
									if self.token.add(_tokenchar) is not None:
										_tokenchar=None
										self.token.discontinued()
									else:
										self.error="Failed to shortcut operator "+operatortext+"!"
								else: # cannot be a continuation of the operator
									self.token.discontinued()
								# promote the operator if no errors occurred because every unfinished binary operator also is an operator in its own rights
								if self.error is None:
									# anything left to do??????
									if _tokenchar is not None: # no error, and _tokenchar not consumed yet
										if _tokenchar in s or _tokenchar in soro: # a unary operator
											# add the unary operators
											self.addToken(SIGN_TOKENTYPE,_tokenchar,echo).discontinued()
											_tokenchar=None # don't append again!!
										# any character that unambiguously starts a binary operator should be prohibited
										# any other character either in a, A, d, (, ), ' " is allowed
										elif _tokenchar in os or _tokenchar in o:
											if _tokenchar!=assignmentchar: # TODO not very neat that = is also in os whereas it can also be a soro
												if secondoperatorchar:
													self.error="It is not allowed to separate operator characters."
												else:
													self.error="Binary operator "+(("(start) ","")[_tokenchar in o])+_tokenchar+" not allowed behind operator "+operatortext+"."
								if self.error is None:
									if tokentype<OPERATOR_TOKENTYPE:
										self.token.setType(OPERATOR_TOKENTYPE)
						elif abs(tokentype)==INTEGER_TOKENTYPE or abs(tokentype)==REAL_TOKENTYPE: # in/behind a number
							# it's better to only allow digits (periods and whitespace already handled above)
							if not _tokenchar in d: # anything not a digit will discontinue the number
								# but not everything is allowed
								# - anything that can start an identifier is NOT allowed
								# - signs are not allowed
								# - opening parenthesis are not allowed
								# this leaves any operator character which is allowed, closing parenthesis (already considered before)
								if not _tokenchar in o and not _tokenchar in os and not _tokenchar in soro:
									self.error=_tokenchar+" not allowed behind a number."
								else: # apparently allowed in which case we need to discontinue the number literal, to make the character start a new token
									self.token.end() # MDH@24AUG2017: instead of discontinuing the token (which would mean that it cannot be continued anymore, which it can, we end it!!!!
							elif tokentype<0:
								self.error="Number cannot be continued this way: all digits need to be adjacent."
						elif abs(tokentype)>=IDENTIFIER_TOKENTYPE: # in an identifier
							# anything not alphanumeric or digits ends the identifier
							# but you cannot start another value
							if not _tokenchar in a and not _tokenchar in A and not _tokenchar in d: # we are allowed to continue an active identifier with a, A or d but not when in whitespace!!!
								# unless the new token is the assignment operator
								# NOTE we have to perform the check again when registering the == two-character comparison operator (because then the test will fail!!!)
								# MDH@31AUG2017: tokenchar equal to the declarationchar already taken care of above (removed here)
								tokentext=self.getLastTokenText()
								if self.functionExists(tokentext): # a function name, and only ( is basically allowed behind it
									if not _tokenchar in ls:
										self.error="Function "+tokentext+" should now be applied to an argument (inside parentheses)."
								elif not self.identifierExists(tokentext): # MDH@30AUG2017: same here, allow for variables initialized in this expression before
									# if this identifier is used as value, it should NOT be accepted here and now...
									# i.e. basically you can only assign a value to it, i.e. it should be the first token in the expression
									# which still allows one to start any subexpression with a variable assignment like in (a=2)+(b=3)
									# MDH@12AUG2017: let's allow chaining assignments that would be neat
									if len(self.tokens)>1 and self.tokens[-1].getText()==assignmentchar: # something in front of this identifier that doesn't exist yet is not allowed, even if it's a function or operator as
										self.error="You cannot use the value of variable "+tokentext+" until after a value was assigned to it."
									elif _tokenchar==assignmentchar: # the entered token character is the assignment character which is the only operator we allow on a non-existing identifier
										if self.parent is not None:
											self.parent.initializesIdentifier(tokentext)
										self.addToken(OPERATOR_TOKENTYPE,assignmentchar,echo).discontinued() # thus allowing whitespace but NOT another = or : sign!!!
										_tokenchar=None
									else:
										self.error="You cannot use variable "+tokentext+" in computations until after declaring it or assigning a value to it."
								# here we not just finish the token but end it (so it will be appended!!!)
								if self.error is None:
									if _tokenchar is not None: # assignment char behind a non existing identifier
										self.token.end() # MDH@24AUG2017: given that the token can still be continued, we end it (which should ALSO let self.getTokentype() return a negative value
							elif tokentype<0: # apparently in whitespace
								self.error="Identifier or number not allowed behind identifier."
						# if no error detected the tokenchar still might start a new token
						# NOTE whitespace already processed at the top level
						if self.error is None and _tokenchar is not None:
							# NOTE we might have negated the tokentype we ended, so we can still know what it was
							# NOTE we NOW always have a self.token which is the token that has finished but is not yet added to self.tokens!!
							tokentype=self.setTokentype(self.getTokentype()) # due to the possilbity of tokens finishing we have to redetermine the current token type
							########write("{"+str(tokentype)+"}")
							if tokentype<=0: # i.e. the given character starts a new token BUT this can be an operand or an operator
								# we can not create the token until we actually know the type
								# because the type determines the color in which the token character that is added is displayed
								# it's easiest to check afterwards whether or not an error occurred and if not create the token
								#######self.token=Token(???????).add(tokenchar)
								# because we introduced o (removing these single-character operators from os), we take care of these here and now
								# any two-character operator should have ended by now (so we'd have -8 as self.tokentype)
								# start of a two character operators???
								osindex=os.find(_tokenchar)
								########output("\n###"+str(osindex)+"###")
								# NOTE ! is no longer the first character in os, as it was moved over to soro
								#			 this makes it a little easier to deal with the os stuff because it's NEVER a sign operator
								#			 BUT it complicates the sign stuff a bit now
								# NOTE a special situation is the ! which is NOT a binary operator but an acceptable unary operator (otherwise should be followed by = which we could append immediately?)
								if osindex>=0: # starts a two-digit binary operator, only the first can also be a unary operator (!)
									# we have to take special care in the case when we're behind a string literal
									# NOTE that we take care of the equal to operator BEFORE addressing the string literal
									#			 so that we do NOT end up with trying to assign to a string literal
									# I guess 0 and -9 should be followed by an operand and NOT the start of an operator unless it's a unary operator
									if tokentype+OPERATOR_TOKENTYPE!=0 and tokentype+SIGN_TOKENTYPE!=0: # not behind a binary or unary operator
										# if the given token is the assignment operator but not behind an identifier we may append the second equal sign (to indicate comparison)
										# as this is the only possible next character to enter
										if tokentype==0: # binary operator cannot start an expression
											# MDH@27AUG2017: let's allow starting with the equal soro operator
											if osindex==0: # TODO in what other situations is using = as unary operator allowed as well??????
												self.addToken(SIGN_TOKENTYPE,_tokenchar,echo).discontinued()
											else:
												self.error="Can't start with an operator."
										elif _tokenchar==assignmentchar and self.tokens[-1].getType()<IDENTIFIER_TOKENTYPE: # not an assignment
											# unless, we're behind an identifier element expression
											if self.tokens[-1].getType()!=EXPRESSION_TOKENTYPE or not isinstance(self.tokens[-1],IdentifierElementExpression):
												# force equal is comparison operator
												# if we want to be able to undo the entire token with backspace
												# we move the second token character directly in the 'whitespace' suffix so we can recognize that situation
												self.autoinserted=_tokenchar # MDH@21SEP2017: expose any auto inserted character!!!
												self.addToken(OPERATOR_TOKENTYPE,_tokenchar+_tokenchar,echo).discontinued() # instead of 'ignoring' the second character, we put both in ONE token char and discontinue the lot
												if echo:
													beep()
												### replacing: self.newToken(OPERATOR_TOKENTYPE,_tokenchar,_output).add(_tokenchar).discontinued()
											else: # get this assignment operator appended
												tokentype=self.setTokentype(osindex+1)
											######self.token.end() #### replacing: tokentype=self.setTokentype(self.tokenends()) # we'd let self.tokenends() return the current token type (as a result of ending the new token!)
										elif (tokentype+SINGLEQUOTED_TOKENTYPE==0 or tokentype+DOUBLEQUOTED_TOKENTYPE==0) and (osindex==0 or osindex>3): # binary operator behind a string literal
											self.error="Not allowed to apply the "+_tokenchar+" operator to a string literal."
										else: # we should wait for the second operator character (if any)
											# do NOT allow using the power operator on a string literal
											if (tokentype+SINGLEQUOTED_TOKENTYPE==0 or tokentype+DOUBLEQUOTED_TOKENTYPE==0) and osindex==3: # applying *
												# NOTE here we do not insert characters ourselves, therefore no need to remember
												self.addToken(OPERATOR_TOKENTYPE,_tokenchar,echo).discontinued() # cannot be continued...
											else:
												tokentype=self.setTokentype(osindex+1)
									else: # behind binary or unary operator
										if osindex==0: # assignment (equal) character
											self.addToken(SIGN_TOKENTYPE,_tokenchar,echo).discontinued()
										else:
											self.error="Operator not allowed behind operator or sign."
								elif _tokenchar in o: # a single-character binary operator
									# not allowed behind another binary operator
									if tokentype==0:
										self.error="Can't start the expression with an operator."
									elif tokentype+OPERATOR_TOKENTYPE!=0:
										if tokentype+SINGLEQUOTED_TOKENTYPE==0 or tokentype+DOUBLEQUOTED_TOKENTYPE==0:
											self.error="Operator "+_tokenchar+" cannot be applied to a string literal."
										else:
											tokentype=self.setTokentype(OPERATOR_TOKENTYPE)
									else:
										self.error="Operator not allowed behind operator."
								elif _tokenchar in s: # a single-character unary operator
									tokentype=self.setTokentype(SIGN_TOKENTYPE)
								elif _tokenchar in soro: # a unary or binary operator (i.e. ! or - or +) depending on where it's located
									# BUT - and + can also be used as binary operator (to make things simple!!!)
									#			 so we have to do something different when it's the binary operator
									if tokentype!=0 and tokentype+OPERATOR_TOKENTYPE!=0 and tokentype+SIGN_TOKENTYPE!=0: # NOT behind a operator (or nothing) right now
										soroindex=soro.index(_tokenchar)
										if soroindex==0: # this would be the two-character unequal to operator to which we may automatically add the equal character
											# TODO we might decide not to auto-append the = character of the unequal to operator
											# we now create a token with a single tokenchar containing both token, so they will be removed as a whole (whether or not that is a good idea????)
											self.autoinserted=assignmentchar # MDH@21SEP2017: expose to the outside what was auto inserted...
											self.addToken(OPERATOR_TOKENTYPE,_tokenchar+assignmentchar,echo).discontinued() # todo more likely the equal-to-character
											if echo: # interactive mode
												beep() # inform user of something special happening
										else: # possibly - or + binary operator
											if (tokentype+SINGLEQUOTED_TOKENTYPE==0 or tokentype+DOUBLEQUOTED_TOKENTYPE==0) and soroindex==1: # applying - not +
												self.error="Not allowed to apply the - operator to a string literal."
											else:
												tokentype=self.setTokentype(OPERATOR_TOKENTYPE) # I suppose I need this to make the processing below right (i.e. it uses the operator tokentype)
									else: # the character should be treated as a sign, in which case it suffices to set the (new) token type processed below
										tokentype=self.setTokentype(SIGN_TOKENTYPE) # what comes after the sign determines what to do with it NO we need to end this unary operator token immediately as well (see below)
								elif _tokenchar in ts: # starts a string literal
									tokentype=self.setTokentype(SINGLEQUOTED_TOKENTYPE+ts.index(_tokenchar))
								elif _tokenchar in d: # a digit
									tokentype=self.setTokentype(INTEGER_TOKENTYPE) # starts an integer literal
								else: # accept to be an identifier start
									# we need an identifier that could exist (either as a function or as a variable) when not the first expression token
									# unless we allow chaining assigning identifiers (which I suppose we can do)
									if len(self.tokens)>0 and self.tokens[-1].getText()!=assignmentchar and not self.identifiersExistStartingWith(_tokenchar) and not self.functionsExistStartingWith(_tokenchar):
										self.error="No identifiers or functions exist starting with "+_tokenchar+" as is required here."
									else: # for now allowed
										tokentype=self.setTokentype(IDENTIFIER_TOKENTYPE)
								# if no error occurred _tokenchar was accepted, so ready to create the current token, and get _tokenchar echoed
								if self.error is None and tokentype>0:
									self.addToken(tokentype,_tokenchar,echo)
									# we can see in the previous M implementation (commented out above) that if the token type was set to 8 or 9 the token also ends
									if tokentype==OPERATOR_TOKENTYPE:
										# if the token cannot be continued with the shortcutter, discontinue the token
										tokentext=self.token.getText()
										if tokentext[-1]==assignmentchar or (len(tokentext)>1 and tokentext[0] in '.&|' and tokentext[-1]==tokentext[0]):
											self.token.discontinued()
									elif tokentype==SIGN_TOKENTYPE:
										self.token.discontinued()
							else: # continuation of a token
								self.token.add(_tokenchar)
			else: # expression no longer continuable, so put _tokenchar in the suffix (which means in the comment part of the main expression or closing parenthesis part of a subexpression)
				self.ignore(_tokenchar)
		except Exception,ex:
			if _tokenchar is None:
				self.error="ERROR: '"+str(ex)+"'"
			else:
				self.error="ERROR: '"+str(ex)+"' adding "+_tokenchar+"."
		# MDH@12SEP2017: updating the continuation if the token was accepted (i.e. when no error occurred)
		self.continuation=""
		if self.error is None and result is not None: # no error, and a valid result
			if len(self.tokens)>0 and self.tokens[-1].getType()==IDENTIFIER_TOKENTYPE: # we're in an (active) identifier
				self.continuation=getContinuation(self.tokens[-1].getText(),self.allidentifiernames)
		return result
	# useful to be able to obtain a list of all token characters to be appended to the user input line when choosing an existing expression to continue
	# NOTE we won't be needing getWritten() anymore soon, as we can suffice with using the token characters for rewriting the expression
	def getCharacters(self):
		characters=[]
		characters.extend(self.writtenprefix)
		characters.extend(self.text)
		for token in self.tokens:
			characters.extend(token.getCharacters())
		characters.extend(self.writteninfix)
		characters.extend(self.suffix)
		characters.extend(self.writtenpostfix)
		return characters
	def getWritten(self,_showcomment=True):
		# being a token means that there might be a writtenprefix (i.e. something written in front of the first character)
		written=self.getWrittenPrefix()+Token.getWrittenText(self) # the whitespace in front of the expression, but should I call getWritten??????
		if self.debug&32:
			written+=getColoredText(":0",33)
			ti=0
		#### replacing: result=self.text
		for token in self.tokens:
			written+=str(token)
			if self.debug&32:
				ti+=1
				written+=getColoredText(":"+str(ti),33)
		if _showcomment:
			written+=self.getWrittenInfix() # is this to be placed here?????
			written+=self.getWrittenSuffix() # replacing: self.suffix
			if self.debug&32:
				ti+=1
				written+=getColoredText(":"+str(ti),33)
		written+=self.getWrittenPostfix()
		return written
	def getSuffix(self,_showcomment):
		suffix=Token.getSuffix(self)
		if not _showcomment:
			commentpos=suffix.find(commentchar)
			if commentpos>0:
				suffix=suffix[:commentpos].rstrip()
			elif commentpos==0:
				suffix=''
		return suffix
	def getText(self,_showcomment=True):
		text=Token.getText(self) ### replacing: self.text
		for token in self.tokens:
			text+=token.getText()
		text+=self.getSuffix(_showcomment)
		return text
	def echo(self,_showcomment=True):
		# what we'd want is to have the main expression rewritten in this case, so we have to find the top expression (that has no parent)
		expression=self
		while expression.parent is not None:
			expression=expression.parent
		output(expression.getWritten(_showcomment))
	def __str__(self):
		return self.getText(False) # suppress any comment
	# override Token.getRepresentation() to return the representation of the list of tokens
	def getRepresentation(self):
		representation=""
		for token in self.tokens:
			representation+=" "+token.getRepresentation()
		return representation.strip()
	# if we pass the environment to getValue() which I suppose should then better be called evaluate or evaluatesTo we should ascertain that any subexpression
	# that we push on elements actually wraps the expression in an ExpressionEvaluator
	# that way getOperationResult() and Function.getValue() never sees any expression that does NOT know it's environment
	# MDH@05SEP2017: passing the execution environment to getValue() is not such a bad idea, although this would mean that we cannot use getValue() without it
	#								 in most cases the evalution environment will be the same as the creation environment as an expression is typically created and immediately executed
	#								 therefore: the default is to NOT have to specify an environment in the call to getValue()
	def getValue(self): # MDH@07Sep2017: you can always check self.value by requesting the value and if not None, NOT call evaluatesTo() if you want to!!!
		return self.value
	def setValue(self,_value): # MDH@12SEP2017: Actually only allowed when a ReturnException is thrown by the expression
		self.value=_value
	# MDH@07SEP2017: getValue() renamed to evaluatesTo, so we can use getValue() to request the value computed
	def evaluatesTo(self,_environment=None):
		#####note("Value of '"+self.getText()+"' requested!")
		self.value=None
		self.error=None
		if not self.isEmpty():
			evaluationenvironment=(self.environment,_environment)[_environment is not None]
			# MDH@05SEP2017: we can define the while, for, if and eval 'function' calls here, as they need their execution environment
			def getEvalResult(arguments):
				result=list()
				if len(arguments)>0:
					for argument in arguments:
						# we need the text representation of the argument's value
						argumenttext=dequote(getText(argument.evaluatesTo(evaluationenvironment)))[0] # dequoting is essential!!!
						if not isinstance(argumenttext,str) or len(argumenttext)==0:
							result.append(undefined)
						else:
							result.append(getExpressionValue(argumenttext,evaluationenvironment))
				return result
			def getWhileResult(_arglist):
				result=list()
				if len(_arglist)>1: # we really need two arguments here
					condition=_arglist[0] # or we might pop this last argument
					if isinstance(condition,Expression):
						whilebody=_arglist[1:]
						# NOTE: we can force computation of the value (as we should), by passing True as second argument!!!
						while 1:
							conditionvalue=condition.evaluatesTo(evaluationenvironment)
							######note("Value of condition '"+str(condition)+"': '"+str(conditionvalue)+"'...")
							if conditionvalue!=1: # everything not equal to 1 should be considered false!
								break
							bodyvalues=[bodyexpression.evaluatesTo(evaluationenvironment) for bodyexpression in whilebody]
							########note("Value of body '"+str(whilebody)+"': '"+str(bodyvalues)+"'...")
							result.append(bodyvalues)
					else:
						note("Please report the following bug: The condition in the while loop is not an expression, but of type "+str(type(_arglist[0]))+"!")
				return result
			def getForResult(_arglist):
				result=list()
				if len(_arglist)>2:
					forindexexpression=_arglist[0]
					# NOTE any argument should always be an expression, which should create the identifier mentioned in it
					#			 now, if it is not a single token in it of type identifier
					if isinstance(forindexexpression,Expression): # which it should be
						#######note("Evaluating for loop range '"+str(_arglist[1])+"'.")
						forindexvalues=_arglist[1].evaluatesTo(evaluationenvironment)
						if isIterable(forindexvalues):
							# it's MORE convenient to ALWAYS create a new environment, with the for index identifier as identifier
							if len(forindexexpression.tokens)==1 and forindexexpression.tokens[-1].getType() in (IDENTIFIER_TOKENTYPE,VARIABLE_TOKENTYPE):
								forindexidentifiername=forindexexpression.tokens[-1].getText()
								forindexidentifier=Identifier(forindexidentifiername)
								########note("For index identifier: '"+forindexidentifier.getName()+"'.")
							else:
								forindexidentifier=None
							# create the for index environment BUT then the problem is that all variables declared in the for loop are local to the for loop and lost afterwards!!!
							# which means that whatever is assigned to in the for loop should already exist!!
							if forindexidentifier is not None:
								forindexenvironment=Environment(forindexidentifiername,evaluationenvironment).addIdentifier(forindexidentifier)
							else: # just execute in the current 'global' environment
								forindexenvironment=evaluationenvironment
							# do we have a for index identifier????
							# NOTE we might consider leaving the loop if it's value changed within the loop
							forbodyexpressions=_arglist[2:]
							for forindexvalue in forindexvalues:
								# update the value of the forindex identifier (if any)
								if forindexidentifier is not None:
									forindexenvironment.getIdentifier(forindexidentifiername).setValue(forindexvalue)
									###########forindexidentifier.setValue(forindexvalue) # this is a bit of an issue
								forbodyvalues=[forbodyexpression.setImmediatelyExecutable(True).evaluatesTo(forindexenvironment) for forbodyexpression in forbodyexpressions] # evaluate the remaining arguments
								######note("For body values: "+str(forbodyvalues)+".")
								if not isIterable(forbodyvalues) or len(forbodyvalues)!=1:
									result.append(forbodyvalues)
								else: # a single result
									result.append(forbodyvalues[0])
						else:
							note("Second for loop argument ("+str(forindexvalues)+") not a list.")
					else:
						note("Please report the following bug: The first for loop argument is not an expression, but of type "+str(type(_arglist[0]))+"!")
				return result
			def getIfResult(_arglist):
				# NOTE we might expand if a bit but making it a multiselector
				#			 i.e. the output value (typically 0 or 1) in a comparison selects the expression to evaluate and return
				result=list()
				conditionvalue=_arglist[0].evaluatesTo(evaluationenvironment)
				#######note("Condition '"+str(_arglist[0])+"' evaluates to '"+str(conditionvalue)+"'.")
				if isinstance(conditionvalue,(int,long)): # an acceptible outcome
					if conditionvalue!=0: # condition evaluates to True
						if len(_arglist)>1:
							result.append(_arglist[1].evaluatesTo(evaluationenvironment))
					else:
						if len(_arglist)>2:
							result.append(_arglist[2].evaluatesTo(evaluationenvironment))
				return result
			def getSwitchResult(_arglist):
				result=list()
				conditionvalue=_arglist[0].evaluatesTo(evaluationenvironment)
				if isinstance(conditionvalue,(int,long)): # an acceptible outcome
					# with the True and False clause switched, we should use ! to get the proper index
					# wrap around the condition value to be in the range [0,len(_arglist)-2]
					if conditionvalue>0:
						conditionvalue%=len(_arglist)-1
					if conditionvalue<0:
						conditionvalue=0
					result.append(_arglist[conditionvalue+1].evaluatesTo(evaluationenvironment))
				return result
			def getExistsResult(_arglist):
				# MDH@12SEP2017: should return 1 if ALL arguments denote existing identifiers			result=1
				for arg in _arglist: # each argument should be an expression
					# the arguments needs to have exactly one token or all tokens need to be expressions
					if len(arg.tokens)==0:
						continue
					# with multiple arguments, or a single expression token, just call getExistsResult on all tokens...
					tokentype=arg.tokens[-1].getType()
					if len(arg.tokens)>1 or tokentype==EXPRESSION_TOKENTYPE:
						return getExistsResult(arg.tokens)
					# a single token in this argument, needs to be either an expression or an identifier that exists
					if tokentype!=IDENTIFIER_TOKENTYPE or not evaluationenvironment.identifierExists(arg.tokens[-1].getText()):
						return 0
				return 1 # success
			# best not to end with a period, given the possible color showing the last token
			try:
				if self.debug&8:
					valueText=self.getRepresentation()
				# MDH@18AUG2017: an expression with no tokens will return the undefined identifier!!!
				#								 in order to be able to assign this we need to return the empty list!!!
				if len(self.tokens)>0 or len(self.text)==0 or not (self.text[0] in ls): # not an empty subexpression
					# MDH@15AUG2017: instead of keeping separate list to store the operators and arguments it's a good idea to create an expression that will contain the end result
					#								 of the evaluation of the tokens by applying the functions and binary operators
					#								 the point is that if we allow argument lists with multiple arguments (=values), it's easiest to store the list of these arguments in a single argument
					#								 to which the function is to be applied, then the function has to take care of processing the list and apply itself to the number of arguments it needs
					########evaluatedexpression=Expression() # the expression to populate with the values of the successive tokens and operators to apply
					def getElementValue(_element):
						######note("Get the value of element "+str(_element)+" of type "+str(type(_element))+"...")
						if isinstance(_element,list):
							########note("ERROR: the element is a list, which should NOT happen!")
							return map(getElementValue,_element)
						if isinstance(_element,Expression):
							#######note("Evaluating expression "+str(_element)+".")
							elementvalue=_element.evaluatesTo(evaluationenvironment)
						else:
							elementvalue=getValue(_element)
						if self.debug&8:
							note("Value of "+str(_element)+" of type "+str(type(_element))+": '"+str(elementvalue)+"' of type '"+str(type(elementvalue))+"'.")
						return elementvalue
					elements=[] # arguments (functions and values) and operators intertwined
					# as we will be applying functions to arguments multiple times, we create a subfunction to do that for us
					def applyFunctions():
						# 1. POP OFF ALL ARGUMENTS
						arguments=[] # the list of arguments, there should be at least one
						while len(elements)>0 and not isinstance(elements[-1],Operator) and not isinstance(elements[-1],Function):
							arguments.insert(0,elements.pop())
						# 2. APPLY ALL FUNCTIONS
						while len(elements)>0 and isinstance(elements[-1],Function):
							function=elements.pop().setDebug(self.debug) # make the function take over
							if self.debug&8:
								note("Applying function "+str(function)+" to arguments "+str(arguments)+".")
							# MDH@02SEP2017: we cannot apply a function to arguments that are expressions
							#								 as the function does NOT know the environment
							#								 so any expression needs to be evaluated first
							# TODO because we pre-evaluate function should NOT evaluate anymore!!!!!!
							# MDH@04SEP2017: that is SO wrong because we already took care of converting
							#								 Expression instances to ExpressionEvaluator instances which
							#								 SO know in which environment to evaluate the expression
							if function.getIndex()==9 or function.getIndex()==21: # = or eval
								arguments=getEvalResult(arguments)
							elif function.getIndex()==100: # while
								arguments=getWhileResult(arguments)
							elif function.getIndex()==210: # for
								arguments=getForResult(arguments)
							elif function.getIndex()==200: # if
								arguments=getIfResult(arguments)
							elif function.getIndex() in (201,202,203): # select/case/switch
								arguments=getSwitchResult(arguments)
							elif function.getIndex()==23: # exists
								arguments=getExistsResult(arguments)
							else: # application of a normal function (directly passing in the evaluated arguments
								arguments=function.getValue(map(getElementValue,arguments)) ###### NO NO NO map(getElementValue,arguments))
							# this would be an annoying step, we should let the function do that?????
							if not isIterable(arguments):
								arguments=[arguments]
							if self.debug&8:
								note("Result of the function application: "+str(arguments)+".")
						# 3. PUSH THE RESULT (LIST) BACK ON THE elements STACK
						# NOTE we need to 'delist' arguments
						# the first step would be to remove the undefined values at the end
						if isinstance(arguments,list):
							if len(arguments)==1: # a single argument (which might be undefined though)
								arguments=arguments[0]
						elements.append(arguments) # which might be an empty list...
					# process the tokens one at a time
					# if we take the priorities into account
					tokenindex=0
					if self.debug&16:
						note("Number of tokens to process: "+str(len(self.tokens))+".")
					for token in self.tokens:
						tokenindex+=1
						if token is None:
							continue
						tokentype=token.getType()
						tokentext=token.getText()
						if self.debug&16:
							note("Processing token #"+str(tokenindex)+" of type "+getTokentypeRepresentation(tokentype)+": "+tokentext+"...")
						if tokentype==SIGN_TOKENTYPE: # a unary operator (! or - or ~ or + and now even =)
							# any token is either from s or soro
							sindex=s.find(tokentext)
							if sindex>=0: # ~
								elements.append(Function(7+sindex))
							else: # ! or = or - or +
								elements.append(Function(7+len(s)+soro.index(tokentext)))
						elif tokentype==OPERATOR_TOKENTYPE: # the token represents a binary operator (which might be the assignment operator =)
							# MDH@15AUG2017: we should apply any function to any argument (list) in front of this operator to end up with a single argument to which the operator is to be applied
							#								 so we end up with operand operator operand operator etc. (all odd elements will be operators and all even elements will be operands)
							applyFunctions()
							# determine whether or not we can apply the previous operator now which should be the before last element on the elements stack now (if any)
							# we cannot apply an operator immediately until we encounter another operator with equal or lower precedence
							# which basically means that we can at most apply the PREVIOUS operator i.e. the last one in operators
							precedence=getOperatorPrecedence(tokentext)
							if self.debug&16:
								note("Precedence of operator "+tokentext+": "+str(precedence)+".")
								if len(elements)>2:
									note("Precedence of "+str(elements[-2])+": "+str(elements[-2].getPrecedence())+".")
							while len(elements)>2 and elements[-2].getPrecedence()<=precedence: # a lower (=better) or equal precedence, i.e. we should apply that operator to the last two arguments on the stack
								try:
									elements.append(evaluationenvironment.getOperationResult(elements.pop(),elements.pop().getText(),elements.pop())) # pretty neat to be able to do it this way (but I rewrote getOperationResult to accept the 2nd argument first!!!)
								except Exception,ex:
									self.error=ex
									break
							# remember this operator and its associated precedence
							# MDH@15AUG2017: I need to be able to distinguish operators from operands
							elements.append(Operator(tokentext,precedence))
							# MDH@24AUG2017: it's a bit dangerous to assume that the assignment will succeed, in which case the token can be made continuable again
							if tokentext==assignmentchar and not token.isContinuable():
								token.undiscontinued()
						else: # not an operator
							argument=None
							if tokentype==INTEGER_TOKENTYPE: # an integer
								argument=getInteger(tokentext) # we've allowed using ~ as sign TODO make a function out of it
							elif tokentype==REAL_TOKENTYPE: # a float
								argument=float(tokentext)
							elif tokentype==EXPRESSION_TOKENTYPE: # a subexpression which we should evaluate now
								argument=token # MDH@05SEP2017: now again allowed to pass along token of type expression!!!!
							elif tokentype==IDENTIFIER_TOKENTYPE: # some identifier, either a function or an identifier
								# although an identifier can also be a function, we allow using function names as identifiers, so it depends on what's behind the identifier name
								# whether it's a function or identifier
								# on the other hand if there's nothing behind the identifier it's an existing identifier
								# so if it's an existing identifier assume it's an identifier, and correct when an opening parenthesis comes next
								function=self.getFunction(tokentext)
								if function is not None:
									argument=function # remember the function until we have the argument to apply it to
								else: # identifier that does not yet exist
									argument=evaluationenvironment.getIdentifier(tokentext)
							else: # anything else (which is stored as text)
								argument=getValue(tokentext) # like an expression
							# MDH@15AUG2017: if we allow as many arguments as possible, we cannot immediately apply the functions to an argument, not until we come across an operator
							#								 as soon as we come across the operator we should the functions to ALL arguments
							elements.append(argument)
						if self.debug&16:
							for element in elements:
								note("Element: "+str(element))
					# apply all operators left
					if self.error is None:
						# because we do not have an operator at the end we need to first apply functions
						while len(elements)>1:
							if self.debug&8:
								note("Evaluating: "+str(elements)+".")
							try:
								####note("Applying final functions!")
								applyFunctions()
								# the problem is that getOperationResult will receive expressions as well
								# which it sometimes must evaluate and sometimes not, so it needs an environment
								if len(elements)>2: # we should have at least an operator in front of it
									elements.append(evaluationenvironment.getOperationResult(elements.pop(),elements.pop().getText(),elements.pop()))
							except Exception,ex:
								self.error=ex
								#######note("ERROR: '"+str(ex)+"'!")
								break
					if self.error is None:
						if self.debug&8:
							note("Final result: "+str(elements)+".")
						if len(elements)==0: # we should end with one argument and no operators
							self.error="No operands left."
						elif len(elements)>1:
							self.error="Too few operators."
					########note("Elements: "+str(elements)+".")
					self.value=map(getElementValue,elements) # evaluate what's left
					# MDH@22SEP2017: we do NOT want to unlist a single result, which would mean that expressions enclosed in parenthesis return a list!!!!
					#								 alternatively, we might remove all None elements at the end so that a list would remain if only a single element (like Python does!)
					########note("Result value: "+str(self.value)+".")
					# MDH@22SEP2017: how about NOT delisting here, to honour the parentheses around the subexpressions?????
					#								 unless this is the topmost expression
					while isinstance(self.value,list) and len(self.value)==1:
						self.value=self.value[0]
					# MDH@22SEP2017: we can force to return a list by appending None elements (i.e. empty expressions), as Python does!!!
					if isinstance(self.value,list):
						while len(self.value)>0 and self.value[-1] is None:
							self.value.pop()
					if self.debug&8:
						output("\n\t"+valueText)
						write(" = ",0)
						if self.value is None:
							output("(Undefined)")
						else:
							output(str(self.value))
				else: # no tokens and a subexpression
					self.value=undefined.getValue()
			# the first argument might still have been left unevaluated, e.g. when a single identifier is typed!!!
			except Exception,ex:
				self.value=undefined
				######note("ERROR: '"+str(ex)+"'...")
				if self.error is None:
					self.error=ex
		return self.value
	def isEmpty(self):
		return len(self.tokens)==0
	def unendText(self): # called by self.undiscontinued() whenever the discontinuation is undone
		if len(self.tokens)>0:
			self.tokens[-1].unend()
		else: # very, very unlikely (unless someone does not put something between ( and ) which we might allow in the future though)
			Token.unendText(self)
	def removeLastToken(self):
		# return either itself if the new last token is not an expression, otherwise it returns that token
		self.tokens.pop()
		# replace the current token with the last token
		# which we should re-open for continuation if possible
		if len(self.tokens)>0:
			self.token=self.tokens[-1].unend()
			if isinstance(self.token,Expression):
				return self.token
		else:
			self.token=None
		return self
	def backspace(self):
		# MDH@01SEP2017: how about checking userInputLine first?????
		#								 because backspace() is recursive removing the last character should be done by the caller
		#								 otherwise sometimes multiple tokens would be removed (e.g. when removing end of expression character)
		#								 ASSERTION assumes that there are still characters on the current user input line
		#								 we shouldn't thrown an error just return None if we're at the start of the current user input line
		#								 ALSO it's better to not do any beeping here, as that's I/O to the user console
		self.error=None
		self.value=None # MDH@07SEP2017: after executing backspace() the value will need to be recomputed...
		result=self
		if self.isContinuable(): # not in the comment part
			if self.token is not None: # there is an token currently active
				# we should let the token do the backspace (given the recursive nature of tokens in an expression)
				# NOTE if we delete the last character in a token, we should also remove the token itself
				# NOTE now the problem is whether or not we should distinguish between a Token token or an Expression token
				#			 this way we need to make Token have an self.error as well (which we didn't have so far)
				if self.token.backspace() is None:
					self.error=self.token.getError()
				else: # backspace() successful, but the token could now be empty
					if self.token.isEmpty(): # the token is now empty, so should be removed from the expression
						self.removeLastToken()
					else: # now comes the interesting part
						if self.token.getType()==4: # just removed the second period of the .. operator
							if self.token.backspace() is not None: # remove the first period as well
								if self.token.isEmpty():
									# as we're adding the period below I have to remove it first
									userInputLine.removeLastCharacter(True)
									self.removeLastToken()
									# the integer in front of the .. should now become a (continuable) real!!
									self.token.unend()
									# we want to 'add' the period to the integer token BUT it should not be written because it's already visible
									self.token.add(periodchar) # will change the type to REAL_TOKENTYPE
								else:
									self.error="Failed to remove the .. operator!"
							else:
								self.error=self.token.getError()
						elif isinstance(self.token,Expression): # we've deleted a tokenchar in a subexpression, that must have been the closing parenthesis
							result=self.token # continue with the subexpression
			else: # somewhere in the prefix probably
				# NOTE as soon as we empty this (sub)expression we should move back to the parent expression if any, to take it from there
				#			 but we shouldn't call the backspace on self.token because we just removed the last token char on this (sub) expression
				if len(self.text)>0:
					self.text.pop()
				# have we emptied this (sub)expression
				if len(self.text)>0:
					self.text[-1].unend()
				elif self.parent is not None:
					#########result=self.parent # definitely
					# this is dangerous territory because if we removed the , separator just now that starts a new expression in a list, result should be that subexpression!!!
					# remove the last token (which is me), so it'll be ready to continue this token (or delete token characters of it)
					# we can solve that by making removeLastToken return either self or self.token (if the latter is an expression)
					result=self.parent.removeLastToken()
				else: # we've reached the end of the main expression, so nothing to remove!!!
					self.error="Please report the following bug: start of expression reached with characters left to delete on the user input line."
		else: # in the suffix (comment part)
			# NOT allowed to remove a newline token character
			if len(self.suffix)>0:
				self.suffix.pop()
				if len(self.suffix)==0: # comment character removed
					self.undiscontinued() # which will call unendText() on success (which we have to override to prevent Token.unendText() to unend the last tokenchar in self.text
				else:
					self.suffix[-1].unend()
			else:
				self.error="Please report the following bug: no comment characters left to remove."
		# update the continuation
		self.continuation=""
		if self.error is None and result is not None: # no error, and a valid result
			if len(self.tokens)>0 and self.tokens[-1].getType()==IDENTIFIER_TOKENTYPE: # we're in an (active) identifier
				self.continuation=getContinuation(self.tokens[-1].getText(),self.allidentifiernames)
		if self.error is not None: # any error should make result None for sure
			result=None
		return result
# MDH@17AUG2017: when an identifier is 'applied' to an expression the expression indicates an index
# such an expression behaves like any other expression except that it returns the value
class IdentifierElementExpression(Expression):
	def __init__(self,_identifiertext,_environment,_parent=None,_debug=0,_output=True,_tokenchar=None):
		Expression.__init__(self,_environment,_parent,_debug,_output) # no passing _tokenchar (yet)
		# copy all token characters over from the identifier token
		self.text=_identifiertext # use the text (the token characters representing the identifiers)
		if isinstance(_tokenchar,str):
			self.append(_tokenchar)
	def getIdentifier(self):
		return str(self.text)
	# an additional method to get at the value of this expression returns the index value
	"""
	# MDH@19SEP2017: essential to evaluate getIndexValue() in the evaluation environment
	#								 instead of the creation environment (which e.g. are different in a for)
	def getIndexValue(self,_environment):
		# MDH@18SEP2017: given that we can now have an index into a 'multidimensional' list
		#								 self.indexvalue could now evaluate to a list of indices
		#								 oh, in a for loop getIndexValue() might change!!!
		indexvalue=Expression.evaluatesTo(self,_environment)
		###note("Index expression '"+self.getText()+"' evaluates to '"+str(self.indexvalue)+"'.")
		return indexvalue
	"""
	def evaluatesTo(self,_environment):
		######note("Value of an element of "+str(self.identifiername)+" requested.")
		identifier=_environment.getExistingIdentifier(self.getIdentifier())
		if identifier is None:
			raise Exception("Identifier "+self.getIdentifier()+" vanished.")
		# help function to return the value at a given index (even when a list of indices)
		def getValueAtIndex(_value,_index):
			if not isinstance(_value,list):
				return undefined.getValue()
			if isinstance(_index,list):
				newvalue=list()
				for index in _index:
					newvalue.append(getValueAtIndex(_value,index))
				return newvalue
			if _index<0:
				_index+=(len(_value)+1)
			if _index<=0 or _index>len(_value):
				return undefined.getValue()
			return _value[_index-1]
		value=identifier.getValue() # which should be a list or string
		if not isinstance(value,list) and not isinstance(value,str):
			raise Exception("Value of variable "+self.getIdentifier()+" not cannot be indexed.")
		# convert any string into a list of string characters
		if isinstance(value,str):
			(text,quotechar)=dequote(value)
			value=[enquote(c,quotechar) for c in text]
		indexvalues=Expression.evaluatesTo(self,_environment) ##self.getIndexValue(_environment)
		if isinstance(indexvalues,list):
			for indexvalue in indexvalues:
				# replace value with the value at the given index
				value=getValueAtIndex(value,indexvalue)
		else: # a single index
			value=getValueAtIndex(value,indexvalues)
		return value
	def setValue(self,_value,_environment=None): # TODO do we need to know the environment here????
		environment=(_environment,self.environment)[_environment is None]
		identifier=environment.getExistingIdentifier(self.getIdentifier())
		if identifier is None:
			raise Exception("Identifier "+self.getIdentifier()+" vanished.")
		value=identifier.getValue() # the list of which elements are to be set
		def setValueAtIndex(_index):
			if isinstance(value,list) or isinstance(value,str): # we should be assigning to a list element
				if isinstance(_index,list):
					result=list()
					for index in _index:
						result.append(setValueAtIndex(index))
					return result
				if isinstance(_index,(int,long)): # index supposed to be an integer
					if _index==0: # prepend the given value
						value.insert(0,undefined)
						return 1 # the actual index of the element we changed
					if _index<0:
						_index+=(len(value)+1)
					if _index>0:
						while _index>len(value):
							value.append(undefined)
						result=_index
						value[result-1]=_value
						return result
			return undefined
		def getValueAtIndex(_index):
			if isinstance(value,list) or isinstance(value,str):
				if isinstance(_index,list):
					newvalue=list()
					for index in _index:
						newvalue.append(getValueAtIndex(index))
					return newvalue
				if isinstance(_index,(int,long)):
					if _index<0:
						_index+=(len(value)+1)
					if _index>0 and _index<=len(value):
						return value[_index-1]
			return undefined
		#######note("Identifier: "+str(identifier)+".")
		if not isIndexable(value):
			raise Exception("Variable "+self.getIdentifier()+" cannot be indexed: its value is not a list.")
		####note("Setting the element at index "+str(indexvalue)+" of "+self.identifiername+" with value "+str(value)+".")
		maxindex=len(value) # get the length of the list
		indexvalues=Expression.evaluatesTo(self,environment) ##self.getIndexValue(_environment)
		# typically the last index will do the actually assigning
		# and therefore it makes sense to start with popping that one off
		#########note("Index values: "+getText(indexvalues)+".")
		if isinstance(indexvalues,list):
			lastindex=indexvalues.pop()
			for indexvalue in indexvalues:
				value=getValueAtIndex(indexvalue)
			setValueAtIndex(lastindex)
		else:
			setValueAtIndex(indexvalues)
		Expression.setValue(self,_value) # we have to do as it needs to be returned by getValue()
		return self
# MDH@30AUG2017: if an expression is executed it executes within a certain 'environment' i.e. a set of variables constitute a state that is local
#								 this means that the getValue() that we used to have in Expression is to be moved over to the ExpressionEvaluator
#								 this way at any moment the same expression can be used in multiple expression executors at the same time all with different 'environments'
class ExpressionEvaluator:
	def __init__(self,_expression,_environment):
		self.expression=_expression
		self.environment=_environment
	def __str__(self):
		return str(self.expression)
	def getExpression(self):
		return self.expression
	def getEnvironment(self):
		return self.environment
	# because we know the 'parent' environment, when getValue is requested, we can pass that environment into the expression
	# at the moment that the expression is to be evaluated, which can pass it along to any subexpression that are evaluated 'below' it
	def getValue(self):
		expressionvalue=self.expression.evaluatesTo(self.environment)
		debugnote("Value of expression "+str(self.expression)+": "+str(expressionvalue)+"...")
		return expressionvalue
	def setValue(self,_value): # TODO do we need _environment here as well??????
		self.expression.setValue(_value,self.environment)
	def getIdentifier(self,_identifiername):
		return self.environment.getIdentifier(_identifiername)
	def deleteIdentifier(self,_identifiername):
		self.environment.deleteIdentifier(_identifiername)
"""
******************************************************************** M USER INTERFACE LOOP *********************************************************************
"""
# and here some additional utility functions
def writeagain(_expression):
	#####writeln("Write again!")
	writeprompt()
	# we might be in a subexpression, so we need to start all over
	expression=_expression
	while expression.parent is not None:
		expression=expression.parent
	expression.echo()
# a separate function to return the first non escaped character (that is acceptable as expression token)
# effectively ignoring all special key sequences
def getexprch():
	exprch=getch()
	while ord(exprch)==0x1B:
		sch=getch() # the second character which should be [
		if ord(sch)==0x5B: # CSI code sequence
			tch=getch()
			while ord(tch)<0x40 or ord(tch)>0x7E:
				tch=getch()
		else: # Non-CSI
			# keep reading until the ST - String terminator character
			while ord(sch)!=ord('\\'):
				sch=getch()
		beep()
		exprch=getch() # read the next keyboard character
	return exprch
def writeFunctions(_environment):
	write("Functions:")
	for functionname in _environment.getFunctionNames():
		write(" "+functionname)
	newline()
def writeVariables(_environment):
	write("Variables:")
	for variablename in _environment.getIdentifierNames():
		write(" "+variablename)
	newline()
def endFunctionCreation():
	global environment
	function=environment.endUserFunction()
	if function is not None: # done with creating the function
		# we have to move the expressions from the environment to the function to make it executable
		# wait a minute, no that's OK
		#### see endUserFunction()!!! function.setExpressions(environment.getExpressions()) # salvage the function expressions from the environment expression history
		note("End of defining function "+function.getName()+".")
		note("At the end of this trial execution the function-local variable values are:")
		valuestext=""
		identifiervalues=environment.getIdentifierValues(("M","functions","variables")) # not showing the implicit identifiers M, functions and variables
		for identifiername in identifiervalues:
			identifiervalue=identifiervalues[identifiername]
			valuestext+=" "+identifiername+"="+(getText(identifiervalue),"?")[identifiervalue is None]
		note(valuestext)
		environment=function.getHostEnvironment() # return to the parent environment (which is NOT the parent of the current environment when it's a standalone function)
		if environment.addFunction(function): # make it accessible!!!
			function.writeDefinition(environment.getFunctionsFilename())
		newline()
		writeFunctions(environment)
	else:
		writeerror("No function being created right now to end.")
# MDH@12SEP2017: we'll be needing continuation of user names and identifiers
def getContinuation(_id,_ids):
	continuation=""
	# 2. get all the longer names that start with the current input user name!!!
	matchingids=list()
	for id in _ids:
		if id.startswith(_id) and len(id)>len(_id):
			matchingids.append(id)
	# determine the number of additional characters that the matching user names have in common
	if len(matchingids)>0:
		#######write(str(len(matchingusernames)))
		i=len(_id) # the first position to compare that is present in at least one of the matching user names!!!
		while 1:
			charactertomatch=None
			allcharactersmatch=True
			for matchingid in matchingids:
				# if not available in this matching user name we cannot add this character
				if len(matchingid)<=i:
					allcharactersmatch=False
					break
				if charactertomatch is None:
					charactertomatch=matchingid[i]
				elif matchingid[i]!=charactertomatch: # too bad this one doesn't match
					allcharactersmatch=False
					break
			if not allcharactersmatch:
				break
			######output("Matching '"+charactertomatch+"'")
			continuation+=charactertomatch # another matching character...
			i+=1 # ready to test the next one
	return continuation
# MDH@06SEP2017: I've moved the 'login' to the control mode, so every session starts with an undefined user (i.e. anonymous)
currentusername=None
usernames=None
def writeUsageNotes():
	lnwrite("Please read the following usage notes")
	if len(currentusername)>0:
		write(", "+currentusername)
	write(".")
	lnwrite("\tM operates in either input mode, or control mode.")
	lnwrite("\tIn input mode you enter the expressions (aka formulas) to evaluate (aka compute).")
	lnwrite("\tIn control mode you can e.g. adapt M settings (e.g. debug level), login, or define a new function to create.")
	lnwrite("\tUse a backtick character (i.e. `) at the start of an expression to enter control mode.")
	lnwrite("\tThe control mode menu offers a list of options that can be selected with a single character.")
	lnwrite("\tWhen you're asked to answer a question (as opposed to selecting an option), always end with pressing the Enter key.")
	lnwrite("\tIn input mode, use Ctrl-C to cancel the current expression, Ctrl-D to end the function being created, or exit M.")
	lnwrite("\tM keeps track of all expressions entered, writes them to a file, and reads them on startup, so you can always use them again.")
	lnwrite("\tFor more information, read the M documentation (in M.pdf).")
defaultusername="" # means undefined (should NOT be None)
def setUsername(_username):
	if not isinstance(_username,str): # no change to the current user name!!!!
		return
	# if same user no change
	global currentusername
	if currentusername is not None and currentusername==_username:
		return
	if _username=="M":
		lnwrite("Name 'M' refused. There can be only one M, and that's me.")
		return
	if currentusername is not None and len(currentusername)>0:
		lnwrite("Bye, "+currentusername+". Thanks for using M!")
		newline()
	# the current user changed, the question is whether or not the working environment should be Menvironment???????
	# possibly Menvironment could be considered the global environment shared by all users but I'd say that not every user should be allowed to change it
	currentusername=_username
	# we have to start over with a new environment
	global environment,usernames,defaultusername
	if len(currentusername)>0:
		environment=Environment(currentusername,Menvironment)
		# register any change to file Musers if need be
		# a new user name?
		newuser=usernames is None or not currentusername in usernames
		if newuser:
			if usernames is None:
				usernames=list()
			usernames.append(currentusername)
			writeUsageNotes()
		else: # no, welcome back
			write("Good to see you again, "+currentusername+".")
		# if the default changed, update Musers file
		if currentusername!=defaultusername: # the current user name is not the registered default user name
			fuser=open(environment.getUsersFilename(),'w') # rewrite the user names to Musers
			if fuser:
				for username in usernames:
					if username==currentusername:
						fuser.write("*")
					else:
						fuser.write(" ")
					fuser.write(username+opsys.linesep) # MDH@03SEP2017: using the official line separator
				fuser.close()
				defaultusername=currentusername # assume success, so update the default user name to me!!!
			else:
				lnwrite("ERROR: Failed to update the Musers file! ")
				if newuser:
					writeln("You will need to register yourself by editing the Musers file manually.")
				else:
					writeln("You will not be recognized as the last (default) user, unless you mark your name in the Musers file with an asterisk yourself.")
		initializeEnvironment(environment)
	else: # use the global (M) environment, to which you can add functions shared by all projects!!!
		environment=Menvironment
def getUsername():
	# NOTE we're using the global currentusername but as long as we do not try to change it we do not need to declare it as global I think
	# allowing a user to logout by pressing Enter
	newuser=False # assume not a new user
	# use the last user that logged in as default for the user name
	usersfilename=environment.getUsersFilename()
	defaultusername="" # assume no default user name!!
	usernames=list()
	if opsyspath.exists(usersfilename):
		fuser=open(usersfilename,'r')
		if fuser:
			while 1:
				userline=fuser.readline().rstrip('\n\r')
				if len(userline)==0:
					break
				username=userline[1:]
				usernames.append(username)
				if userline[0]=='*':
					defaultusername=username
			fuser.close()
	else:
		lnwrite("Users filename '"+usersfilename+"' does not exist!")
	# I suppose we can show a list of user names!!!
	if len(usernames)>1:
		lnwrite("Registered users: ")
		for username in usernames:
			write(" "+username)
		write(".")
	# how can a user stop current input?????? I guess we can use Ctr-C to that purpose again
	newline()
	writeln("Restrictions: spaces are not allowed in the name, you cannot choose M as name.")
	writeln("Special keys: Ctrl-C: cancel, Tab: accept suggested text (in grey).")
	write("What is your name")
	# NOTE allow the current user to logout by pressing the Enter key immediately
	if len(currentusername)==0 and len(defaultusername)>0:
		write(" (default: "+defaultusername+")")
	write("? ")
	# allow the user to enter his/her name
	inputusername="" # what the user entered
	while 1:
		# 1. UPDATE AND SHOW ANY USER CONTINUATION FOR THE USER TO CHOOSE WITH TAB
		usercontinuation=getContinuation(inputusername,usernames)
		# write the new user continuation, replacing the current user continuation
		usercontinuationlength=len(usercontinuation) # remember the number of characters in the user continuation
		if usercontinuationlength>0:
			write(usercontinuation,DEBUG_COLOR)
			output("\033["+str(usercontinuationlength)+"D") # return to the cursor position
			hidecursor() # hide the cursor otherwise we won't see the first continuation character on the position where to input a character
		else:
			showcursor() # show the cursor so the user can see where (s)he's typing
		# 2. GET USER INPUT CHARACTER
		ch=getch()
		# 3. IF A TAB ACCEPT USER CONTINUATION
		if ord(ch)==9: # a tab indicates that the user wants to accept the continuation offered
			if len(usercontinuation)>0:
				output(usercontinuation) # overwrites automatically any visible continuation
				inputusername+=usercontinuation
			else: # no user continuation to write
				beep()
			continue
		# 4. REMOVE USER CONTINUATION IN CASE OF ANY OTHER INPUT THEN THE TAB CHARACTER
		if usercontinuationlength>0: # some continuation showing to remove?????
			write(" "*usercontinuationlength)
			output("\033["+str(usercontinuationlength)+"D") # return to the previous cursor position
		# 5. IF CANCEL OR ENTER DONE
		if ord(ch) in (3,4,10,13):
			break
		# 6. IF ACCEPTED INPUT (IE IF NOT A BLANK OR PERIOD OR BACKSPACE AT THE START OF THE LINE) PROCESS
		if ch!='.' and ch!=' ' and (ord(ch)!=127 or len(inputusername)>0): # some valid input character (do not accept blanks!!!)
			if ord(ch)==127: # backspace, to remove the last entered character
				inputusername=inputusername[:-1]
				output("\033[1D \033[1D") # this should do the trick, go back one position, write a blank and go back one position again
			else:
				inputusername+=ch
				output(ch)
		else: # backspace encountered on an empty input user name
			beep()
	# login canceled??
	if ord(ch)==3 or ord(ch)==4:
		lnwrite("Login canceled! No change to the current user!")
		return None
	# use the default????
	if len(currentusername)==0 and len(inputusername)==0 and len(defaultusername)>0: # user did NOT enter a name at all, but we have a default we can use
		inputusername=defaultusername
	return inputusername
"""
# MDH@07SEP2017: here we should have access to getExpression() therefore we can read any expressions stored in the user function expression file
def getEnvironmentPath(_environment):
	environmentname=_environment.getName()
	if isinstance(environmentname,str) and len(environmentname)>0:
		return environmentname+opsyspath.sep
	return ""
"""
def readExpressions(_environment,_evaluate=False):
	# _expressionfile designates the open file containing the expressions to populate _environment with
	expressionsfilename=_environment.getExpressionsFilename()
	if opsyspath.exists(expressionsfilename):
		#######note("Reading expressions from "+expressionsfilename+".")
		expressionsfile=open(expressionsfilename,'r')
		if expressionsfile:
			expressionline=expressionsfile.readline()
			while len(expressionline)>0:
				try:
					expressiontext=expressionline.rstrip('\r\n')
					# there's either a value or a value and an expression on the line
					if len(expressiontext)>0: # not an expression declaration (probably the value of the expression)
						tabpos=expressiontext.find('\t')
						if tabpos>=0: # expression available
							expressiontext=expressiontext[tabpos+1:]
						#######note("\tParsing '"+expressiontext+"'...")
						# MDH@10SEP2017: essential to pass 0 for the debug value!!!
						(expression,error)=getExpression(expressiontext,_environment,_evaluate,0)
						if error is None: # no error
							_environment.addExpression(expression)
							if _evaluate:
								try:
									expression.evaluatesTo(_environment) # return statements throw the return exception, which we want to catch
								except ReturnException,returnException:
									expression.setValue(returnException.getValue()) # TODO an IdentifierElementExpression also has a setValue but that one requires an environment as well
						else: # some error, add None
							note("ERROR: '"+error+"' in processing expression text '"+expressiontext+"' of '"+_environment.getName()+"'.")
							_environment.addExpression(None)
				finally:
					expressionline=expressionsfile.readline() # read the next line
			expressionsfile.close()
		else:
			note("ERROR: Failed to open expressions file '"+expressionsfilename+"'.")
	else:
		note("NOTE: Expressions file '"+expressionsfilename+"' does not exist!")
def initializeUsers(_environment):
	try:
		usersfilename=_environment.getUsersFilename()
		if opsyspath.exists(usersfilename):
			usersfile=open(usersfilename,'r')
			if usersfile:
				userlines=usersfile.readlines()
				usersfile.close()
				for userline in userlines:
					usertext=userline.rstrip('\r\n')
					if len(usertext)>0:
						_environment.addUser(usertext)
			else:
				note("ERROR: Failed to open users file '"+usersfilename+"'.")
		else:
			note("NOTE: Users file '"+usersfilename+"' does not exist!")
	finally:
		_environment.setUsersFile(open(usersfilename,'a'))
def initializeFunctions(_environment):
	functionsfilename=_environment.getFunctionsFilename()
	if opsyspath.exists(functionsfilename):
		functionsfile=open(functionsfilename,'r')
		if functionsfile:
			functionlines=functionsfile.readlines()
			functionsfile.close()
			if len(functionlines)>0:
				note("Number of functions defined in functions file '"+functionsfilename+"': "+str(len(functionlines))+".")
				for functionline in functionlines:
					functiontext=functionline.rstrip('\r\n')
					if len(functiontext)==0 or functiontext[0]==';':
						continue
					functionparameters=functiontext.split('\t')
					if len(functionparameters)==0:
						continue
					standalone=False
					functionname=functionparameters[0] # the first element is the name of the function
					if functionname.endswith('*'): # ends with the standalone indicator
						functionname=functionname[:-1]
						standalone=True
					ffn=_environment.getFunctionFilename(functionname) # the name of the function file
					if opsyspath.exists(ffn):
						note("Creating function "+functionname+"...")
						functionparameters=functionparameters[1:]
						functionresultidentifiername=None
						functionparameterdefaults=list()
						for functionparameter in functionparameters:
							functionparameterparts=functionparameter.split("=")
							if functionparameterparts[0]=='$': # defines the name to use for the result
								if len(functionparameterparts)>1 and len(functionparameterparts[1])>0:
									functionresultidentifiername=functionparameterparts[1]
							else:
								note("Registering parameter default "+getText(functionparameterparts)+" of function "+functionname+".")
								if len(functionparameterparts)>1:
									functionparameterdefaults.append((functionparameterparts[0],functionparameterparts[1]))
								else:
									functionparameterdefaults.append((functionparameterparts[0],None))
						# ready to create the function
						function=UserFunction(functionname,_environment,standalone,functionparameterdefaults,functionresultidentifiername)
						# create an environment with the right name and initialize like any other environment
						functiondefinitionenvironment=function.getDefinitionEnvironment() # in which we will read the expressions
						# I need to read the subfunctions first before I can read the expressions from the file
						note("Looking for inner functions of "+functionname+"...")
						initializeFunctions(functiondefinitionenvironment) # the inner functions are stored in the definition environment
						# MDH@19SEP2017: how about waiting loading the expressions until we encounter a function call??????
						"""
						note("Reading expressions defining function "+functionname+"...")
						readExpressions(functiondefinitionenvironment) # all subsequent lines in the function file are expressions to be read into the function environment
						"""
						######functionenvironment=None # no further use for this function environment
						note("Registering function "+functionname+"...")
						_environment.addFunction(function) # store the function with the environment (without registering again)
					else:
						note("ERROR: Assumed function file '"+ffn+"' does not exist!")
			else:
				note("WARNING: No functions defined in functions file '"+functionsfilename+"'.")
		else:
			note("ERROR: Failed to open functions file '"+functionsfilename+"'.")
	else:
		note("NOTE: Functions file '"+functionsfilename+"' does not exist!")
	return 0
def initializeEnvironment(_environment):
	initializeUsers(_environment) # load the users
	initializeFunctions(_environment) # load the functions (but not the expressions yet!!!)
	_environment.loadExpressions(True) # force load the expressions (which should force load the expressions of those functions actually called!!!)
# we'd like to write the option character in a different backcolor e.g. the DEBUG_BACKCOLOR?
def getOptionText(_text):
	return str(ColoredText(_text,OPTION_COLOR,OPTION_BACKCOLOR))
options=(getOptionText(':')+' (declaration) mode',getOptionText('=')+' (value) mode',getOptionText('b')+'ackcolor',getOptionText('c')+'olor',getOptionText('d')+'ebug',getOptionText('f')+'unction',getOptionText('h')+'elp',getOptionText('l')+'ogin','show '+getOptionText('M'),getOptionText('o')+'perators',getOptionText('s')+'hell',getOptionText('u')+'sers',getOptionText('v')+'ariables','e'+getOptionText('x')+'it M')
def writeOptions():
	####lnwrite("What would you like to do? [:|=|b|c|d|f|h|l|M|o|s|u|v|x] ") #### replacing: write(tokenchar)
	lnwrite("Options: ")
	for option in options:
		output(option+'	 ')
"""
READY FOR THE MAIN USER INPUT LOOP
"""
def main():
	global DEBUG
	global environment,Menvironment
	global INFO_BACKCOLOR,LITERAL_BACKCOLOR,OPERATOR_BACKCOLOR,DEBUG_BACKCOLOR,IDENTIFIER_BACKCOLOR,RESULT_BACKCOLOR,ERROR_BACKCOLOR,OPTION_BACKCOLOR
	global INFO_COLOR,LITERAL_COLOR,OPERATOR_COLOR,DEBUG_COLOR,IDENTIFIER_COLOR,RESULT_COLOR,ERROR_COLOR,OPTION_COLOR
	# keep a list of statements, every line is one statement
	# MDH@03SEP2017: I suppose we can let M remember the last user
	writeln("Welcome to M.")
	# initialize the list of possible M function filenames (as used by initializeFunctions)
	initializeEnvironment(Menvironment) # load whatever expressions were entered in the root environment
	setUsername("") # start with an undefined current user
	# make it possible to retrieve previous expressions entered
	#####print("Start control messages with a backtick (`)!")
	######### MDH@02SEP2017 the environment will keep the list of entered expressions: global mexpressions
	mexpression=None
	controlmode=False # start out in input mode
	expressioncontinuation='' # no expression continuation to start with
	newline() # ready for the first input prompt!!
	while 1:
		# if we've entered control mode somehow process control input until done
		if controlmode:
			# MDH@02SEP2017: it might be a good idea to to a Q&A
			while 1:
				# TODO write what each possible option means on a single line here
				writeOptions()
				lnwrite("What would you like to do? [:=bcdfhlMosuvx] ") #### replacing: write(tokenchar)
				controlch=getch()
				writeln(controlch)
				if ord(controlch)==3 or ord(controlch)==4 or ord(controlch)==10 or ord(controlch)==13:
					break
				if controlch=='s' or controlch=='S': # execute a shell command
					while 1:
						write("Enter the (shell) command to execute: ")
						shellcommand=raw_input().strip()
						if len(shellcommand)==0:
							break
						try:
							returncode=executeshellcommand(shellcommand)
							if returncode:
								writeln("\tWARNING: Non-zero return code of executing '"+shellcommand+"': "+str(returncode)+".")
						except Exception,ex:
							writeln("\tERROR: '"+str(ex)+"' executing '"+shellcommand+"'.")
				elif controlch=='h' or controlch=="H":
					writeln("Options (following the backtick):")
					writelnleft(":\tto switch to declaration mode (default).")
					writeln("=\tto switch to evaluation mode.")
					writelnleft("b\tto set back colors (d=debug, i=identifier, l=literal, o=operator, p=prompt).")
					writeln("c\tto set text colors (d=debug, i=identifier, l=literal, o=operator, p=prompt).")
					writelnleft("d\tto set the debug level.")
					writeln("f\tto create a new function.")
					writelnleft("F\tto end the function currently being created.") # MDH@02SEP2017: do we want something else????
					writeln("h\tto view this help.")
					writelnleft("l\tto login.")
					writeln("M\tto show the entered expressions (one at a time).")
					writelnleft("o\tshows the list of operators.")
					writeln("s\tto execute shell commands.")
					writelnleft("v\tshows the list of variables.")
					writeln("u\tshows the list of registered users.")
					writelnleft("x\tto exit M immediately.")
				elif controlch=="F": # end the current function
					# register the function that ends to the current environment
					endFunctionCreation()
						#######newline()
				elif controlch=="o" or controlch=="O":
					writelnleft("Binary operators:")
					writeln("\tArithmetic\t- + % \ | & ^ . .. * ** / // << >>")
					writelnleft("\tComparison\t< <= > >= == ")
					writeln("\tLogical\t\t&& ||")
					writelnleft("\tAssignment\t=")
					writeln("\tDeclaration\t:")
					writelnleft("Unary operators:\t= ! ~ - +")
				elif controlch=="u" or controlch=="U":
					if usernames is not None:
						write("Users:")
						for username in usernames:
							write(" "+username)
					else:
						lnwrite("No users available.")
					newline()
				elif controlch=="v" or controlch=="V":
					write("Variables ('M', 'functions' and 'variables' not included):")
					identifiervalues=environment.getIdentifierValues(["M","functions","variables"]) # passing the list of names not to show...
					for identifiername in identifiervalues:
						identifiervalue=identifiervalues[identifiername]
						write(" "+identifiername+"="+(getText(identifiervalue),"?")[identifiervalue is None])
					newline()
				elif controlch==":": # MDH@27AUG2017: switch to declaration mode
					environment.setMode(0)
				elif controlch=="=": # MDH@27AUG2017: switch to evaluation mode
					environment.setMode(1)
				elif controlch=="f": # starts a function
					writeFunctions(environment)
					write("What is the name of the function? ")
					functionname=raw_input().strip()
					if len(functionname)>0:
						newfunction=not functionname in environment.getFunctionNames()
						if newfunction: # doesn't exist yet
							# I need to know which external variables the user wants to use
							write("What local variable will contain the result (default: $)? ")
							functionresultidentifiername=raw_input().strip()
							# get the parameters/local variables
							write("Will this be a standalone function [y|n]? ")
							controlch2=getch()
							write(controlch2)
							standalone=(controlch2=='y' or controlch=='Y')
							lnwrite(controlch2)
							functionparameters=list()
							while 1:
								parameterindex=len(functionparameters)+1
								write("What is the name of parameter #"+str(parameterindex)+"? ")
								parametername=raw_input().strip()
								if len(parametername)==0:
									break
								write("What is the default value of "+parametername+"? ")
								parameterdefaulttext=raw_input().strip()
								if len(parameterdefaulttext)>0:
									parameterdefault=getExpressionValue(parameterdefaulttext,environment)
									if parameterdefault is None:
										writeln("WARNING: The value of the default expression '"+parameterdefaulttext+"' is undefined!")
								else:
									parameterdefault=None
								functionparameters.append((parametername,parameterdefault))
							# allow adding more local variables if not a standalone version
							if not standalone:
								writeln("Please define any local variable the function will use (masking any external variable with the same name)")
								while 1:
									write("What is the name of the local variable? ")
									parametername=raw_input().strip()
									if len(parametername)==0:
										break
									functionparameters.append((parametername,None))
							userfunction=UserFunction(functionname,environment,standalone,functionparameters,functionresultidentifiername) # create the function with its own creation environment
							# register this function in the environment's Mfunctions file
							#########userfunction.writeDefinition(environment.getName()+'.Mfunctions') # can't write the function expressions yet of course!!!
							writeln("Until you end "+functionname+" with `F or Ctrl-D the following expressions will use the parameter defaults (as a test).")
						else: # the function already exists, let's allow continuation
							userfunction=environment.getFunction(functionname) # I guess the given function is already loaded then????
							writeln("Until you stop continuing "+functionname+" with `F or Ctrl-D the following expressions will use the parameter defaults (as a test).")
						environment=userfunction.getDefinitionEnvironment() # update the current environment with the operating environment using the defaults (i.e. there's NO argument list)
						if newfunction: # MDH@11SEP2017: read the expressions defined previously
							environment.setup()
						else:
							readExpressions(environment,False)
						environment.startUserFunction(userfunction) # pushing the user function to pop off when done creating!!!
						# when running standalone NO access to the (current) environment but only to the (global) Menvironment
						# TODO if we want the function to be callable in itself, we need to add it to the given environment immediately
						# get the new child environment, to be used during creating the function
						# remember the function being created TODO we still need to make it possible for a function to call itself
						writeVariables(environment)
				elif controlch=="b": # the back color
					# allow changing multiple backcolor in a row
					write("Text backcolor codes: debug="+str(DEBUG_BACKCOLOR)+", error="+str(ERROR_BACKCOLOR)+", identifier="+str(IDENTIFIER_BACKCOLOR)+", literal="+str(LITERAL_BACKCOLOR)+", operator="+str(OPERATOR_BACKCOLOR)+", prompt="+str(INFO_BACKCOLOR)+", result="+str(RESULT_BACKCOLOR)+".")
					while 1:
						lnwrite("What backcolor do you want to set? [d|e|i|l|o|p|r] ")
						controlch2=getch()
						if controlch2=="l":
							currentcolorcode=LITERAL_BACKCOLOR
						elif controlch2=="e":
							currentcolorcode=ERROR_BACKCOLOR
						elif controlch2=="o":
							currentcolorcode=OPERATOR_BACKCOLOR
						elif controlch2=="d":
							currentcolorcode=DEBUG_BACKCOLOR
						elif controlch2=="i":
							currentcolorcode=IDENTIFIER_BACKCOLOR
						elif controlch2=="p":
							currentcolorcode=INFO_BACKCOLOR
						elif controlch2=="r":
							currentcolorcode=RESULT_BACKCOLOR
						else:
							break
						lnwrite("Change the text backcolor code ("+str(currentcolorcode)+") to: ")
						try:
							colorcode=int(raw_input())
							if controlch2=="l":
								LITERAL_BACKCOLOR=colorcode
							elif controlch2=="e":
								ERROR_BACKCOLOR=colorcode
							elif controlch2=="o":
								OPERATOR_BACKCOLOR=colorcode
							elif controlch2=="d":
								DEBUG_BACKCOLOR=colorcode
							elif controlch2=="i":
								IDENTIFIER_BACKCOLOR=colorcode
							elif controlch2=="p":
								INFO_BACKCOLOR=colorcode
							elif controlch2=="r":
								RESULT_BACKCOLOR=colorcode
						except Exception,ex:
							lnwrite("ERROR: '"+str(ex)+"' changing the "+controlch2+" backcolor code.")
				elif controlch=="c":
					lnwrite("Text color codes: debug="+str(DEBUG_COLOR)+", error="+str(ERROR_COLOR)+", identifier="+str(IDENTIFIER_COLOR)+", literal="+str(LITERAL_COLOR)+", operator="+str(OPERATOR_COLOR)+", prompt="+str(INFO_COLOR)+", result="+str(RESULT_COLOR)+".")
					while 1:
						lnwrite("What text color do you want to set? [d|e|i|l|o|p|r] ")
						controlch2=getch()
						if controlch2=="l":
							currentcolorcode=LITERAL_COLOR
						elif controlch2=="e":
							currentcolorcode=ERROR_COLOR
						elif controlch2=="o":
							currentcolorcode=OPERATOR_COLOR
						elif controlch2=="d":
							currentcolorcode=DEBUG_COLOR
						elif controlch2=="i":
							currentcolorcode=IDENTIFIER_COLOR
						elif controlch2=="p":
							currentcolorcode=INFO_COLOR
						elif controlch2=="r":
							currentcolorcode=RESULT_COLOR
						else:
							break
						lnwrite("Change the color code ("+str(currentcolorcode)+") to: ")
						try:
							colorcode=int(raw_input())
							if controlch2=="l":
								LITERAL_COLOR=colorcode
							elif controlch2=="e":
								ERROR_COLOR=colorcode
							elif controlch2=="o":
								OPERATOR_COLOR=colorcode
							elif controlch2=="d":
								DEBUG_COLOR=colorcode
							elif controlch2=="i":
								IDENTIFIER_COLOR=colorcode
							elif controlch2=="p":
								INFO_COLOR=colorcode
							elif controlch2=="r":
								RESULT_COLOR=colorcode
						except Exception,ex:
							lnwrite("ERROR: '"+str(ex)+"' changing the "+controlch2+" text color code.")
				elif controlch=="m" or controlch=="M": # show the contents of the M array element by element
					write("Contents of M (press Esc to stop, any other key to continue):")
					Mexpressionlist=environment.getIdentifierValue("M")
					if isIterable(Mexpressionlist):
						expressionindex=0
						for Mexpression in Mexpressionlist:
							expressionindex+=1
							if Mexpression is None:
								continue
							lnwrite("M("+str(expressionindex)+")="+str(Mexpression))
							sch=getch()
							if ord(sch)==27:
								break
					else:
						lnwrite("Sorry. Unable to show the contents of M as it is not a list.")
				elif controlch=="l" or controlch=="L":
					setUsername(getUsername())
				elif controlch=="d" or controlch=="D":
					write("Please enter the new debug level (replacing: "+str(DEBUG.getValue())+"): ")
					debugtext=raw_input().strip()
					try:
						DEBUG.setValue(int(debugtext))
						writeln("Debug level set to "+str(DEBUG.getValue())+".")
					except:
						writeln("Invalid debug level input '"+debugtext+"': only non-negative integer values are allowed!")
				elif controlch=="x" or controlch=="X":
					break
				else:
					writeln("Unrecognized control message.")
				# only the b, c and d control characters allow further setting
				if controlch!='b' and controlch!='c':
					break
			if controlch=="x" or controlch=="X":
				break
			controlmode=0 # if we get here we finished control messages and we could've done continue BUT we'd end up at the newprompt() next anyway!!!!
		# display the prompt (with the info line in front of it)
		newprompt()
		#######expressioncontinuation=""
		resulttext="" # no result text so far
		# MDH@01SEP2017: if we have an expression defined at the moment, we simply retrieve all token characters in it, and display them
		if mexpression is not None:
			userInputLine.reset(mexpression.getCharacters())
			output(str(userInputLine)) # write right after the prompt
		else:
			userInputLine.reset()
			# replacing: mexpression.echo() which still uses .getWritten()
		# otherwise the first character on the new expression is allowed to be Ctr-D or the backtick
		tokenchar=getch()
		# special tokens are permitted when starting with a new expression which we have to process first
		if mexpression is None:
			if ord(tokenchar)==4: # Ctrl-D
				if environment.getNumberOfStartedUserFunctions()==0: # not creating a function right now
					if len(currentusername)==0:
						break
					setUsername("")
				else:
					# MDH@03SEP2017: at the top level exit M otherwise exit the function creation
					endFunctionCreation()
				continue
			if tokenchar=='`': # ` means the user wants to set an M option (and not enter an M expression)
				controlmode=1 # switch to control mode, we skip the rest (which deals with input mode)
				continue
			# if we get here it wasn't Ctrl-D or `, it might still be the arrow up or arrow down to select a previous expression
			mexpressionretrieved=None
			exprindex=environment.getNumberOfExpressions() # the position of the expression to use
			# if this is the Escape character let's wait for the last of the threesome characters
			while ord(tokenchar)==27: # Escape character received
				if mexpressionretrieved is not None: # a previously retrieved expression showing, we cannot overwrite the same line
					mexpressionretrieved=None
					reprompt() # the effect being that the expression written on the line is erased (because prompt(False) clears the current line)
				sch=getch() # first Escaped character
				ch=getch() # last Escaped character
				if ord(sch)==0x5B: # [, i.e. CSI escape sequence
					# now read all characters up until something between 64 and 126, inclusive
					while ord(ch)<0x40 or ord(ch)>0x7D:
						ch=getch()
					if ord(ch)==0x41: # arrow up
						if exprindex>0:
							exprindex-=1
						else: # can we beep?
							beep()
						if exprindex<environment.getNumberOfExpressions():
							mexpressionretrieved=environment.getExpression(exprindex)
					elif ord(ch)==0x42: # arrow down
						# user shouldn't be allowed to cycle beyond len(mexpressions)
						if exprindex<environment.getNumberOfExpressions():
							exprindex+=1
							if exprindex<environment.getNumberOfExpressions():
								#####print "Retrieving expression #"+str(exprindex)+"..."
								mexpressionretrieved=environment.getExpression(exprindex)
					elif ord(ch)==0x43: # C, move forward
						beep() #note("Moving the cursor forward not implemented yet!")
					elif ord(ch)==0x44: # D, move backward
						beep() #note("Moving the cursor back not implemented yet!")
					# something to display????
					if mexpressionretrieved is not None:
						######print("Printing the expression!")
						mexpressionretrieved.unend() # we need to write the unended version as that's the one that is to be continued...
						userInputLine.reset(mexpressionretrieved.getCharacters())
						updateUserInputLine(True) # write the user input line again
						# we have to show it anyway I suppose without registering with userInputLine
				# read the next character (which might be another Escape character)
				tokenchar=getch() # get the first character
			if mexpressionretrieved is not None:
				mexpression=copy.deepcopy(mexpressionretrieved) # NO need to unend here because we already did that when showing the expression!!!
		# if we haven't got an expression (to continue) at this moment, we create a new one
		if mexpression is None:
			mexpression=Expression(environment,None,DEBUG,True) # start a new expression at the main debug level (DEBUG) which is the default!!
			########output(str(userInputLine)) # MDH@01SEP2017: no need to do this we've already echoed the unended expression!!!
		# I guess we can allow Ctrl-D at any moment as well
		# NOTE a newline (Enter) shouldn't end the expression input per se
		##### see the use of Expression.echo() to rewrite the entire expression again!!! Mexpression=mexpression # MDH@25APR2017: we need a reference to the main level expression, so we can rewrite it (e.g. after a backspace!!)
		# MDH@01SEP2017: it's probably best to deal with all situations separately (i.e. following either backspace(), add() or processing the newline character???
		resultlength=0
		while ord(tokenchar)!=3 and ord(tokenchar)!=4 and tokenchar!='`': # not Ctrl-C or Ctrl-D or backtick
			expressionerror=None
			if ord(tokenchar)!=10 and ord(tokenchar)!=13: # the expression WILL change (because it's not a newline character!)
				"""
				resultlength=len(resulttext)
				if resultlength>0: # there is (intermediate) result text to remove
					resulttext=""
					output(" "*resultlength) # write as many blanks as the result takes
					output("\033["+str(resultlength)+"D") # return to the original cursor position
				"""
				if ord(tokenchar)==9: # a tab
					# we need a continuation to add to the name of the identifier
					if len(expressioncontinuation)>0:
						# remove the intermediate result
						resultlength=len(resulttext)
						if resultlength>0:
							resulttext=""
							output(" "*(resultlength+2)) # MDH@04SEP2017: TODO or some more if there's debug information in the character removed!
							output("\033["+str(resultlength+2)+"D") # return to the previous cursor position
						for tokenchar in expressioncontinuation:
							mexpression_new=mexpression.add(tokenchar)
							expressionerror=mexpression.getError()
							if expressionerror is not None:
								writeerror(expressionerror)
								updateUserInputLine(false)
								break
							if mexpression_new is None:
								break
							mexpression=mexpression_new
				elif ord(tokenchar)==127: # a backspace
					if len(userInputLine)>0:
						mexpression_new=mexpression.backspace() # returns None if some error occurred
						expressionerror=mexpression.getError()
						# write the error first (if so required)
						if expressionerror is not None:
							newline()
							writeerror(expressionerror)
						if mexpression_new is not None: # success i.e. definitely NO error
							userInputLine.removeLastCharacter(expressionerror is None)
						elif expressionerror is None: # NO success AND NO error
							beep() # shouldn't happen though!!!!
					else: # nothing left on the input line
						beep()
				else: # not a backspace, or a tab
					mexpression_new=mexpression.add(tokenchar)
					expressionerror=mexpression.getError()
					if expressionerror is not None:
						newline()
						writeerror(expressionerror)
						updateUserInputLine(False) # no need to empty the line because it is already empty after writing the error
				# next to write any expression continuation available
				# forget about the continuation if an error occurred
				if expressionerror is None:
					expressioncontinuation=mexpression.getContinuation()
					if len(expressioncontinuation)>0: # an expression continuation to show
						# remove any current intermediate result, so it won't be visible when showing the continuation
						resultlength=len(resulttext)
						if resultlength>0:
							resulttext=""
							output(" "*(resultlength+2)) # MDH@04SEP2017: TODO or some more if there's debug information in the character removed!
							output("\033["+str(resultlength+2)+"D") # return to the previous cursor position
						write(expressioncontinuation,DEBUG_COLOR)
						output("\033["+str(len(expressioncontinuation))+"D") # return to the cursor position
						hidecursor() # hide the cursor otherwise we won't see the first continuation character on the position where to input a character
					else:
						showcursor() # show the cursor so the user can see where (s)he's typing
			elif len(userInputLine)>0: # Enter pressed, with something on the current input line
				# MDH@25AUG2017: we'll evaluate the expression until now and continue on the next line, which would be neat
				#								 but let's decide to only do that when we're at the top level
				#######note("Checking whether the expression is complete!")
				if mexpression.parent is not None: # there is a parent, but if the expression is a declaration we're done anyway!!
					if mexpression.isDeclared():
						mexpression=mexpression.parent # pretty essential to return to the parent, in which the declaration occurred!!
						break
				elif mexpression.ends() is None: # expression complete, so ready to be evaluated, so there's no need to set mexpression_new anyway!!!
					break
				# let's NOT add the newline character to the expression anymore, so the expression itself does NO longer contain newline characters
				# this means that when requesting such an expression again, it will occupy a single input line
				# this might be bad if the text line is long, but continuing an expression on the next line is only there for debugging (showing intermediate results)
				########mexpression_new=mexpression.add(newlinechar) # add the newline char (which we know is whitespace)
				newline()
				resulttext="" # prevent the old result text from showing immediately on the new user input line
				continueprompt() # change the prompt to the continuation prompt (not including M(<index>)
				userInputLine.reset() # start a new user input line by clearing the displayed token characters
				writeprompt()
			else: # just ignore
				beep()
				mexpression_new=None # force skip the following, so we'll be reading the next character next!!!
			# FINAL PROCESSING OF THE RESULT OF PROCESSING THE CHARACTER INPUT BY THE USER
			if mexpression_new is not None: # whatever we did we succeeded!!!
				mexpression=mexpression_new
				# MDH@31AUG2017: it's neat to show the value of the expression in debug mode when it could end
				if getDebug()&1:
					newresulttext=""
					# MDH@19SEP2017: if empty do not evaluate
					if mexpression.parent is None and not mexpression.isEmpty() and not mexpression.assigns(): # we're at the top level in a non-assigning expression
						if mexpression.ends() is None: # expression is considered complete
							try:
								expressionvalue=mexpression.evaluatesTo(environment)
								newresulttext=" = "+getText(expressionvalue)
							except ReturnException,returnException:
								newresulttext=str(returnException)
					else: # when in a subexpression there's NO result to show until we leave it again
						newresulttext=" "
					# if the previous result was larger than the current result replace that
					resultlength=len(resulttext)
					# replace result text if we have a new result text otherwise we stick to showing again what we had before
					newresultlength=len(newresulttext)
					if newresultlength>0: # a new result to show
						# clear the entire previous result
						if resultlength>0:
							output(" "*(resultlength+1)) # MDH@04SEP2017: TODO or some more if there's debug information in the character removed!
							output("\033["+str(resultlength+1)+"D") # return to the previous cursor position
						resulttext=newresulttext
						resultlength=newresultlength
					# we have to skip any continuation showing, increment resultlength before showing the intermediate result
					if resultlength>0: # still some result to display
						if len(expressioncontinuation)>0:
							output("\033["+str(len(expressioncontinuation))+"C") # jump over the showing expression continuation
							resultlength+=len(expressioncontinuation) # when we jump back we have to jump over the continuation as well
						# something left to remove of the old result????
						output(str(ColoredText(resulttext,DEBUG_COLOR,None)))
						output("\033["+str(resultlength)+"D") # return to the original cursor position
			# ready to read and process the next character!!!
			tokenchar=getexprch()
			# it's prudent to remove any expression continuation here immediately
			# NOTE you can overwrite the expression continuation with blanks but you cannot
			#			 clear expressioncontinuation because the user could still choose it
			# NOTE we can check right now whether the new token character is a Tab though
			#			 so when it is NOT a Tab we can safely remove the continuation right away
			if ord(tokenchar)!=9: # not a tab
				expressioncontinuationlength=len(expressioncontinuation)
				if expressioncontinuationlength>0:
					expressioncontinuation=""
					output((" "*expressioncontinuationlength)+"\033["+str(expressioncontinuationlength)+"D")
			#######output("("+str(ord(tokenchar))+")")
		#####writeln("Done processing user input...")
		if tokenchar=='`': # backtick, do NOT read another token
			controlmode=1 # and switching to control mode as well
			continue
		if ord(tokenchar)==4: # Ctrl-D
			showcursor()
			if len(currentusername)==0:
				lnwrite("Exit M? ")
				sch=getch()
				write(sch)
				if sch=="y" or sch=="Y":
					break
				newline()
			else: # logout
				setUsername("")
			continue
		# in all other situations will we be starting a new user input line
		####### NOT HERE!!!! userInputLine.reset()
		if ord(tokenchar)==3: # Ctrl-C
			mexpression=None
			newline()
			continue
		# ready to evaluate (and register)
		if mexpression is not None:
			mexpression.end() # end the expression as token instance
			# get rid of whatever intermediate result text was shown behind where the cursor is
			if resultlength>0:
				output(" "*resultlength)
				output("\033["+str(resultlength)+"D") # return to the original cursor position
			# MDH@22SEP2017: empty expressions now return None, whereas if somehow invalid, they return undefined!!!
			try:
				expressionvalue=mexpression.evaluatesTo(environment) # pass in the global environment to evaluate the expression
				#######note("Expression value: "+str(expressionvalue)+"'!")
			except ReturnException,returnException:
				expressionvalue=returnException.getValue()
			# write the value of the expression on a separate line (before writing any error)
			newline()
			output(' '*(len(prompt)-2)) # skip length of prompt!!
			write("= ",INFO_COLOR)
			if expressionvalue is not None:
				write(getText(expressionvalue),RESULT_COLOR,RESULT_BACKCOLOR)
			newline()
			computationerror=mexpression.getError()
			if computationerror is not None:
				writeerror(computationerror)
			# even if the expression is empty we store it anyway (although it's best not referred to!!)
			if environment.getMode()==0: # declaration mode
				environment.addExpression(mexpression) # MDH@17AUG2017: storing the expression itself (which value might change dynamically)
			else:
				environment.addExpression(expressionvalue) # MDH@17AUG2017: for now let's see if we can do this!!
			mexpression=None # thus forcing to have to create a new one instead of continueing with the incompleted one
		else:
			writeerror("No expression to evaluate!")
	######emptyline() # clear the current input line
	newline()
	writeln("Thank you for using M"+("",", "+currentusername)[len(currentusername)>0]+".")
	showcursor()
####DEBUG=1 # by default, shows the intermediate result!!
if __name__=="__main__":
	try:
		if len(sys.argv)>1:
			DEBUG.setValue(int(sys.argv[1]))
	finally:
		main()
