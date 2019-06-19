#!/usr/bin/python
import re
import nltk
import sys
import getopt
import pickle
import index

from math import floor, sqrt

########################### DEFINE CONSTANTS ########################### 
NOT_OP = "NOT"
AND_OP = "AND"
AND_NOT_OP = AND_OP + " " + NOT_OP
OR_OP = "OR"
PAREN_START = "("
PAREN_END = ")"

OPERATORS = [NOT_OP, AND_NOT_OP, AND_OP, OR_OP]
PRECEDENCE = dict(zip(OPERATORS, range(len(OPERATORS))))

END_LINE_MARKER = '\n'

######################## COMMAND LINE ARGUMENTS ########################

### Read in the input files as command-line arguments
###
def read_files():
    dictionary_file = postings_file = file_of_queries = file_of_output = None

    def usage():
        print ("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")
	
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o == '-d':
            dictionary_file  = a
        elif o == '-p':
            postings_file = a
        elif o == '-q':
            file_of_queries = a
        elif o == '-o':
            file_of_output = a
        else:
            assert False, "unhandled option"

    if dictionary_file == None or postings_file == None or file_of_queries == None or file_of_output == None :
        usage()
        sys.exit(2)

    return dictionary_file, postings_file, file_of_queries, file_of_output

######################## FILE READING FUNCTIONS ########################

### Parse a list object
### Future improvement: use pickle to serialise
###
def parse_list(list_string):
    return [int(x) for x in list_string.split()]

### Retrieve a dictionary format given the dictionary file
###
def get_dictionary():
    with open(dictionary_file, 'rb') as f:
        dictionary = pickle.load(f)
    return dictionary

### Retrieve a list of all valid document IDs given the postings file
###
def get_document_list():
    postings_file.seek(0)
    document_list = parse_list(postings_file.readline())
    return document_list

### Retrieve all the queries which need to be processed
###
def get_queries():
    with open(file_of_queries, 'r') as f:
        queries = f.read().splitlines()

    return queries

### Retrieve the posting list for a particular dictionary term
###
def get_posting_list(t):
    try:
        term_data = dictionary[t]
        term_freq, offset = term_data
        postings_file.seek(offset)
        data = parse_list(postings_file.readline())
        return term_freq, data
    except KeyError:
        # term does not exist in dictionary
        return 0, list()
    
############################## QUERY PARSING ##############################

### Parse the query for the Shunting Yard Algorithm
###
def parse_query(q):
    if not PAREN_START in q:
        return q.split()
    
    paren_query = q[q.find(PAREN_START): q.find(PAREN_END) + 1]
    result_front = q[: q.find(PAREN_START)].split()
    result_back = q[q.find(PAREN_END) + 1: ].split()
    return result_front + [paren_query] + result_back    
    
### Shunting Yard Algorithm to convert infix expression to postfix boolean expression
###
def shunting_yard(q):

    tokens = parse_query(q)
    
    token_stack = list()
    result = list()

    # Transfer operators on token stack to result
    def clear_token_stack():
        nonlocal token_stack, result
        while token_stack != []:
            result.append(token_stack.pop())

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in OPERATORS:
            if t == AND_OP and tokens[i+1] == NOT_OP:
                t = AND_NOT_OP
                i += 1
                
            # Check if the precedence of the top of the stack is higher
            if token_stack != [] and PRECEDENCE[token_stack[-1]] > PRECEDENCE[t]:
                clear_token_stack()
            token_stack.append(t)
        elif t.startswith(PAREN_START):
            parsed_query = shunting_yard(t[1: -1])
            for term in parsed_query:
                result.append(term)
        else:
            result.append(index.normalise_term(t))  # use the term normaliser in indexing

        # Increase the counter
        i += 1

    clear_token_stack()

    return result

################### POSTING LIST RETRIEVAL AND MERGING ###################

### Checks if an operand is already an intermediate posting list
### The format should be (size, [list of docIDs])
###
def is_posting_list(operand):
    return type(operand) == tuple and len(operand) == 2

### Asserts that an operand is a posting list, else enforce it
###
def assert_posting(operand):
    if not is_posting_list(operand):
        return get_posting_list(operand)
    return operand

### Retrieves the size of a posting list
###
def get_size(posting):
    return posting[0]

### Retrieves the posting list itself
###
def get_data(posting):
    return posting[1]

### Apply NOT to operand
###
def apply_not(operand):
    posting = assert_posting(operand)
    posting_data = get_data(posting)

    if get_size(posting) == 0:
        return document_list

    ptr_main = 0    # pointing to the list of all docIDs
    
    ptr_p = 0       # pointing to the current posting
    p_current = posting_data[ptr_p]

    result = list()
    while True:
        current_main = document_list[ptr_main]
        if current_main < p_current:
            result.append(current_main)
            ptr_main += 1
        else:       # current_main == p_current, cannot be > because document_list contains all docIDs
            ptr_main += 1
            ptr_p += 1
            if ptr_p >= get_size(posting):
                break

            p_current = posting_data[ptr_p]

    while ptr_main < total_num_documents:
        current_main = document_list[ptr_main]
        result.append(current_main)
        ptr_main += 1

    return len(result), result

