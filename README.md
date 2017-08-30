# PyM
a simple interpreter written in Python

History:
29 Aug 2017: while, if and for 'functions' implemented
30 Aug 2017: Now working on implementing functions

Usage:
Run from the command line using python M.py <debug level> where <debug level> is a positive number (the default is 0 i.e. no debug information is shown).
Then you will be prompted to enter an expression (formula) or a control message. A control message starts with a backtick (`), and should be followed by at least one character. For all possible options use `h behind the prompt.
The prompt consists of the letter M followed by the current expression index between parentheses, with suffix : e.g. M(1): will be the first prompt.
Press the Enter key when you have finished entering the complete expression. Note that the interpreter will tokenize you expression as you type and will refuse characters that are not allowed. If you press the Enter key when the expression is not yet complete, you are told so, and you may continue the expression on the next line. Press Ctrl-C to cancel the input without further evaluation of the expression.
Use Ctrl-D at the prompt to exit M immediately. You can also use when you've already entered expression text, but in that case you will be asked whether you want to exit M first.
If you want to evaluate multiple expressions at once you will have to enter an expression list. A list start with ( and ends with ). Expressions in the list must be separated by a comma.
Allowed literals are integers, reals (containing a decimal point), text literals (enclosed in single or double quotes) or lists of course.
Variables can be created by assigning a value to them using the assignment (i.e. =) operator. Note that you can only start an expression with an assignment, you cannot place it somewhere in the middle. However, since every ( starts a new (sub)expression, you can create a new variable directly behind any opening parenthesis as well. 
