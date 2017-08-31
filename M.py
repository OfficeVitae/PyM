"""
Marc's expression tokenizer and evaluator
"""
""" History
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
	####print str(type(ch))
	#######sys.stdout.write(str(ord(ch)))
	return ch

DEBUG_COLOR=8 # light gray
INFO_COLOR=0 # black
ERROR_COLOR=9 # red
PROMPT_COLOR=INFO_COLOR # same as the info color

IDENTIFIER_COLOR=202 # orange for unknown identifiers (although these would be used for assignments)
VARIABLE_COLOR=13 # magenta
FUNCTION_COLOR=93 # something more blueish
LITERAL_COLOR=22 # green
OPERATOR_COLOR=12 # blue
RESULT_COLOR=15 # quite dark
RESULT_BACKCOLOR=12 # or what????

INFO_BACKCOLOR=231 # white
DEBUG_BACKCOLOR=255 # light grey

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
# convenient to be able to color certain text
def getColoredText(_text,_color,_backcolor=None):
	return getColorText(_color,_backcolor)+_text+getColorText(0)

# main output method to be used to output any text directly
def output(_tooutput):
	sys.stdout.write(_tooutput)

# methods that write to the console themselves, and should be called by all other output producing functions/methods
def beep():
	output('\a')
def emptyline(): # clears the current line and puts the cursor at the beginning of the current line
	output("\033[2K\r")
def backspace(): # means go one position to the left on the current line, and clear the rest of the line
	output("\033[D") # go left one character
	output("\033[K") # clear the rest of the line
# write outputs text to be colored
def write(_towrite,_color=None,_backcolor=None):
	result=getColorText(_color,_backcolor)+_towrite+"\033[0m" # prudent to force the standard color after each write!!
	output(result)
	return result
def newline():
	output("\n\033[0m") # it makes sense to reset the coloring at the start of each next line!!!
# end of output producing methods

# helper functions for outputting text
def writeln(_linetowrite,_backcolor=None,_color=None): # writes a line in black
	write(_linetowrite,_color,_backcolor) #####write(_linetowrite+'\n',_color,_backcolor)
	newline()
def lnwrite(_linetowrite,_backcolor=None,_color=None):
	# NOTE whatever's left of the current line we want to use the standard background color
	newline()
	write(_linetowrite,_color,_backcolor) # NOT using write assuming the newline will undo any coloring defined!!!
def lnwriteleft(_linetowrite,_width=0,_color=None,_backcolor=None):
	dwidth=_width-len(_linetowrite)
	if dwidth>0:
		_linetowrite+=" "*dwidth
	lnwrite(_linetowrite,_color,_backcolor)
# \r at the start forces the cursor to be at the beginning of the line
# but it is a bit of a nuisance that the line might not be empty so can we do that here as well????
# as such it should either be preceded by newline() or emptyline()
# MDH@27AUG2017: allowing two modes of operation
mode=0 # declaration mode
def setMode(_mode):
	global mode
	mode=_mode
modechars=":=" # the two mode characters (: in declaration mode and = in evaluation mode)
prompt=None
def updateprompt():
	global prompt
	prompt="M("+str(len(mexpressions)+1)+")"+modechars[mode]+" "
def continueprompt():
	global prompt
	prompt=" "*len(prompt)
def writeprompt():
	write(prompt,PROMPT_COLOR)
def reprompt():
	emptyline()
	writeprompt()
def showprompt():
	newline()
	writeprompt()
def newprompt():
	#########lnwrite('Press Ctrl-D anytime to exit M, Ctrl-C to cancel any input.')
	updateprompt() # MDH@27AUG2017: we need a new prompt
	showprompt()
def note(_note):
	lnwrite('\t'+_note)
def writeerror(_error):
	lnwrite(" "*len(prompt))
	if isinstance(_error,str) and len(_error)>0:
		write(_error,ERROR_COLOR) # we have to go to a new line afterwards because prompt(False) will clear the current line
	else:
		write("Unknown error ("+str(_error)+")",ERROR_COLOR)

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

mexpressions=[] # keep track of all expressions entered so far

def isIterable(_obj):
	try:
		return not isinstance(_obj,str) and hasattr(_obj,'__iter__')
	except Exception,ex:
		note("ERROR: '"+str(ex)+"' checking on the iterability of "+str(_obj)+".")
def isIndexable(_obj):
	try:
		return hasattr(_obj,'__getitem__')
	except Exception,ex:
		note("ERROR: '"+str(ex)+"' checking on the indexability of "+str(_obj)+".")
def getText(_obj):
	if _obj is not None:
		###print "To print: "+str(_obj)+"."
		if isinstance(_obj,list): # get rid of the blanks behind the comma's
			if len(_obj)==1:
				return getText(_obj[0])
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
class Function:
	def __init__(self,_functionindex):
		self.functionindex=_functionindex
		self.debug=DEBUG # the default to use the global debug mode...
	def __str__(self):
		return "funct#"+str(self.functionindex)
	def setDebug(self,_debug):
		self.debug=_debug
		return self
	def apply(self,_value): # the function to be applied to a single argument
		value=getValue(_value)
		if value!=undefined.getValue():
			if self.functionindex>=50: # a list function
				if isIterable(value): # as it should be
					if self.functionindex==97: # length
						i=len(value)
						while i>0 and value[i-1]==undefined.getValue():
							i-=1
						return i
					if self.functionindex==98: # size
						return len(value)
					if self.functionindex==99: # sorti
						return [i[0]+1 for i in sorted(enumerate(value), key=lambda x:x[1])] # do NOT forget to add 1 to the index (zero-based in Python, one-based in M)
			else:
				# application of a scalar function to a list, means applying the function to each element of the list (and return the list of it)
				if isIterable(value):
					return map(self.apply,value)
				if self.functionindex==7:
					return ~value
				if self.functionindex==8: # NOT unary operator (which is !)
					return (0,1)[value==0]
				if self.functionindex==9: # = which means evaluate the expression behind it, which we already did!!!
					return value
				if self.functionindex==10: # minus unary operator
					return -value
				if self.functionindex==11:
					return value
				if self.functionindex==12:
					return math.sqrt(value)
				if self.functionindex==13:
					return abs(value)
				if self.functionindex==14:
					return math.cos(value)
				if self.functionindex==15:
					return math.sin(value)
				if self.functionindex==16:
					return math.tan(value)
				if self.functionindex==17:
					return 1/math.tan(value)
				if self.functionindex==18:
					return random.uniform(0,value)
				if self.functionindex==19:
					return math.log(value)
				if self.functionindex==20:
					return math.log10(value)
				if self.functionindex==21: # eval
					# __value is supposed to be a string which is a bit of an issue if it isn't
					# nevertheless we should treat __value as an expression that we need to evaluate
					expression=Expression(MEnvironment,0) # do not show any debug information while constructing the expression from the expression text!!!
					expressionerror=None
					expressiontext=dequote(value)[0]
					if self.debug&8:
						lnwrite("\tEvaluating '"+expressiontext+"'.")
					for ch in expressiontext:
						new_expression=expression.add(ch,False) # don't echo anything
						if new_expression is None:
							expressionerror="Unknown error processing '"+ch+"'."
						else:
							expressionerror=expression.getError()
						if expressionerror is not None:
							break
						if self.debug&8:
							note("No error processing '"+ch+"'...")
						expression=new_expression
					if expressionerror is None: # no error so far
						expressionerror=expression.ends()
					# if an error occurred somehow, raise an exception, alternatively we could return None to indicate no result (and therefore some error)
					if expressionerror is not None:
						raise Exception(expressionerror)
					if self.debug&8:
						note("Expression to evaluate: "+expression.getText()+".")
					return expression.getValue()
				if self.functionindex==22: # error
					raise Exception(value) # generate an error
				if self.functionindex==23: # list
					if isinstance(value,int):
						if value>0:
							return [undefined.getValue()]*value
						return []
		# if we get here the function result is undefined
		return undefined.getValue()
	def getValue(self,_arglist):
		fvalue=undefined.getValue()
		# this is the function application at the top level i.e. it will receive an argument list
		argcount=1+(self.functionindex/100) # the number of arguments this function has
		if len(_arglist)>=argcount:
			if argcount==1:
				if self.functionindex<23 and len(_arglist)==1: # a scalar function applied to a single-item argument list is to return a scalar
					fvalue=self.apply(_arglist[0])
				else: # apply the function to each separate element!!!
					fvalue=map(self.apply,_arglist)
					if self.functionindex>=23 and len(fvalue)==1:
						fvalue=fvalue[0]
			elif argcount==2: # two-argument functions like while and shape|format|arrange|group
				fvalue=[]
				# first all functions that consume all arguments in one go
				if self.functionindex==100: # while
					whilebody=_arglist[1:]
					condition=_arglist[0] # or we might pop this last argument
					conditionvalue=getValue(condition)
					###note("Value of condition '"+str(condition)+"': '"+str(conditionvalue)+"'...")
					while conditionvalue!=0:
						bodyvalues=map(getValue,whilebody)
						###note("Value of body '"+str(whilebody)+"': '"+str(bodyvalue)+"'...")
						fvalue.append(bodyvalues)
						conditionvalue=getValue(condition)
						###note("Value of condition '"+str(condition)+"': '"+str(conditionvalue)+"'...")
				else:
				# I guess we can pop two operands at a time into a result????
					while len(_arglist)>0:
						if self.functionindex==199: # the group function
							fvalue.append(group(getValue(_arglist.pop()),getValue(_arglist.pop())))
						elif self.functionindex==125: # while function application
							whilebody=_arglist.pop()
							condition=_arglist.pop()
							whilevalue=[]
				if len(fvalue)==1:
					fvalue=fvalue[0]
			elif argcount==3:
				if self.functionindex==200 or self.functionindex==201 or self.functionindex==202 or self.functionindex==203: # the 'if' function
					# NOTE we might expand if a bit but making it a multiselector
					#			 i.e. the output value (typically 0 or 1) in a comparison selects the expression to evaluate and return
					conditionvalue=getValue(_arglist[0])
					if isinstance(conditionvalue,int): # an acceptible outcome
						# wrap around the condition value to be in the range [0,len(_arglist)-2]
						if conditionvalue>0:
							conditionvalue%=len(_arglist)-1
						if conditionvalue>0: # evaluate one of the 'true' clauses
							fvalue=getValue(_arglist[conditionvalue+1])
						else: # evaluate the False clause
							fvalue=getValue(_arglist[1])
				elif self.functionindex==210: # for requires a total of three elements the loop variable, the list to iterate over, and what to do
					# instead of a condition we have a list with values to iterate over
					forindex=_arglist[0]
					# NOTE any argument should always be an expression, which should create the identifier mentioned in it
					#			 now, if it is not a single token in it of type identifier
					if isinstance(forindex,ExpressionEvaluator): # which it should be
						forindexvalues=getValue(_arglist[1]) # or we might pop this last argument
						if isIterable(forindexvalues):
							# create the identifier in forindex if need be (to be destroyed when done)
							forindexidentifierexists=False
							forindexexpression=forindex.getExpression()
							forindexenvironment=forindex.getEnvironment()
							if len(forindexexpression.tokens)==1 and forindexexpression.tokens[-1].getType() in (IDENTIFIER_TOKENTYPE,VARIABLE_TOKENTYPE):
								forindexidentifiername=forindexexpression.tokens[-1].getText()
							else:
								forindexidentifiername=None
							# remember if it already existed
							forindexidentifierexisted=forindexidentifiername is not None and forindexenvironment.identifierExists(forindexidentifiername)
							# ready to rock'n'roll
							getValue(forindex) # get the forindex expression executed (which will take care of creating the index identifier)
							# the for index identifier should now definitely exist
							if forindexidentifiername is not None: # the forindex identifies a single identifier to use as index variable
								forindexidentifier=forindex.getIdentifier(forindexidentifiername)
							else:
								forindexidentifier=None
							# do we have a for index identifier????
							fvalue=[]
							# NOTE we might consider leaving the loop if it's value changed within the loop
							for forindexvalue in forindexvalues:
								# update the value of the forindex identifier (if any)
								if forindexidentifier is not None:
									forindexidentifier.setValue(forindexvalue) # this is a bit of an issue
								forbodyvalue=map(getValue,_arglist[2:]) # evaluate the remaining arguments
								if not isIterable(forbodyvalue) or len(forbodyvalue)!=1:
									fvalue.append(forbodyvalue)
								else: # a single result
									fvalue.append(forbodyvalue[0])
							# if the for index identifier was created, it should be removed again
							if forindexidentifiername is not None and not forindexidentifierexisted:
								forindex.deleteIdentifier(forindexidentifiername)
						else:
							note("Second for loop argument not a list.")
					else:
						note("Please report the following bug: The first for loop argument is not an expression, but of type "+str(type(_arglist[0]))+"!")
		return fvalue
# keep track of the identifier (that have a value)
class Identifier:
	def setValue(self,_value=None):
		if self.name is None:
			raise Exception("Cannot change the value of a constant.")
		self.value=_value
		return self
	def __init__(self,_name=None,_value=None):
		self.name=_name
		self.value=_value
	def getValue(self):
		return self.value
	def __repr__(self):
		return self.name
	def __str__(self):
		return self.name
undefined=Identifier() # the identifier with None value is used to indicate an undefined value
# MDH@30AUG2017: an 'environment is basically a dictionary of identifiers
class Environment:
	def __init__(self,_parent=None):
		if isinstance(_parent,Environment):
			self.parent=_parent
		else:
			self.parent=None
		self.identifiers=dict()
		self.functiongroups=[]
	def getFunctionIndex(self,_identifier):
		for functiondict in self.functiongroups:
			if _identifier in functiondict:
				return functiondict[_identifier]
		return 0 # not a function
	def functionsExistStartingWith(self,_functionprefix):
		for functiongroup in self.functiongroups:
			for function in functiongroup:
				if function.startswith(_functionprefix):
					return True
		return False
	def identifiersExistStartingWith(self,_identifierprefix):
		for identifier in self.identifiers:
			if identifier.startswith(_identifierprefix):
				return True
		return False
	def identifierExists(self,_identifiername):
		if _identifiername in self.identifiers:
			return True
		if self.parent is not None:
			return self.parent.identifierExists(_identifiername)
		return False # can't find it
	def getIdentifier(self,_identifiername):
		if not self.identifierExists(_identifiername):
			self.identifiers[_identifiername]=Identifier(_identifiername)
			if DEBUG&8:
				note("Identifier "+_identifiername+" added...")
		return self.identifiers[_identifiername]
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
		try:
			return self.getIdentifier(_identifiername).getValue()
		except:
			note("Can't find "+_identifiername+".")
			return undefined.getValue()
	def addIdentifier(self,_name,_identifier):
		self.identifiers[_name]=_identifier
	def addFunction(self,_name,_function,_functiongroup):
		self.functions[_name]=_function
	def addFunctionGroup(self,_functiongroup):
		self.functiongroups.append(_functiongroup)
# create the main M environment
import math
MEnvironment=Environment()
# populate the M environment with the predefined constants/variables
MEnvironment.addIdentifier('undefined',undefined)
MEnvironment.addIdentifier('false',Identifier(_value=0))
MEnvironment.addIdentifier('true',Identifier(_value=1))
MEnvironment.addIdentifier('pi',Identifier(_value=math.pi))
MEnvironment.addIdentifier('e',Identifier(_value=math.e))
MEnvironment.addIdentifier('M',Identifier(_value=[]))
# MDH@31AUG2017: let's add the function groups as well
MEnvironment.addFunctionGroup({'sqr':12,'abs':13,'cos':14,'sin':15,'tan':16,'cot':17,'rnd':18,'ln':19,'log':20,'eval':21,'error':22,'list':23,'len':97,'size':98,'sorti':99})
MEnvironment.addFunctionGroup({'while':100,'join':199})
MEnvironment.addFunctionGroup({'if':200,'select':201,'case':202,'switch':203,'for':210})

# MDH@30AUG2017:
# the user is allowed to create functions with the function function
# last first argument should be the argument list, the remaining arguments the body expressions
class MFunction(Function):
	def __init__(self,_parameters,_body):
		Function.__init__(self,0) # all user defined functions have function index 0!!
		self.parameters=parameters
		self.body=_body
	def getValue(self,_arglist):
		# TODO yet to do
		pass
		# the argument list supplies the function with the initial values of the formal parameters i.e. actual parameters
		# the body is an expression that is to be executed using these actual parameters i.e. an expression can be given a set of actual values
def getTokentypeRepresentation(_tokentype):
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
	return ("-","")[_tokentype>=0]+result
def getOperatorPrecedence(_operator):
	if _operator==declarationchar: # TODO I have to think about this...
		return 15
	if _operator==assignmentchar: # = also is part of soro and we do not want it to come out there!!!
		return 14
	if _operator=="..":
		return 2
	if _operator=="**":
		return 3
	if _operator in ("*","/","^","%","\\","//","%%"): # all single-character operators (accidently?)
		return 4
	if _operator==periodchar or _operator in soro: # the bisexual operators
		return 5
	if _operator in ("<<",">>"):
		return 6
	if _operator in ("<","<=",">",">="):
		return 7
	if _operator in ("==","!="):
		return 8
	if _operator=="&":
		return 9
	if _operator=="^":
		return 10
	if _operator=="|":
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
periodchar="." # integer fraction part separator MDH@27AUG2017 now also a one- and two-character binary operator
declarationchar=":" # for 'declaring' an expression (or a list of expression that can be considered a block)
o=periodchar+"\^"+declarationchar # all one-character binary operators that are not also unary operators
# NOTE more convenient to put ! (possible part of != as binary operator) in the soro operator list, and to remove it from the os list!!!
# MDH@27AUG2017: it's also very convenient to be able to use = as a unary operator which means that the expression that is following should be evaluated
soro="!=-+" # single-character binary or unary operators
ls="(" # starts an argument list
le=")" # ends an (argument) list
ld="," # separates list arguments
w=" \n" # whitespace between tokens (include the newline character now)
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
"""
# MDH@17AUG2017: if we want to be able to change an element of an identifier we need the indexable identifier and the index
class IdentifierElement(Identifier):
	def __init__(self,_identifier,_index):
		Identifier.__init__(self,str(_identifier)+"("+str(_index)+")")
		self.identifier=_identifier
		self.index=_index
	def getValue(self):
		value=self.identifier.getValue() # which should be a list
		if not isinstance(value,list):
			raise Exception("Value of indexed variable "+str(self.identifier)+" not a list.")
		maxindex=len(value) # get the
		indexvalue=self.index #####getValue(self.index) # technically the index thingie
		# technically the index can also be a list (of indices)
		if isinstance(indexvalue,list):
			valuelist=[]
			for index in indexvalue:
				if index>0 and index<=maxindex:
					valuelist.append(value[index])
				else:
					valuelist.append(None)
			return valuelist
		if not isinstance(indexvalue,int):
			raise Exception("Element index not an integer.")
		if indexvalue<1 or indexvalue>len(value):
			raise Exception("Index ("+str(indexvalue)+") of element in "+str(self.identifier)+" out of range.")
		return value[indexvalue]
	def setValue(self,_value):
		value=self.identifier.getValue() # which should be a list
		if not isinstance(value,list):
			raise Exception("Value of indexed variable "+str(self.identifier)+" not a list.")
		maxindex=len(value) # get the length of the list
		indexvalue=self.index #####getValue(self.index) # technically the index thingie
		# technically the index can also be a list (of indices)
		if isinstance(indexvalue,list):
			for index in indexvalue:
				if not isinstance(index,int) or index<=0:
					continue
				while index>maxindex:
					value.append(0)
					maxindex+=1
				value[index]=_value
		if not isinstance(indexvalue,int):
			raise Exception("Element index not an integer.")
		if indexvalue<1 or indexvalue>maxindex:
			raise Exception("Index ("+str(indexvalue)+") of element in "+str(self.identifier)+" out of range.")
		value[indexvalue]=_value