### Apply AND to two operands
### The merging is done such that size of posting1 >= size of posting2 by a level of significance
###
def apply_and(operand1, operand2):
    posting1 = assert_posting(operand1)
    posting2 = assert_posting(operand2)
    
    if get_size(posting2) > get_size(posting1):
        return apply_and(operand2, operand1)
    
    ptr1 = 0
    ptr2 = 0
    posting1_data = get_data(posting1)
    posting2_data = get_data(posting2)

    p1_skipsize = floor(sqrt(get_size(posting1)))
    p2_skipsize = floor(sqrt(get_size(posting2)))

    has_skip_p1 = lambda x: x % p1_skipsize == 0
    has_skip_p2 = lambda x: x % p2_skipsize == 0

    result = list()
    while ptr2 < get_size(posting2) and ptr1 < get_size(posting1):
        # While the values may not change every iteration, this is more
        # efficient than error checking at every clause
        p1_current = posting1_data[ptr1]
        p2_current = posting2_data[ptr2]

        if p1_current == p2_current:
            result.append(p2_current)
            ptr1 += 1
            ptr2 += 1
        elif has_skip_p1(ptr1) \
             and ptr1 + p1_skipsize < get_size(posting1) \
             and posting1_data[ptr1 + p1_skipsize] < p2_current:
            # skip on p1
            ptr1 += p1_skipsize
        elif p1_current < p2_current:
            # increment p1 by 1
            ptr1 += 1
        elif has_skip_p2(ptr2) \
             and ptr2 + p2_skipsize < get_size(posting2) \
             and posting2_data[ptr2 + p2_skipsize] < p1_current:
            # skip on p2
            ptr2 += p2_skipsize
        elif p1_current > p2_current:
            # data does not exist, increment p2 by 1
            ptr2 += 1

    return len(result), result

### Apply AND NOT to two operands
###
def apply_and_not(operand1, operand2):
    posting1 = assert_posting(operand1)
    posting2 = assert_posting(operand2)
    
    ptr1 = 0
    ptr2 = 0
    posting1_data = get_data(posting1)
    posting2_data = get_data(posting2)

    p1_skipsize = floor(sqrt(get_size(posting1)))
    p2_skipsize = floor(sqrt(get_size(posting2)))

    has_skip_p1 = lambda x: x % p1_skipsize == 0
    has_skip_p2 = lambda x: x % p2_skipsize == 0

    result = list()
    while ptr2 < get_size(posting2) and ptr1 < get_size(posting1):
        # While the values may not change every iteration, this is more
        # efficient than error checking at every clause
        p1_current = posting1_data[ptr1]
        p2_current = posting2_data[ptr2]

        if p1_current < p2_current:
            result.append(p1_current)
            ptr1 += 1
        elif p1_current == p2_current:
            ptr1 += 1
            ptr2 += 1
        elif has_skip_p2(ptr2) \
             and ptr2 + p2_skipsize < get_size(posting2) \
             and posting2_data[ptr2 + p2_skipsize] < p1_current:
            # skip on p2
            ptr2 += p2_skipsize
        elif p1_current > p2_current:
            # increment p2 by 1
            ptr2 += 1

    # Add the remaining values of p1 into result
    while ptr1 < get_size(posting1):
        p1_current = posting1_data[ptr1]
        result.append(p1_current)
        ptr1 += 1

    return len(result), result

### Apply OR to two operands
###
def apply_or(operand1, operand2):
    posting1 = assert_posting(operand1)
    posting2 = assert_posting(operand2)

    ptr1 = 0
    ptr2 = 0
    posting1_data = get_data(posting1)
    posting2_data = get_data(posting2)
    
    result = list()
    while ptr1 < get_size(posting1) and ptr2 < get_size(posting2):
        p1_current = posting1_data[ptr1]
        p2_current = posting2_data[ptr2]
        
        if p1_current < p2_current:
            result.append(p1_current)
            ptr1 += 1
        elif p2_current < p1_current:
            result.append(p2_current)
            ptr2 += 1
        else:
            result.append(p1_current)   # both point to same docID
            ptr1 += 1
            ptr2 += 1

    while ptr1 < get_size(posting1):
        result.append(posting1_data[ptr1])
        ptr1 += 1

    while ptr2 < get_size(posting2):
        result.append(posting2_data[ptr2])
        ptr2 += 1

    return len(result), result

########################### QUERY PROCESSING ###########################

### Processing a boolean query
###
def process_query(q):

    # Convert the infix query to a postfix notation using the Shunting Yard Algorithm
    postfix_query = shunting_yard(q)

    # Process the expression in the correct precedence
    # An empty posting list is inserted for the case of a blank query
    operands = [(0, list())]
    for t in postfix_query:
        if t in OPERATORS:
            # Evaluate the operation
            operand1 = operands.pop()

            if t == NOT_OP:
                result = apply_not(operand1)
            else:
                operand2 = operands.pop()
                if t == AND_OP:
                    result = apply_and(operand1, operand2)
                elif t == AND_NOT_OP:
                    # Note that the order of operands is swapped for AND NOT
                    result = apply_and_not(operand2, operand1)
                elif t == OR_OP:
                    result = apply_or(operand1, operand2)
            operands.append(result)
        else:
            operands.append(t)
    
    result = operands.pop()
    return get_data(result)

dictionary_file, postings_file, file_of_queries, file_of_output = read_files()
postings_file = open(postings_file, 'r') # kept open because of frequent use

dictionary = get_dictionary()
document_list = get_document_list()
total_num_documents = len(document_list)
queries = get_queries()

with open(file_of_output, 'w') as f:
    for q in queries:
        result = process_query(q)
        f.write(' '.join([str(x) for x in result]) + END_LINE_MARKER)
        
postings_file.close()
