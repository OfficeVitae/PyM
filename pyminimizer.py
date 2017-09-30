"""
Author: M.P.A.J. de Hoogh
Date: 31 Aug 2017
creates a minimized version of a Python script removing all comment lines
input: the name of a Python file
"""
import sys
import os
def main(_args):
	if len(_args)>0:
		inputfilename=_args[0]
		# check if this identifies as a Python input file
		if inputfilename.lower().endswith(".py"):
			outputfilename=inputfilename[:-3]+".min.py" # the default name of the output file
			if not os.path.exists(outputfilename):
				inputfile=open(inputfilename,'r')
				if inputfile:
					outputfile=open(outputfilename,'w')
					if outputfile:
						inputlineindex=0
						inputline=inputfile.readline()
						l=len(inputline)
						incomment=False # whether or not we are in a multiline comment
						while l>0:
							inputlineindex+=1 # keep track of the input line index
							inputtext=inputline.rstrip('\r\n') # strip the end of the line
							stripped=len(inputtext)-l # what we stripped of
							#######stripped=len(inputtext)-l # remember what was stripped, we can use stripped to obtain the end of line characters used
							inputcode=inputtext.lstrip('\t ') # remove trailing whitespace and the like
							if len(inputcode)>0: # something on the line to further judge
								if incomment: # this line might end the multiline comment
									if inputcode.startswith('"""'): # end the multicomment part
										incomment=False # next line should not be a multicomment line anymore...
								else: # currently not in a multiline comment
									if inputcode.startswith('"""'): # starts the multicomment part
										incomment=True # next line should not be a multicomment line anymore...
									elif not inputcode.startswith('#'): # not a comment line
										outputfile.write(inputtext+" # "+str(inputlineindex)+inputline[stripped:])
							inputline=inputfile.readline()
							l=len(inputline)
						outputfile.close()
					else:
						print "ERROR: Failed to create output file '"+outputfilename+"'."
					inputfile.close()
				else:
					print "ERROR: Failed to open output file '"+outputfilename+"'."	
			else:
				print "ERROR: Output file '"+outputfilename+"' already exists, try again after removing it!"
		else:
			print "ERROR: Input file '"+inputfilename+"' does not end with .py, so does not qualify as a Python input file."
	else:
		print "ERROR: No Python file specified to process."
		
if __name__=="__main__":
	main(sys.argv[1:])