"""
# and here's the dictionary in which the identifiers themselves are stored
# we allow using M as variable, referring to the previously executed commands, given that the value is a list you can change elements (not recommended though)
def getInteger(_value):
	if isinstance(_value,int):
		return _value
	if isinstance(_value,str) and len(_value)>0:
		if _value[0]=='~': # starts with complement 'sign'
			return ~getInteger(_value[1:])
		return int(_value)
	return None
def getValue(_value):
	if DEBUG&8:
		note("Determining the value of "+str(_value)+"...")
	if _value is not None:
		if isinstance(_value,list):
			return map(getValue,_value)
		if isinstance(_value,(int,float)):
			return _value
		if isinstance(_value,str):
			return _value
		# everything else is assumed to have a getValue() method (like Identifier and Expression)
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
	if t[:1] in ts and t[-1:] in te:
		return (t[1:-1],t[:1])
	return (t,ts[0])
def enquote(t,quotechar):
	return quotechar+t+quotechar
def concatenate(operand1,operand2):
	(o1,quotechar)=dequote(stringify(operand1))
	o2=dequote(stringify(operand2))[0]
	return enquote(o1+o2,quotechar)
def repeat(operand1,operand2):
	if isinstance(operand1,(int,float)):
		return repeat(operand2,operand1)
	if isinstance(operand2,(int,float)):
		(o,quotechar)=dequote(stringify(operand1))
		return quotechar+(o*operand2)+quotechar
	return None
def shift(operand,by):
	if by==0:
		return operand
	# MDH@14AUG2017: if operand is alphanumeric we rotate it
	if by<0:
		if isinstance(operand,int):
			return operand>>-by
		(operandtext,quotechar)=dequote(stringify(operand))
		# shift right means cut off the right-hand side and move it to the left-hand side
		l=len(operandtext)
		if l<=1 or ((-by)%l)==0:
			return operand
		shiftby=(-by)%l
		return quotechar+operandtext[-shiftby:]+operandtext[:l-shiftby]+quotechar
	if isinstance(operand,int):
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
# MDH@15AUG2017: the way we're pushing the elements of the expression on the stack, we're always popping the second operand first, then the operator, then the first argument
def getOperationResult(argument2,operator,argument1):
	result=None
	if argument2 is not None and argument1 is not None:
		if operator==declarationchar: # the expression assignment operator (which is very special indeed)
			if not isinstance(argument1,Identifier) and not isinstance(argument1,IdentifierElementExpression):
				raise Exception("Expression destination of type "+str(type(argument1))+" of "+str(argument1)+" not an identifier (element)!") # TODO this error should've been identified by the tokenizer
			if DEBUG&8:
				note("Declaring "+str(argument2)+" as "+str(argument1)+".")
			return (argument1.setValue(argument2)).getValue()
		# MDH@27AUG2017: all other operations require evaluation of the RHS expression!!!
		operand2=getValue(argument2)
		if DEBUG&8:
			note("Computing "+str(argument1)+" "+str(operator)+" "+str(argument2)+"...")
		# with an assignment the left-hand side will not be a 'list' but the right-hand side can be a list to assign
		# so it's easist to deal with the assignment separately
		if operator==assignmentchar:
			if isinstance(argument1,list) and len(argument1)==1:
				operand1=argument1[0]
			else: # which could be an empty list!!!
				operand1=argument1
			if not isinstance(operand1,Identifier) and not isinstance(operand1,IdentifierElementExpression):
				raise Exception("Assignment destination of type "+str(type(argument1))+" of "+str(argument1)+" not an identifier (element)!") # TODO this error should've been identified by the tokenizer
			if DEBUG&8:
				note("Assigning "+str(operand2)+" to "+str(operand1)+".")
			return (operand1.setValue(operand2)).getValue()
		# if assigning do not evaluate the left-hand side
		operand1=getValue(argument1)
		# both operands need not be None
		if operand1 is not None and operand2 is not None:
			# with the period also defined as list concatenation operand we should simply extend operand1 with (listified) operand2
			if operator==periodchar: # the list concatenation operator
				result=list(operand1)
				result.extend(listify(operand2)) # do NOT use listify() on operand1, because we need to actually extend a copy not the original
				return result
			# ok, both elements should be either lists or scalars, at least to apply the non-assignment binary operators to
			# although we should always obtain two list or two items, we make a list of either if need be
			if isinstance(operand2,list):
				if len(operand2)==0:
					return operand1
				if not isinstance(operand1,list):
					return getOperationResult(operand2,operator,[operand1])
				# delist if both arguments are one-element lists
				if len(operand1)==1 and len(operand2)==1:
					return getOperationResult(operand2[0],operator,operand1[0])
				result=[]
				for i in range(0,max(len(operand1),len(operand2))):
					result.append(getOperationResult(getItem(operand2,i),operator,getItem(operand1,i)))
				return result # return as list!!!
			if isinstance(operand1,list):
				if len(operand1)==0:
					return operand2
				return getOperationResult([operand2],operator,operand1)
			if operator=="..": # MDH@27AUG2017: replaced : because : is now the operator to defined a block of (unevaluated) expressions
				if isinstance(operand1,(int,float)) and isinstance(operand2,(int,float)):
					result=[operand1]
					if operand1<operand2:
						while operand1+1<=operand2:
							operand1+=1
							result.append(operand1)
					elif operand1>operand2:
						while operand1-1>=operand2:
							operand1-=1
							result.append(operand1)
			elif operator=="-":
				result=operand1-operand2
			elif operator=="+":
				# a bit of an issue if we have string concatenation which we should or should not allow
				if isinstance(operand1,(int,float)) and isinstance(operand2,(int,float)):
					result=operand1+operand2
				else:
					result=concatenate(operand1,operand2)
			elif operator=="*":
				if isinstance(operand1,(int,float)) and isinstance(operand2,(int,float)):
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
					if isinstance(operand1,int) and isinstance(operand2,int):
						result=operand1/operand2
					else: # Python has a math.trunc() which seems to do just what we want!!
						result=math.trunc(operand1/operand2)
				else:
					raise Exception("Integer division by zero attempted.")
			elif operator=="/": # non-integer division
				if operand2!=0:
					# we'll have to force Python to do non-integer division
					if isinstance(operand1,int) and isinstance(operand2,int):
						result=float(operand1)/operand2
					else:
						result=operand1/operand2
				else:
					raise Exception("Division by zero attempted.")
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
		if DEBUG&8:
			note("Result of applying "+str(operator)+" to "+str(operand1)+" and "+str(operand2)+"="+str(result))
	return result
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

# MDH@22AUG2017: also more reliable to keep any token character is a separate class instance
#								 this can be a character that is to be written (when _color is given) or not
# MDH@23AUG2017: TokenChar is to be used to store a single user input token character exactly
#								 and as much debug information text as one wants
#								 setText should fail if
class TokenChar:
	# write allows additional colored text to be written (even if there's no token character
	def append(self,_towrite,_color=None):
		if not isinstance(_towrite,str):
			return None
		if isinstance(_color,int):
			self.color=_color
		self.writtentext+=write(_towrite,_color)
		return self
	# you can only define significant character text once
	def start(self):
		if self.debug&2:
			self.append("(",DEBUG_COLOR)
	def __init__(self,_debug):
		self.debug=_debug
		self.text=""
		self.writtentext=""
		self.ended=-1 # keep track of how many characters were had before writing the end of tokenchar characters
		self.color=None
		self.error=None
		self.start()
	def end(self):
		if self.ended<0:
			self.ended=len(self.writtentext)
			# keep track of the number of characters actually written (so we can remove them on unend)
			if self.debug&2:
				self.append(")",DEBUG_COLOR)
	def unend(self):
		if self.ended>=0: # return to whatever we had when we ended!!!
			self.writtentext=self.writtentext[:self.ended]
		self.ended=-1
	def isEnded(self):
		return self.ended>=0
	def getWritten(self):
		return self.writtentext
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
		""" replacing:
		self.writtentexts[-1]+=write(_towrite,(self.color,_color)[isinstance(_color,int)])
		return _towrite
		"""
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
		tokenchar=TokenChar(self.debug)
		try:
			self.text.append(tokenchar)
		except Exception,ex:
			tokenchar=None
		return tokenchar
	def getSuffixTokenchar(self,_any):
		tokenchar=None
		if len(self.suffix)>0: # we have tokenchars
			if _any or self.suffix[-1].isEmpty(): # if anything goes, or the last token char is empty return that
				tokenchar=self.suffix[-1]
			# if we get here, we're going to create a new tokenchar, so we should end the last one
			self.suffix[-1].end()
		tokenchar=TokenChar(self.debug)
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
				color=(None,((_color,self.color)[_color is None],-1)[self.color==self.getLastWrittenColor()])[self.output]
				tokenchar.set(_tokenchar,color)
				return self
			self.error="Failed to store "+_tokenchar+"."
		return None
	def start(self):
		# NOTE by NOT producing any debug output when _tokenchar is NOT defined (typically None), as is the case with expressions
		#			 there's no initial expression token prefix
		if self.output:
			if self.debug&6: # something to write immediately
				if self.debug&2: # immediately write the start of token text
					self.writtenprefix+=write('[',DEBUG_COLOR) # an empty token character
				if self.debug&4:
					self.writtenprefix+=write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR)
			""" replacing:
			self.writtentexts=[] # start with empty list
			if self.debug&6: # something to write immediately
				self.writtentexts.append("")
				if self.debug&2: # immediately write the start of token text
					self.write('[',DEBUG_COLOR)
				if self.debug&4:
					self.write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR)
			"""
		else: # no need to keep track of the written text
			pass
			""" replacing:
			self.writtentexts=None
			"""
	def __init__(self,_tokentype,_debug=None,_tokenchar=None):
		self.debug=_debug # do NOT change DEBUG while constructing a token????
		self.error=None # MDH@21AUG2017: the backspace() method requires the use of self.error here as well
		self.text=[] # replacing: "" # the meaningful text
		self.suffix=[] # replacing: "" # what's appended to the token AFTER it ends (typically whitespace or a comment)
		self.output=isinstance(_debug,int) # whether we should output anything at all
		self.continuable=True # assume to be continuable to start with
		self.ended=False # not ended until end() is actually called!!!
		self.setType(_tokentype)
		# what used to go in start
		### added: prefix / infix / postfix written stuff initialized to empty strings
		self.writteninfix=""
		self.writtenprefix=""
		self.writtenpostfix=""
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
			if self.output:
				if self.debug&2: # indicates the start of the suffix (if any)
					self.writteninfix+=write("|",DEBUG_COLOR) ###self.write("|",DEBUG_COLOR)
		return result
	def unendText(self):
		if len(self.text)>0:
			self.text[-1].unend()
	def undiscontinued(self): # we might want to undiscontinue (when the suffix is removed)
		result=not self.continuable
		if result:
			self.continuable=True
			self.unendText() # e.g. to be overridden by subclasses
			if self.output:
				if self.debug&2: # indicates the start of the suffix (if any)
					self.writteninfix=""
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
			if self.output:
				if self.debug&2:
					self.writtenpostfix=write(']',DEBUG_COLOR)
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
			if self.output:
				if self.debug&2:
					self.writtenpostfix=""
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
	def getWritten(self):
		return self.writtenprefix+self.getWrittenText()+self.writteninfix+self.getWrittenSuffix()+self.writtenpostfix
	# getRepresentation() returns the type in gray and the text itself in black
	def getRepresentation(self):
		return getColorText(INFO_COLOR)+' '+self.getText()+getColorText(DEBUG_COLOR)+":"+getTokentypeRepresentation(self.type)
	def ignore(self,_tokenchar): # any whitespace that's in the token needs to be displayed but does not change the type
		# TODO perhaps it's better to change this is making this thing discontinuable, and then add it
		# we'll be appending at least one character
		if isinstance(_tokenchar,str) and len(_tokenchar)>0: # TODO this should be an assertion
			self.discontinued() # the discontinuation debug text should come in front of the first suffix token char
			self.getSuffixTokenchar(False).set(_tokenchar,(-1,self.color)[self.output]) # TODO what color????
			if len(self.suffix)>0: # very likely though
				return self
			self.error="Failed to 'ignore' "+_tokenchar+"."
		return None
		""" replacing:
		if self.output:
			self.writtentexts.append("") # a new text to be written
		self.discontinued() # remember whether or not discontinued for the first time
		if self.output:
			self.suffix+=self.write(_tokenchar)
		else:
			self.suffix+=_tokenchar
		"""
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
				self.append(periodchar,OPERATOR_COLOR) # show in the operator color
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
		if len(self.suffix)>0:
			self.suffix.pop() # very convenient
			# NOTE never force continuability until actually removing a significant token
			#			 BUT that's a problem because sometimes the thing is not continuable AND there's no suffix
			if len(self.suffix)>0:
				self.suffix[-1].unend()
			return self
		l=len(self.text)-1 # index of the last tokenchar
		if l>=0:
			removedtokenchar=self.text.pop() # very convenient
			# we might need to change the token type depending on what is removed...
			if self.type==REAL_TOKENTYPE:
				# removing the tokenchar that contains the period?
				if removedtokenchar.getText()[-1]==periodchar:
					self.type=INTEGER_TOKENTYPE
			elif self.type==OPERATOR_TOKENTYPE:
				# removing the second character of a two-character operator???
				if l>0: # still tokens left, so reset the type
					self.type=1+os.find(self.text[-1].getText())
			#### TODO should we do this here??????? self.undiscontinued() # return to being continuable again for certain
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
	# NOTE setType() won't change the coloring...
	def setType(self,_tokentype):
		self.type=_tokentype
		if self.output:
			self.color=getTokentypeColor(self.type) # initiate the color to use when writing once
		# TODO how do we want to treat whitespace?????
		if self.type<=0: # only whitespace characters allowed, so everything that follows is whitespace!!
			self.discontinued()
		return self.type
	def __repr__(self):
		return self.getText()
	def __str__(self):
		return self.getText()
""" replacing:
# MDH@29JUL2017: it's more convenient/reliable to remember the token in a separate class
# MDH@30JUL2017: let Token itself keep track of what was written by it, so it can reproduce it
# MDH@01AUG2017: Token writes without a color i.e. calls the main write()
class Token:
	# NOTE do NOT call write unless self.output is True
	def write(self,_towrite,_color=None):
		self.writtentexts[-1]+=write(_towrite,(self.color,_color)[isinstance(_color,int)])
		return _towrite
	def append(self,_tokenchar):
		# if not of the right type throw an exception
		if not isinstance(_tokenchar,str):
			raise Exception("Type of item to append to token text not text.")
		if len(_tokenchar)>0: # something to append for real
			if self.output:
				self.writtentexts.append("") # a new text element starts
				self.text+=self.write(_tokenchar)
			else: # just append as is
				self.text+=_tokenchar
	def __init__(self,_tokentype,_tokenchar=None,_output=True):
		self.debug=DEBUG # do NOT change DEBUG while constructing a token????
		self.error=None # MDH@21AUG2017: the backspace() method requires the use of self.error here as well
		self.text="" # the meaningful text
		self.suffix="" # what's appended to the token AFTER it ends (typically whitespace or a comment)
		self.output=_output # whether we should output anything at all
		self.continuable=True # assume to be continuable to start with
		self.ended=False # not ended until end() is actually called!!!
		self.setType(_tokentype)
		# what used to go in start
		if self.output:
			self.writtentexts=[] # start with empty list
			if self.debug&6: # something to write immediately
				self.writtentexts.append("")
				if self.debug&2: # immediately write the start of token text
					self.write('[',DEBUG_COLOR)
				if self.debug&4:
					self.write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR)
		else: # no need to keep track of the written text
			self.writtentexts=None
		# append whatever token we received
		if isinstance(_tokenchar,str):
			self.append(_tokenchar)
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
			if self.output:
				if self.debug&2:
					self.write("|",DEBUG_COLOR)
		return result
	def undiscontinued(self): # we might want to undiscontinue (when the suffix is removed)
		result=not self.continuable
		if result:
			self.continuable=True
			# TODO what else????
		return result
	def end(self):
		if not self.ended: # once suffices!!
			self.ended=True # mark as discontinuable although perhaps it's better not to if I'm not discontinued somehow, in which case it remains continuable even though it ended!!!
			# any operator that might have been continued, register it as operator immediately, so one cannot continue it with the second character!!!
			if self.type>0 and self.type<OPERATOR_TOKENTYPE:
				self.type=OPERATOR_TOKENTYPE
			if self.output:
				if self.debug&2:
					self.write(']',DEBUG_COLOR)
		return self
	def unend(self): # which undo any assumed end (what we'll do with the last token in an expression), so it can be continued again
		# unending doesn't change the continuability (anymore)
		if self.ended: # something to unend, therefore we have to remove the ] written at the end
			self.ended=False
			if self.output:
				if self.debug&2:
					if len(self.writtentexts[-1])>0:
						self.writtentexts[-1]=self.writtentexts[-1][:-1] # cut off the last character written (which would be the ] character!!!)
		return self
	def getWritten(self):
		written=""
		if self.writtentexts is not None:
			for writtentext in self.writtentexts:
				written+=writtentext
		return written
	# getRepresentation() returns the type in gray and the text itself in black
	def getRepresentation(self):
		return getColorText(INFO_COLOR)+' '+self.text+getColorText(DEBUG_COLOR)+":"+getTokentypeRepresentation(self.type)
	def ignore(self,_tokenchar): # any whitespace that's in the token needs to be displayed but does not change the type
		# TODO perhaps it's better to change this is making this thing discontinuable, and then add it
		# we'll be appending at least one character
		if self.output:
			self.writtentexts.append("") # a new text to be written
		self.discontinued() # remember whether or not discontinued for the first time
		if self.output:
			self.suffix+=self.write(_tokenchar)
		else:
			self.suffix+=_tokenchar
		return self
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
		self.append(_tokenchar)
		return self
	# MDH@21AUG2017: removing the last character is fun
	def backspace(self):
		# NOTE it's possible that we're NOT continuable AND there's no suffix!!!
		#			 it's also possible that a character is not whitespace in which case we need to remove another character
		# NOTE we shouldn't forget to remove the last writtentexts as well
		if not self.continuable: # in the suffix (if any)
			toremove=self.suffix[-1] # the last character of the suffix to remove
			note("Removing character '"+toremove+"' from suffix '"+self.suffix+"'...")
			del self.writtentexts[-1]
			self.suffix=self.suffix[:-1]
			# if the suffix is now empty, we're continuable again
			if len(self.suffix)==0:
				self.continuable=True
			# TODO is this true?????
			if toremove in w: # a whitespace character was removed, and so we're done
				return self
		# if we get here, we're supposed to remove the last character of self.text
		tokentext=self.text
		if len(tokentext)==0:
			self.error="Please report the following bug: No character left in token to remove!"
			return None
		self.text=tokentext[:-1] # token character removed...
		del self.writtentexts[-1]
		return self
	def getText(self):
		result=self.text
		# append all non-w characters in the suffix
		for sch in self.suffix:
			if sch in w:
				break
			result+=sch
		return result
	def getType(self):
		return self.type
	# NOTE setType() won't change the coloring...
	def setType(self,_tokentype):
		self.type=_tokentype
		if self.output:
			self.color=getTokentypeColor(self.type) # initiate the color to use when writing once
		# TODO how do we want to treat whitespace?????
		if self.type<=0: # only whitespace characters allowed, so everything that follows is whitespace!!
			self.discontinued()
		return self.type
	def __repr__(self):
		return self.text
	def __str__(self):
		return self.text
