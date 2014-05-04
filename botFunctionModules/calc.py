import riftChatBotUtils
import operator as op, ast

# Safe calculator courtesy of Stack Overflow's J.F.Sebastian
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.pow}

def eval_ast(node):
    if isinstance(node, ast.Num): # <number>
        return node.n
    elif isinstance(node, ast.operator): # <operator>
        return operators[type(node)]
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        return eval_ast(node.op)(eval_ast(node.left), eval_ast(node.right))
    else:
        raise TypeError(node)
		
def evaluate(input):
	return str(eval_ast(ast.parse(input).body[0].value))

# Perform mathematical calculations
def bot_calc(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if not req.argList:
		req.response += ['Usage: !calc expr']
		
	elif req.argList[0] in ['-h', '--help', 'help']:
		func, opts, desc = __botFunctions__["calc"]
		req.response += [desc]
		req.response += ['Usage: !calc expr']
	
	else:
		# Try to evaluate the calculation (with spaces removed)
		try:
			req.response += [evaluate("".join(req.argList))]
		except TypeError:
			req.response += ['Syntax Error']
		except SyntaxError:
			if any('x' in arg for arg in argList):
				req.response += ['Syntax Error: Use * for multiplication']
			else:
				req.response += ['Syntax Error']
				
	return req

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'calc'	: (bot_calc, [], "Evaluate math expressions")
	}