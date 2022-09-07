import re

def match_parenthesis(string):
    order = 0
    all_paranthesis = re.findall(r'[\(\)]', string)
    if all_paranthesis.count('(') != all_paranthesis.count(')'):
        raise ValueError('Number of opening parantheses does not match number of closing')
    first_left = string.find('(')
    i = first_left + 1
    while True:
        next_left = string.find('(', i)
        next_right = string.find(')', i)
        if next_left == -1 or next_right < next_left:
            if order == 0:
                return string[first_left+1:next_right], (first_left, next_right)
            else:
                i = next_right + 1
                order -= 1
        else:
            i = next_left + 1
            order += 1

def calculate(string, verbose=False):
    # Search for all operators given that it is not preceded by another operator
    # or "e" or "E" (engineering notation)
    exp = re.compile(r'(?<![eE\+\-\*\/])[\*\/\-\+]')
    # While any operator remain in string
    while True:
        try:
            number = float(string)
            if verbose:
                print("")
            return string
        except ValueError:
            pass
        if verbose:
            print("calculate string: " + repr(string))
        # If the first number in the string is negative, it is interpreted as an
        # operator, but without a left component. Handled manually.
        if string[0] == '-':
            first_minus = True
            string = string[1:]
        else:
            first_minus = False
        comps = exp.split(string)
        if verbose:
            print("All components: " + repr(comps))

        # Search for operators by order of priority        
        # Power
        i = string.find('**')
        marker = None
        if i != -1:
            operator, marker = 'power', '**'
        # Multiply
        if marker is None:
            i = string.find('*')
            if i != -1:
                operator, marker = 'multiply', '*'
        # Divide
        if marker is None:
            i = string.find('/')
            if i != -1:
                operator, marker = 'divide', '/'
        # Add
        if marker is None:
            m = re.search(r'(?<![eE\-\+])\+', string)
            if m:
                i = m.start()
                operator, marker = 'add', '+'
        # Subtract
        if marker is None:
            m = re.search(r'(?<![eE\-\+])\-', string)
            if m:
                i = m.start()
                operator, marker = 'subtract', '-'
        # Else error
        if marker is None:
            raise ValueError('No valid operators found for calculate function!')

        # Get the left and right components (wrt the operator)
        if first_minus:
            i += 1
        left = exp.split(string[:i])
        if verbose:
            print('Left comps: ', left)
        if len(left) == 1:
            left = left[0]
            if first_minus:
                left = '-' + left
        else:
            left = left[-1]
        right = exp.split(string[i+len(marker)-1:])
        if verbose:
            print('Right comps: ', right)
        right = right[1]
        if verbose:
            print('Operation: ', operator)
            print('Left: ', left)
            print('Right: ', right)

        # Apply the operator
        if operator == 'power':
            result = float(left) ** float(right)
        elif operator == 'multiply':
            result = float(left) * float(right)
        elif operator == 'divide':
            numerator = float(left)
            denumerator = float(right)
            if denumerator == 0:
                msg = '(Part of) the given string evaluates to zero in a denumerator!'
                raise ZeroDivisionError(msg)
            result = numerator/denumerator
        elif operator == 'add':
            result = float(left) + float(right)
        elif operator == 'subtract':
            result = float(left) - float(right)

        # Replace the operated components with the result
        expression = left + marker + right
        i = string.find(expression)
        string = string[:i] + str(result) + string[i+len(expression)+1:]
        if verbose:
            print("")
            print("component evaluated to: " + repr(string))
    return string

def evaluate_string(string, verbose=False):
    # First check for decimal point
    if ',' in string and '.' in string:
        raise ValueError('Math string contains both "," and ".". Does not compute!')
    if ',' in string:
        string = string.replace(',', '.')
    # If the string is a (float) number, simply return it and end calculations
    try:
        num = float(string)
        if verbose:
            print('Returning number: ' + string)
        return string
    # Otherwise, recursively evaluate components in the formula starting with
    # matching parenthesis pairs.
    except ValueError:
        if verbose:
            print('Evaluating string: ' + repr(string))
        if '(' in string or ')' in string:
            substring, index = match_parenthesis(string)
            if verbose:
                print('---')
                print('Matching parenthesis found:')
                print(substring)
                print('from index {0} to {1} in parent string'.format(index[0], index[1]))
                print('---')
            string = (
                string[:index[0]]
                + evaluate_string(substring, verbose)
                + string[index[1]+1:]
                )
        else:
            string = calculate(string, verbose)
            if verbose:
                print('Newly evaluated string: ' + string)
        return evaluate_string(string, verbose)

if __name__ == '__main__':
    import sys
    string = sys.argv[1]
    string = string.replace(' ', '')

    print('Result is: ' + evaluate_string(string, verbose=True))