"""
# we have to either choose to append a token immediately when it is created, or until it ends (as we used to)
# nevertheless we can keep track of the current token in self.token (which is the active token)
# and as long as we let the token's add method to do the writing, and the constructor to write the tokens color
# it's going to be OK
# NOTE by making Token.add() method return the token itself, we can replace self.token=tokenchar by self.token=Token(<type>).add(tokenchar) conveniently
# if we make Expression a Token as well, we can store subexpression as tokens itself
# we simply need to override some of the simple Token methods
class Expression(Token):
	"""
	def notoken(self): # only to be called when self.token is not None
		# show the type of the token label if so requested
		if DEBUG&4:
			self.token.write(':'+getTokentypeRepresentation(self.token.getType()),DEBUG_COLOR)
		# mostly in combination with the above, show the end of token character
		self.token.end() # which will take care of writing the ] if need be
		self.token=None # the current token (as long as it wasn't recognized yet)
	"""
	def reset(self):
		# no need to keep track of the expression and/or written expression anymore with the tokens in place
		self.tokens=[]
		# alternatively we can start with a 'whitespace' token (all the other whitespace is appended to the token)
		self.token=None # which also starts the optional whitespace token!!!
	# how about using the Expression itself to store the whitespace at the beginning????
	def start(self):
		# NOTE overrides Token.start() i.e. should be called through the Token constructor
		#			 there's no initial expression token prefix
		if self.output:
			if self.debug&6: # something to write immediately
				if self.debug&2: # immediately write the start of token text
					self.writtenprefix+=write('{',DEBUG_COLOR) # an empty token character
				if self.debug&4:
					self.writtenprefix+=write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR)
			""" replacing:
			self.writtentexts=[] # start with empty list
			if self.debug&6: # something to write immediately
				self.writtentexts.append("")
				if self.debug&2: # immediately write the start of token text
					self.write('[',DEBUG_COLOR)
				if self.debug&4:
					self.write(getTokentypeRepresentation(self.type)+":",DEBUG_COLOR)
			"""
		else: # no need to keep track of the written text
			pass
			""" replacing:
			self.writtentexts=None
			"""
	def __init__(self,_environment,_debug=None,_parent=None,_tokenchar=None):
		Token.__init__(self,EXPRESSION_TOKENTYPE,_debug,_tokenchar)
		self.declared=False # initially assumably not declared...
		self.parent=_parent # supposedly the parent expression to revert to when receiving the ld or le character
		self.environment=_environment # MDH@30AUG2017: knows it's environment, so it can check for the existance of certain variables, when being composed
		self.newidentifiers=[] # MDH@30AUG2017: keep track of any identifiers declared in subexpressions
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
		return self.environment.identifierExists(_identifiername) or self.initializedIdentifier(_identifiername)
	def identifiersExistStartingWith(self,_identifierprefix):
		# if in the global pool, we're done immediately
		if self.environment.identifiersExistStartingWith(_identifierprefix):
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
		if self.environment.functionsExistStartingWith(_functionprefix):
			return True
		# my parent might have them
		if self.parent is not None:
			if self.parent.functionsExistStartingWith(_functionprefix):
				return True
		# NOPE nobody
		return False
	def getFunctionIndex(self,_identifiername):
		functionindex=self.environment.getFunctionIndex(_identifiername)
		if functionindex<=0 and self.parent is not None:
			functionindex=self.parent.getFunctionIndex(_identifiername)
		return functionindex
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
		if self.token is not None: # a previous token to end
			self.token.end()
		elif len(self.text)>0: # some insignificant text at the beginning of the expression to end
			self.text[-1].end()
	# newToken changed a bit so it doesn't require a character to add per se
	def newToken(self,_token):
		self.tokens.append(_token)
		self.token=self.tokens[-1] # ascertain that self.token equals the last token on the tokens list
		return self.token
	def addToken(self,_tokentype,_tokenchar,_output):
		self.endToken() # end whatever token is pending FIRST i.e. BEFORE actually creating the new token (which might be writing debug info)
		if _tokentype<=0: # expression to add
			token=Expression(self.environment,(None,self.debug)[_output],self,_tokenchar)
		else:
			token=Token(_tokentype,(None,self.debug)[_output],_tokenchar) # immediately push the new token on top of the stack
		return self.newToken(token)
	# we can make add return the active expression, to replace the active expression
	# NOTE only whitespace tokens can return a negative value??? this makes it harder to know when a token is still active????
	# we might consider returning None when an error occurs
	def getError(self):
		return self.error
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
			if self.output:
				if self.debug&2:
					self.writtenpostfix=write('}',DEBUG_COLOR)
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
			if self.output:
				if self.debug&2:
					self.writtenpostfix=""
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
	def add(self,_tokenchar,_output=True):
		# default result is the current expression itself
		result=self # the default result is self
		self.error=None # to store the error in
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
									# but if the current expression is an IdentifierElementExpression, so should the next one be
									if isinstance(self,IdentifierElementExpression):
										result.endToken() # end me
										result=self.newToken(IdentifierElementExpression(self.getIdentifier(),self.environment,(None,self.debug)[_output],result,_tokenchar)) # pretty neat (if it works)
									else: # a normal expression to be added to the parent
										result=result.addToken(0,_tokenchar,_output) # we're appending a new expression to the parent (effectively ending this expression token), and continuing with the new subexpression
								else:
									self.ignore(_tokenchar) # append the closing parenthesis token in the suffix of this expression (so no longer ends up as a separate token)
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
								if self.getFunctionIndex(tokentext)==0: # not a function therefore NOT allowed
									# now allowed to index an existing variable of which the current value is a list (i.e. list)
									if self.identifierExists(tokentext): # an existing variable # MDH@30AUG2017: allow for 'locally' defined identifiers as well
										identifiervalue=identifiers[tokentext].getValue()
										if isinstance(identifiervalue,list): # can be indexed
											# we're going to replace the identifier by an IdentifierElementExpression
											self.endToken() # have to do this explicitly here because I removed it from newToken() (and into addToken())
											result=self.newToken(IdentifierElementExpression(tokentext,self.environment,(None,self.debug)[_output],self,_tokenchar)) # have it use the same debug level!!!
											_tokenchar=None # prevents creation of an expression below
										else:
											self.error="Cannot index a variable which value (of type "+str(type(identifiervalue))+") is not a list."
									else:
										self.error=_tokenchar+" not allowed behind a non-existing variable."
							else:
								self.error=_tokenchar+" not allowed behind a literal."
						if self.error is None and _tokenchar is not None:
							result=self.addToken(0,_tokenchar,_output)
					elif _tokenchar in ts:
						# starting a string literal is not allowed in most situations because most operators do not operate on string literals
						# basically a string literal can only occur behind the + and * binary operator and the comparison operators
						# or the assignment operator, so that's + *	 < <= > >= != == and =, and the rest is prohibited
						# and also not behind any of the signs
						if abs(tokentype)>=SIGN_TOKENTYPE: # everything starting at signs can never precede a string literal
							self.error="String literal not allowed here!"
						elif tokentype!=0: # this leaves the operators
							# only the first four unfinished operator are acceptable i.e. < or > or = or * but not the rest i.e. & | / and %
							# we might consider ending the operator token if need be so that all have the same type
							# alternatively, it's easiest to just look at the token text
							# which should be < > = * + (as single character operators) or <= >= == != which is anything that ends with =
							tokentext=self.token.getText()
							if tokentext[-1]!="=" and tokentext!="<" and tokentext!=">" and tokentext!="+" and tokentext!="*":
								self.error="String literal not allowed behind operator "+tokentext+"."
						if self.error is None:
							self.addToken(SINGLEQUOTED_TOKENTYPE+ts.index(_tokenchar),_tokenchar,_output)
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
								if _output: # too bad we have to do that here!!
									backspace()
								self.addToken(OPERATOR_TOKENTYPE,periodchar,_output).add(periodchar).discontinued()
							else: # backspace() on the token failed somehow...
								self.error=self.token.getError()
						elif abs(tokentype)<=SIGN_TOKENTYPE: # behind a unary or binary operator (or when tokentype equals 0 at start of expression)
							# starts a number literal immediately BUT only with a zero in front of it
							# NOTE I cannot use our special trick to indicate an automatic insert here (i.e. by putting it in the suffix)
							self.addToken(INTEGER_TOKENTYPE,"0",_output).add(periodchar)
						elif tokentype==INTEGER_TOKENTYPE: # in an integer, thus a number literal continuation
							########self.token.setType(REAL_TOKENTYPE) # switch over to being a number MDH@27AUG2017: the token should now take care of switching to REAL_TOKENTYPE!!!
							self.token.add(_tokenchar)
						elif abs(tokentype)>=IDENTIFIER_TOKENTYPE or abs(tokentype)==EXPRESSION_TOKENTYPE: # in/behind an identifier or expression, as list concatenation operator
							# MDH@25AUG2017: if we use the period as list concatenation operator as well, the current token needs to evaluate to a list
							#								 the question is whether we actually want to evaluate what's in front of this thing here
							self.addToken(OPERATOR_TOKENTYPE,_tokenchar,_output)	#### MDH@27AUG2017: do NOT discontinue because another period character defines the .. operator!!!!.discontinued()
							#### replacing allowing the period as part of the identifier: self.token.add(_tokenchar)
						else:
							self.error="Period not allowed here."
					else: # not the start (end) of string literal, the start or end of a subexpression, whitespace
						# ALL CODE ABOVE SHOULD BE SELF_CONTAINED BECAUSE ALL CODE BELOW FIRST CHECKS CONTINUATION FOLLOWED BY CREATING NEW TOKENS
						# it's probably best to deal with some of the possible input characters first and determine when they are not allowed
						# you can typically NOT start a string literal in a lot of places e.g. there are not very many operations allowed on it
						# NOTE do NOT forget to end any current token (this would be when the token type is positive)
						if abs(tokentype)>0 and abs(tokentype)<OPERATOR_TOKENTYPE: # behind a binary operator (if a single-character operator this might be the second character
							# expecting either the continuation of the two-character operator or something that is NOT a binary operator
							# given that this character is a operator by itself, another operator character is not allowed
							# unless it's one of the characters that allowed to follow it
							# any subsequent character ends the operator token
							# it's a little easier to use o2 to determine whether the new token is the second character of a two-character binary operator
							# NOTE there's NO need to check when tokentype=8 because in that case it's either already a two-character operator or a single-character operator
							#			 that can not be continued (so in fact tokentype 8 indicates a finishes token, in which case tokentype I guess would be -8
							#			 in which case the token is already finished, and our new token should start a new token if possible
							operatortext=self.token.getText()
							secondoperatorchar=(o2.find(" "+operatortext+_tokenchar)>=0)
							# MDH@23AUG2017: you cannot interrupt a binary operator (so if there's whitespace and tokentype is negative)
							#								 it's illegal, TODO prevent this from happening by ??????
							if tokentype>0 and secondoperatorchar: #### replacing:	 _tokenchar in so[tokentype-1]: # the second character of the two-character operator
								# we should NOT allow using == as operator behind an identifier that has not yet been defined
								# although it's not always true that the == operator is applied to the value of this non-existing identifier per se
								if len(self.tokens)>0 and self.tokens[-1].getType()==IDENTIFIER_TOKENTYPE and not self.identifierExists(self.tokens[-1].getText()):
									self.error="It is not allowed to apply the equal comparison operator to a non-existing variable."
								elif tokentype<=2 and len(self.tokens)>0 and operatortext==_tokenchar and self.tokens[-1].getType()==REAL_TOKENTYPE:
									# someone is trying to apply the shift operator to a real number
									self.error="It is not possible to shift a real number."
								else:
									if self.token.add(_tokenchar) is None: # append to create the two-character binary operator
										self.error="Failed to create the two-character operator."
									_tokenchar=None # no need to add the character to any (new) token
							else:
								# any character that unambiguously starts a binary operator should be prohibited
								# any other character either in a, A, d, (, ), ' " is allowed
								if _tokenchar in os or _tokenchar in o:
									if _tokenchar!=assignmentchar: # TODO not very neat that = is also in os whereas it can also be a soro
										if secondoperatorchar:
											self.error="It is not allowed to separate operator characters."
										else:
											self.error="Binary operator "+(("(start) ","")[_tokenchar in o])+_tokenchar+" not allowed behind operator "+operatortext+"."
							# still something left to do if no error occurred
							if self.error is None:
								# end of binary operator anyway
								self.token.setType(OPERATOR_TOKENTYPE) # hmm, not sure whether I like this (TODO if we change the coloring, any token who's type changes would need to be rewritten)
								self.token.end() # MDH@24AUG2017: we should NOT discontinue an operator that could still be continued (if behind a string literal we should though!!!)
								# _tokenchar could still represent a sign operator
								if _tokenchar is not None:
									if _tokenchar in s or _tokenchar in soro: # a unary operator
										# add the unary operators
										self.addToken(SIGN_TOKENTYPE,_tokenchar,_output).discontinued()
										_tokenchar=None # don't append again!!
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
								tokentext=self.getLastTokenText()
								functionindex=self.getFunctionIndex(tokentext)
								if functionindex>0: # a function name, and only ( is basically allowed behind it
									if not _tokenchar in ls:
										self.error="Function "+tokentext+" should now be applied to an argument (inside parentheses)."
								elif _tokenchar==declarationchar: # doesn't matter if the thing is already declared or not
									# similar to what happens when an opening parenthesis is encountered
									# if we do NOT give it a parent only the Enter key can end it (which is exactly what we want)
									# except that we won't be able to find the parent anymore (and we'd have to remember the main expression elsewhere)
									self.addToken(OPERATOR_TOKENTYPE,declarationchar,_output) # same as with the assignment operator
									self.endToken() # have to do this explicitly here because I removed it from newToken() (and into addToken())
									result=self.addToken(0,"",_output).flagAsDeclared() # mark as being declared, so we can end it with Enter
									_tokenchar=None
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
										self.addToken(OPERATOR_TOKENTYPE,assignmentchar,_output).discontinued() # thus allowing whitespace but NOT another = or : sign!!!
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
												self.addToken(SIGN_TOKENTYPE,_tokenchar,_output).discontinued()
											else:
												self.error="Can't start with an operator."
										elif _tokenchar==assignmentchar and self.tokens[-1].getType()<IDENTIFIER_TOKENTYPE: # not an assignment
											# unless, we're behind an identifier element expression
											if self.tokens[-1].getType()!=EXPRESSION_TOKENTYPE or not isinstance(self.tokens[-1],IdentifierElementExpression):
												# force equal is comparison operator
												# if we want to be able to undo the entire token with backspace
												# we move the second token character directly in the 'whitespace' suffix so we can recognize that situation
												self.addToken(OPERATOR_TOKENTYPE,_tokenchar+_tokenchar,_output).discontinued() # instead of 'ignoring' the second character, we put both in ONE token char and discontinue the lot
												if _output:
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
												self.addToken(OPERATOR_TOKENTYPE,_tokenchar,_output).discontinued()
												########self.token.end() #### replacing: tokentype=self.setTokentype(self.tokenends())
											else:
												tokentype=self.setTokentype(osindex+1)
									elif osindex==0: # assumed to be the unary = operator
										self.addToken(SIGN_TOKENTYPE,_tokenchar,_output).discontinued()
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
											self.addToken(OPERATOR_TOKENTYPE,_tokenchar+assignmentchar,_output).discontinued() # todo more likely the equal-to-character
											if _output: # interactive mode
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
									self.addToken(tokentype,_tokenchar,_output)
									# we can see in the previous M implementation (commented out above) that if the token type was set to 8 or 9 the token also ends
									if tokentype==OPERATOR_TOKENTYPE or tokentype==SIGN_TOKENTYPE:
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
		return result
	def getWritten(self,_showcomment=True):
		# being a token means that there might be a writtenprefix (i.e. something written in front of the first character)
		written=self.writtenprefix+Token.getWrittenText(self) # the whitespace in front of the expression, but should I call getWritten??????
		if self.debug&32:
			written+=getColoredText(":0",33)
			ti=0
		#### replacing: result=self.text
		for token in self.tokens:
			written+=token.getWritten()
			if self.debug&32:
				ti+=1
				written+=getColoredText(":"+str(ti),33)
		if _showcomment:
			written+=self.writteninfix # is this to be placed here?????
			written+=self.getWrittenSuffix() # replacing: self.suffix
			if self.debug&32:
				ti+=1
				written+=getColoredText(":"+str(ti),33)
		written+=self.writtenpostfix
		return written
	def getText(self):
		text=Token.getText(self) ### replacing: self.text
		for token in self.tokens:
			text+=token.getText()
			if isinstance(token,Expression):
				text+=token.getSuffix() ### replacing: token.suffix
		text+=Token.getSuffix(self)
		return text
	def echo(self,_showcomment=True):
		# what we'd want is to have the main expression rewritten in this case, so we have to find the top expression (that has no parent)
		expression=self
		while expression.parent is not None:
			expression=expression.parent
		sys.stdout.write(expression.getWritten(_showcomment))
	def __str__(self):
		return self.getText() # write the whitespace at the beginning as well!!!
	# override Token.getRepresentation() to return the representation of the list of tokens
	def getRepresentation(self):
		representation=""
		for token in self.tokens:
			representation+=" "+token.getRepresentation()
		return representation.strip()
	# if we pass the environment to getValue() which I suppose should then better be called evaluate or evaluatesTo we should ascertain that any subexpression
	# that we push on elements actually wraps the expression in an ExpressionEvaluator
	# that way getOperationResult() and Function.getValue() never sees any expression that does NOT know it's environment
	def getValue(self,_environment=None):
		# best not to end with a period, given the possible color showing the last token
		value=undefined.getValue() # which at the moment is also None, so cannot be used to determine whether or not an error occurred!!!!
		self.error=None
		try:
			if self.debug&1:
				valueText=self.getRepresentation()
			# MDH@18AUG2017: an expression with no tokens will return the undefined identifier!!!
			#								 in order to be able to assign this we need to return the empty list!!!
			if len(self.tokens)>0 or len(self.text)==0 or not (self.text[0] in ls): # not an empty subexpression
				# MDH@15AUG2017: instead of keeping separate list to store the operators and arguments it's a good idea to create an expression that will contain the end result
				#								 of the evaluation of the tokens by applying the functions and binary operators
				#								 the point is that if we allow argument lists with multiple arguments (=values), it's easiest to store the list of these arguments in a single argument
				#								 to which the function is to be applied, then the function has to take care of processing the list and apply itself to the number of arguments it needs
				########evaluatedexpression=Expression() # the expression to populate with the values of the successive tokens and operators to apply
				elements=[] # arguments (functions and values) and operators intertwined
				# as we will be applying functions to arguments multiple times, we create a subfunction to do that for us
				def applyFunctions():
					# MDH@19AUG2017: we can do this another way:
					#								 1. find the last function to apply if any
					#								 2. pass the remaining arguments into the function and append the returned result
					#								 for now assume that a function will not return another function, or perhaps it will???
					""" the following should have worked (better) but it didn't don't know wy yet TODO
					l=len(elements)
					while l>0:
						l-=1
						if isinstance(elements[l],Operator):
							break
						if not isinstance(elements[l],Function):
							continue
						note("Applying function "+str(elements[l])+" to "+str(elements[l+1:])+" (position: "+str(l)+").")
						# a function at position l to apply to all elements behind this position
						arguments=elements[l+1:]
						del elements[l+1:]
						elements[l]=elements[l].getValue(arguments)
					"""
					# replacing the previous solution (18AUG2017)
					# we do NOT want a scalar to be turned into a list which will happen because the arguments are 'enlisted' in the first step
					# to apply any functions to
					# the question is whether or not we should 'delist' them before applying the next function
					# functions typically accept an argument list, so if multiple functions are to be applied
					# each function result should also be 'enlisted' before applying the next function
					# here the problem is that an identifier can be indexed by an expression representing the index
					# this should be solved by replacing Identifier + expression by an expression that can have an identifier
					# so it's still an expression
					# 1. POP OFF ALL ARGUMENTS
					######note("Popping arguments!")
					arguments=[] # the list of arguments, there should be at least one
					while len(elements)>0 and not isinstance(elements[-1],Operator) and not isinstance(elements[-1],Function):
						arguments.insert(0,elements.pop())
					# 2. APPLY ALL FUNCTIONS
					while len(elements)>0 and isinstance(elements[-1],Function):
						function=elements.pop().setDebug(self.debug) # make the function take over
						if self.debug&8:
							note("Applying function "+str(function)+" to arguments "+str(arguments)+".")
						arguments=function.getValue(arguments)
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
						""" MDH@25AUG2017: if someone wants to keep multiple elements they can just append None values to the end of a list
						else:
							while len(arguments)>0 and arguments[-1]==undefined.getValue():
								del arguments[-1]
						"""
					elements.append(arguments) # which might be an empty list...
				# process the tokens one at a time
				# if we take the priorities into account
				tokenindex=0
				for token in self.tokens:
					tokenindex+=1
					if token is None:
						continue
					tokentype=token.getType()
					######note("Processing token "+str(token)+" of type "+str(tokentype)+"...")
					# as soon as we encounter a comment we're definitely done (so far)
					# TODO we can basically put the comment part in the suffix part of Expression (being a Token itself)
					""" won't happen anymore!!!
					if tokentype==COMMENT_TOKENTYPE:
						break
					# NOTE we'll be storing whitespace with the negative value of the token in front of it (if any), so we can simply skip it
					if tokentype<=0:
						continue
					# if ( or ) around a sub expression, skipping is easiest
					if tokentype==CLOSINGPARENTHESIS_TOKENTYPE:
						continue
					if tokentype==OPENINGPARENTHESIS_TOKENTYPE: # we can have nothing in front of it or a sign or a function name
						continue
					"""
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
								elements.append(getOperationResult(elements.pop(),elements.pop().getText(),elements.pop())) # pretty neat to be able to do it this way (but I rewrote getOperationResult to accept the 2nd argument first!!!)
							except Exception,ex:
								self.error=str(ex)
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
							# do NOT evaluate right now, because we might be trying to assign to it
							# NO do NOT ask for the value of the token when dealing with an identifier element expression
							#		 because we might be assigning to it!!!
							if isinstance(token,IdentifierElementExpression): # always behind an identifier argument
								if isinstance(elements[-1],Identifier): # if the previous element on the element stack is the actual indexed identifier (as there should be for the first identifier element expression)
									elements[-1]=ExpressionEvaluator(token,_environment) # replace the identifier argument (just put on the stack)
									continue # i.e. do not append to elements (see below)
								# TODO we need to combine it with the identifier element expression in front of it!!!
							argument=ExpressionEvaluator(token,_environment) ######.getValue() # we need to evaluate it anyway!!!
						elif tokentype==IDENTIFIER_TOKENTYPE: # some identifier, either a function or an identifier
							# although an identifier can also be a function, we allow using function names as identifiers, so it depends on what's behind the identifier name
							# whether it's a function or identifier
							# on the other hand if there's nothing behind the identifier it's an existing identifier
							# so if it's an existing identifier assume it's an identifier, and correct when an opening parenthesis comes next
							functionindex=self.getFunctionIndex(tokentext)
							if functionindex>0:
								argument=Function(functionindex) # remember the function until we have the argument to apply it to
							else: # identifier that does not yet exist
								argument=_environment.getIdentifier(tokentext)
						else: # anything else (which is stored as text)
							argument=getValue(tokentext) # like an expression
						# MDH@15AUG2017: if we allow as many arguments as possible, we cannot immediately apply the functions to an argument, not until we come across an operator
						#								 as soon as we come across the operator we should the functions to ALL arguments
						"""
						# apply all preceding function to anything that is not a function (which is simply appended)
						if argument is None or not isinstance(argument,Function):
							# apply all functions at the top of the argument stack to the argument i.e. effectively removing the functions
							while len(arguments)>0 and isinstance(arguments[-1],Function):
								argument=arguments.pop().getValue(argument) # the argument might be an identifier bro
							# with all functions applied in the proper (right-to-left) order, we end up with either the first or second argument to any binary operator
						"""
						#####if argument is not None:
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
							####note("Applying final operators!")
							if len(elements)>2: # we should have at least an operator in front of it
								elements.append(getOperationResult(elements.pop(),elements.pop().getText(),elements.pop()))
						except Exception,ex:
							self.error=str(ex)
							break
				if self.error is None:
					if self.debug&8:
						note("Final result: "+str(elements)+".")
					if len(elements)==0: # we should end with one argument and no operators
						self.error="No operands left."
					elif len(elements)>1:
						self.error="Too few operators."
				if len(elements)>0: # apparently not an intermediate result at all
					######note("Evaluating the result of the expression evaluation: "+str(elements)+".")
					value=getValue(elements[0])
				else:
					value=getValue(elements)
				if self.debug&1:
					output("\n\t"+valueText)
					write(" = ",0)
					if value is None:
						output("(Undefined)")
					else:
						output(str(value))
			else: # no tokens and a subexpression
				value=[] # empty list therefor
		# the first argument might still have been left unevaluated, e.g. when a single identifier is typed!!!
		except Exception,ex:
			value=None
			if self.error is None:
				self.error=str(ex)
		return value
	def isEmpty(self):
		return self.token is None and len(self.text)==0
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
		self.error=None
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
						if isinstance(self.token,Expression): # we've deleted a tokenchar in a subexpression, that must have been the closing parenthesis
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
					beep()
		else: # in the suffix (comment part)
			if len(self.suffix)>0:
				self.suffix.pop() ### replacing: self.suffix=self.suffix[:-1]
				if len(self.suffix)==0: # comment character removed
					self.undiscontinued() # which will call unendText() on success (which we have to override to prevent Token.unendText() to unend the last tokenchar in self.text
				else:
					self.suffix[-1].unend()
			else:
				self.error="Please report the following bug: no comment characters left to remove."
		if self.error is not None:
			return None
		return result
# MDH@17AUG2017: when an identifier is 'applied' to an expression the expression indicates an index
# such an expression behaves like any other expression except that it returns the value
class IdentifierElementExpression(Expression):
	def __str__(self):
		return self.identifiername+Expression.__str__(self)
	def __init__(self,_identifiername,_environment,_parent=None,_debug=None,_tokenchar=None):
		Expression.__init__(self,_environment,_parent,_debug) # no passing _tokenchar (yet)
		# copy all token characters over from the identifier token
		self.identifiername=_identifiername
		self.indexvalue=None # no need to evaluate more than once!!!
		if isinstance(_tokenchar,str):
			self.append(_tokenchar)
	def getIdentifier(self):
		return self.identifiername
	# an additional method to get at the value of this expression returns the index value
	def getIndexValue(self):
		if self.indexvalue is None:
			self.indexvalue=Expression.getValue(self)
		return self.indexvalue
	def getValue(self,_environment):
		######note("Value of an element of "+str(self.identifiername)+" requested.")
		identifier=_environment.getExistingIdentifier(self.identifiername)
		if identifier is None:
			raise Exception("Identifier "+self.identifiername+" vanished.")
		value=identifier.getValue() # which should be a list
		if not isinstance(value,list):
			raise Exception("Value of indexed variable "+self.identifiername+" not a list.")
		maxindex=len(value) # get the
		indexvalue=self.getIndexValue()
		# technically the index can also be a list (of indices)
		if isinstance(indexvalue,list):
			valuelist=[]
			for index in indexvalue:
				#####note("Index value #"+str(i)+": "+str(index)+".")
				if index==0: # inaccessible
					continue
				if index<0: # count backwards, last element being -1
					index+=(maxindex+1)
				if index<=0 or index>maxindex:
					continue
				valuelist.append(value[index-1])
			return valuelist
		if indexvalue==undefined.getValue():
			return undefined.getValue()
		if not isinstance(indexvalue,int):
			raise Exception("Element index not an integer.")
		if indexvalue==0:
			raise Exception("Element with index 0 does not exist, as lists in M are one-based not zero-based.")
		#####note("Index value: "+str(indexvalue)+".")
		if indexvalue<0:
			indexvalue+=(maxindex+1)
		if indexvalue<=0 or indexvalue>maxindex:
			return Exception("Index ("+str(indexvalue)+") into variable "+self.identifiername+" out of range.")
		return value[indexvalue-1]
	def setValue(self,_value,_environment):
		identifier=_environment.getExistingIdentifier(self.identifiername)
		if identifier is None:
			raise Exception("Identifier "+self.identifiername+" vanished.")
		value=identifier.getValue() # which should be a list
		if not isIndexable(value):
			raise Exception("Variable "+self.identifiername+" cannot be indexed: its value is not a list.")
		####note("Setting the element at index "+str(indexvalue)+" of "+self.identifiername+" with value "+str(value)+".")
		maxindex=len(value) # get the length of the list
		indexvalue=self.getIndexValue() #####getValue(self.index) # technically the index thingie
		# technically the index can also be a list (of indices)
		if isinstance(indexvalue,list):
			for (i,index) in enumerate(indexvalue):
				if not isinstance(index,int):
					continue
				###note("Index value: "+str(index)+".")
				if index==0: # prepend the given value
					value.insert(0,undefined.getValue())
					self.indexvalue[i]=1 # the actual index of the element we changed
					continue
				if index<0:
					index+=(maxindex+1)
					if index<=0: # still not available
						continue
				else: # a positive index, which might be too large
					while index>maxindex:
						value.append(undefined.getValue())
						maxindex+=1
				# if we get here a positive index specified, and no need to check
				self.indexvalue[i]=index # the actual index of the element we changed
				value[index-1]=_value
		else: # index not a list
			if not isinstance(indexvalue,int):
				raise Exception("Element index ("+getText(indexvalue)+") into variable "+self.identifiername+" not an integer.")
			if indexvalue==0:
				self.indexvalue=1 # the actual index of the element we changed (and thus to return)
				value.insert(0,undefined.getValue()) # prepend the undefined value
			elif indexvalue<0: # determine the index in the proper range (counting from the back)
				self.indexvalue=indexvalue+maxindex+1 # update self.indexvalue
			else: # a positive index provided
				# ascertain that that index exists!!
				while indexvalue>maxindex:
					value.append(undefined.getValue())
					maxindex+=1
			if self.indexvalue<=0 or self.indexvalue>maxindex:
				raise Exception("Element index ("+str(self.indexvalue)+") into "+self.identifiername+" out of range.")
			value[self.indexvalue-1]=_value
		return self
# MDH@30AUG2017: if an expression is executed it executes within a certain 'environment' i.e. a set of variables constitute a state that is local
#								 this means that the getValue() that we used to have in Expression is to be moved over to the ExpressionEvaluator
#								 this way at any moment the same expression can be used in multiple expression executors at the same time all with different 'environments'
class ExpressionEvaluator:
	def __init__(self,_expression,_environment):
		self.expression=_expression
		self.environment=_environment
	def getExpression(self):
		return self.expression
	def getEnvironment(self):
		return self.environment
	# because we know the 'parent' environment, when getValue is requested, we can pass that environment into the expression
	# at the moment that the expression is to be evaluated, which can pass it along to any subexpression that are evaluated 'below' it
	def getValue(self):
		return self.expression.getValue(self.environment)
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
	showprompt()
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
def main():
	# keep a list of statements, every line is one statement
	write("Welcome to M.")
	#####print("Start control messages with a backtick (`)!")
	lnwrite("All control messages start with ` (backtick). Type `h for help.")
	lnwrite("Press Ctrl-D to exit M, Ctrl-C to cancel input.")
	global mexpressions
	mexpression=None
	while 1:
		# display the prompt (with the info line in front of it)
		newprompt()
		emptyline=False # whether to clear the remainder of the line after receiving a character
		# we have to write whatever current expression we have immediately BEFORE even reading the first character
		if mexpression is not None:
			mexpression.echo()
		# otherwise the first character on the new expression is allowed to be Ctr-D or the backtick
		tokenchar=getch()
		# special tokens are permitted when starting with a new expression which we have to process first
		if mexpression is None:
			if ord(tokenchar)==4: # Ctrl-D on a new expression means exit M
				break
			if tokenchar=='`': # ` means the user wants to set an M option (and not enter an M expression)
				controlmessage=""
				write(tokenchar)
				while 1:
					controlch=getch()
					if ord(controlch)==3 or ord(controlch)==4 or ord(controlch)==10 or ord(controlch)==13:
						break
					# NOTE you cannot get out, but you can clear the control message using backspace if you want to
					if ord(controlch)==127: # a backspace
						# do NOT allow cutting of the backtick
						if len(controlmessage)>0:
							controlmessage=controlmessage[:-1]
							reprompt()
							sys.stdout.write("`"+controlmessage)
						else: # beep
							beep()
					else:
						sys.stdout.write(controlch)
						controlmessage+=controlch
					# if this is the first character and it's not a d, done
					if len(controlmessage)==1 and controlch!='d' and controlch!='c':
						break
				######newline()
				if ord(controlch)!=3 and ord(controlch)!=4 and len(controlmessage)>0:
					# get to see the variables with v
					if controlmessage[0]=="h" or controlmessage[0]=="H":
						lnwrite("Possible control messages:")
						lnwriteleft("d=<debug level>[Enter] "+(" "*12)+" to set the debug level.",130,DEBUG_BACKCOLOR)
						lnwrite("c<color type>=<color code>[Enter] "+(" "*1)+" to set the color code for color type (d=debug, i=identifier, l=literal, o=operator, p=prompt).")
						lnwriteleft("v "+(" "*33)+" shows the list of (global) constants and variables.",130,DEBUG_BACKCOLOR)
						lnwrite("f "+(" "*33)+" shows the list of functions.")
						lnwriteleft("o "+(" "*33)+" shows the list of operators.",130,DEBUG_BACKCOLOR)
						lnwrite("h "+(" "*33)+" to view this help.")
						lnwriteleft("x "+(" "*33)+" to exit M immediately.",130,DEBUG_BACKCOLOR)
						lnwrite(": "+(" "*33)+" to switch to declaration mode (default).")
						lnwriteleft("= "+(" "*33)+" to switch to evaluation mode.",130,DEBUG_BACKCOLOR)
					elif controlmessage[0]=="x" or controlmessage[0]=="X":
						break
						"""
						sys.stdout.write("Exit M? ")
						sch=getch()
						sys.stdout.write(sch)
						if sch=="y" or sch=="Y":
							break
						continue
						"""
					elif controlmessage[0]=="f" or controlmessage[0]=="F":
						argcount=0
						for functionlist in functions:
							argcount+=1
							lnwrite(str(argcount)+" argument functions:")
							for function in functionlist:
								write(" "+function)
							#######newline()
					elif controlmessage[0]=="o" or controlmessage[0]=="O":
						lnwrite("Binary operators:")
						lnwrite("\tArithmetic\t- + % \ | & ^ . .. * ** / // << >>")
						lnwrite("\tComparison\t< <= > >= == ")
						lnwrite("\tLogical\t\t&& ||")
						lnwrite("\tAssignment\t=")
						lnwrite("\tDeclaration\t:")
						lnwrite("Unary operators:\t= ! ~ - +")
					elif controlmessage[0]=="v" or controlmessage[0]=="V":
						lnwrite("Variables:")
						for identifier in MEnvironment.identifiers:
							write(" "+identifier)
						#####newline()
					elif controlmessage[0]==":": # MDH@27AUG2017: switch to declaration mode
						setMode(0)
					elif controlmessage[0]=="=": # MDH@27AUG2017: switch to evaluation mode
						setMode(1)
					elif controlmessage[:2]=="d=" or controlmessage[:2]=="D=":
						global DEBUG
						DEBUG=int(controlmessage[2:])
						lnwrite("Debug level set to "+str(DEBUG)+".")
					elif controlmessage[0]=="c":
						global INFO_COLOR,LITERAL_COLOR,OPERATOR_COLOR,DEBUG_COLOR,IDENTIFIER_COLOR
						if len(controlmessage)>1: # at least one character following
							if len(controlmessage)>3 and controlmessage[2]=="=": # an assignment
								if controlmessage[1]=="l":
									LITERAL_COLOR=int(controlmessage[3:])
								elif controlmessage[1]=="o":
									OPERATOR_COLOR=int(controlmessage[3:])
								elif controlmessage[1]=="d":
									DEBUG_COLOR=int(controlmessage[3:])
								elif controlmessage[1]=="i":
									IDENTIFIER_COLOR=int(controlmessage[3:])
								elif controlmessage[1]=="p":
									INFO_COLOR=int(controlmessage[3:])
								else:
									writeerror("Invalid color type '"+controlmessage[1]+"'. Possible characters are d, i, l, o or p.")
							else: # write the current color codes
								writeerror("No assignment or no color code specified!")
						else: # let's show the current coloring
							lnwrite("Color codes: prompt="+str(INFO_COLOR)+", debug="+str(DEBUG_COLOR)+", identifier="+str(IDENTIFIER_COLOR)+", literal="+str(LITERAL_COLOR)+", operator="+str(OPERATOR_COLOR)+".")
					else:
						lnwrite("Unrecognized control message.")
				continue
			# if we get here it wasn't Ctrl-D or `, it might still be the arrow up or arrow down to select a previous expression
			mexpressionretrieved=None
			exprindex=len(mexpressions) # the position of the expression to use
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
						if exprindex<len(mexpressions):
							mexpressionretrieved=mexpressions[exprindex]
					elif ord(ch)==0x42: # arrow down
						# user shouldn't be allowed to cycle beyond len(mexpressions)
						if exprindex<len(mexpressions):
							exprindex+=1
							if exprindex<len(mexpressions):
								#####print "Retrieving expression #"+str(exprindex)+"..."
								mexpressionretrieved=mexpressions[exprindex]
					elif ord(ch)==0x43: # C, move forward
						beep() #note("Moving the cursor forward not implemented yet!")
					elif ord(ch)==0x44: # D, move backward
						beep() #note("Moving the cursor back not implemented yet!")
					# something to display????
					if mexpressionretrieved is not None:
						######print("Printing the expression!")
						mexpressionretrieved.unend().echo(False) # we need to write the unended version as that's the one that is to be continued...
				# read the next character (which might be another Escape character)
				tokenchar=getch() # get the first character
			if mexpressionretrieved is not None:
				mexpression=copy.deepcopy(mexpressionretrieved) # NO need to unend here because we already did that when showing the expression!!!
		# if we haven't got an expression (to continue) at this moment, we create a new one
		if mexpression is None:
			mexpression=Expression(MEnvironment,DEBUG) # start a new expression at the main debug level (DEBUG) which is the default!!
		# I guess we can allow Ctrl-D at any moment as well
		# NOTE a newline (Enter) shouldn't end the expression input per se
		##### see the use of Expression.echo() to rewrite the entire expression again!!! Mexpression=mexpression # MDH@25APR2017: we need a reference to the main level expression, so we can rewrite it (e.g. after a backspace!!)
		while ord(tokenchar)!=3 and ord(tokenchar)!=4: # not Ctrl-C or Ctrl-D
			expressionerror=None
			if ord(tokenchar)!=10 and ord(tokenchar)!=13: # tokenchar!='\n' didn't work!!
				# if we've received a backspace character (ASCII 127 on iMac), we tell the expression to execute the backspace
				if ord(tokenchar)==127: # a backspace
					if mexpression.isEmpty() and mexpression.parent is None: # nothing left to delete
						mexpression_new=mexpression
						beep()
					else:
						mexpression_new=mexpression.backspace() # returns None if some error occurred
						if mexpression_new is not None: # expression data model adapted accordingly
							# we have to rewrite the entire expression as it is now
							reprompt() # clears the line and prompt again
							mexpression_new.echo() # write the main expression in the original colouring (that is what echo does, go all the way up to the main expression!!)
				else: # not a backspace
					mexpression_new=mexpression.add(tokenchar)
				expressionerror=mexpression.getError()
			else: # attempt to end the expression which might not be allowed right now
				# MDH@25AUG2017: we'll evaluate the expression until now and continue on the next line, which would be neat
				#								 but let's decide to only do that when we're at the top level
				#######note("Checking whether the expression is complete!")
				if mexpression.parent is not None: # there is a parent, but if the expression is a declaration we're done anyway!!
					if mexpression.isDeclared():
						mexpression=mexpression.parent # pretty essential to return to the parent, in which the declaration occurred!!
						break
				elif mexpression.ends() is None: # expression complete, so ready to be evaluated, so there's no need to set mexpression_new anyway!!!
					break
				if mexpression.parent is None:
					# let's display the result, and return to the current position
					emptyline=True # get rid of the result showing as soon as receiving the next character
					expressionvalue=mexpression.getValue()
					expressionvaluetext=" = "+getText(expressionvalue)
					write(expressionvaluetext,DEBUG_COLOR)
					if DEBUG:
						sys.stdout.write("\033["+str(len(expressionvaluetext))+"D") # return to the original cursor position
					else:
						showprompt() ## replacing:
					error=mexpression.getError()
					if error is not None:
						writeerror(error)
						showprompt()
						writeagain(mexpression)
				else: # in some subexpression, allow continuation
					showprompt()
			# if some error occurred (e.g. that the expression is not yet complete when the user presses the Enter/Return key)
			if expressionerror is not None: # some error occurred (stored with mexpression)
				# write the error and redisplay the expression
				writeerror(expressionerror)
				writeagain(mexpression)
			elif mexpression_new is None:
				writeerror("No (sub)expression")
				writeagain(mexpression)
			else: # cannot except a vanishing expression!!!
				mexpression=mexpression_new
			# ready to read and process the next character!!!
			tokenchar=getexprch()
			if emptyline:
				emptyline=False
				output("\033[K")
			#######output("("+str(ord(tokenchar))+")")
		#####writeln("Done processing user input...")
		if ord(tokenchar)==4: # Ctrl-D
			lnwrite("Exit M? ")
			sch=getch()
			if sch=="y" or sch=="Y":
				break
			continue
		if ord(tokenchar)==3: # Ctrl-C
			mexpression=None
			continue
		# ready to evaluate (and register)
		if mexpression is not None:
			mexpression.end() # end the expression as token instance
			#####writeln("Evaluating the expression...")
			expressiontext=mexpression.getText().strip()
			if len(expressiontext)>0: # something to evaluate at all
				# better to show any syntax error first (because getValue() might also create an error
				###sys.stdout.write("\n")
				expressionvalue=mexpression.getValue(MEnvironment) # pass in the global environment to evaluate the expression
				# MDH@27AUG2017: write the result on the same line
				if expressionvalue is not None:
					write(getColoredText(" = ",INFO_COLOR)+getColoredText(getText(expressionvalue),RESULT_COLOR,RESULT_BACKCOLOR))
				else: # probably best to indicate that the expression could not be evaluated
					write(getColoredText(" = ",INFO_COLOR)+getColoredText("Result undefined!",RESULT_COLOR,RESULT_BACKCOLOR))
				""" replacing:
				if expressionvalue is not None:
					lnwrite(" "*(len(prompt)-2)+"= "+getColoredText(str(expressionvalue),RESULT_COLOR,RESULT_BACKCOLOR))
				else: # probably best to indicate that the expression could not be evaluated
					lnwrite(" "*(len(prompt))+getColoredText("Result undefined!",RESULT_COLOR,RESULT_BACKCOLOR))
				"""
				computationerror=mexpression.getError()
				if computationerror is not None:
					writeerror(computationerror)
				# even if some error occurred (typically because the expression is not yet complete), we can still show the intermediate result (if any)
				# NOTE if the result is undefined i.e. None, do NOT show it TODO should we indicate this somehow????
				mexpressions.append(mexpression) # remember both the expression text, as well as the expression
				#####expressiontext=mexpression.getText() ####Representation() #####mexpression.getWritten()+getColorText(INFO_COLOR) # ascertain to end with the default coloring
				# MDH@18AUG2017: TODO if we store the expression (or expression tokens) itself, we can use val() instead of eval() to evaluate it!!!
				#											but this would also mean that we should be allowed to store/serialize tokenized versions of expression text (source) actually Expression instances
				# MDH@30AUG2017: the global M variable is now defined in MEnvironment
				if mode==0: # declaration mode
					MEnvironment.getIdentifierValue('M').append(mexpression) # MDH@17AUG2017: storing the expression itself (which value might change dynamically)
				else:
					MEnvironment.getIdentifierValue('M').append(expressionvalue) # MDH@17AUG2017: for now let's see if we can do this!!
			mexpression=None # thus forcing to have to create a new one instead of continueing with the incompleted one
		else:
			writeerror("No expression to evaluate!")
	######emptyline() # clear the current input line
	newline()
	writeln("Thank you for using M.")

DEBUG=0
if __name__=="__main__":
	try:
		if len(sys.argv)>1:
			DEBUG=int(sys.argv[1])
	finally:
		main()
