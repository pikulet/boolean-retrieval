This is the README file for the submission of:
JOYCE YEO SHUHUI
ANU KRITI WADHWA

== Python Version ==

We're using Python Version 3.6.6 for this assignment.

== General Notes about this assignment ==

### Indexing the Corpus

We read in all the documents and sort them in increasing order. Note
that the documentIDs have to be converted to integers before sorting,
else we would be sorting by their lexicographical order
("1", "10", "2", "20")...

Next, we iterate though each document. For every document, we read the
document line by line using linecache. We look at the content of each
line and build the dictionary and postings list, with buildListHelper.
We also remember the list of all existing documentIDs in the Postings
class. This base reference is useful for NOT queries.

## Indexing a particular line
Each line is passed through a sentence tokeniser, returning an
iterable list of words.

With the list of words, one can firstly filter out the stop words,
then normalise each word. It is also possible to normalise before
filtering, though this would also remove derivative terms of stop
words. It depends on the use case of the searching to decide how this
step would be carried out.

We normalise our terms using a porter stemmer, followed by case-
folding. Since we abstracted this normalisation into a method, we can
simply change how we want to normalise terms. It is also convenient to
apply the function in normalising query terms.

# Dictionary Structure
Our dictionary is a hashmap since we are not interest in tolerant
retrieval and wildcard queries (we are looking at boolean queries).

The structure of the dictionary is as follows:
dictionary --> [term] --> [termFreq, termID/ termOffset]

For example, calling
>> dictionary["hello"] would return a tuple like 3, [4, 10, 50]
The first value in the tuple represents the term frequency, or number
of documents which the term appears in.
The second value is a sorted list of document IDs. Since the list is
sorted and we are processing documentIDs in ascending order, when we
encounter a new term we can simply append the new documentID to the
end of the list.

# Postings Structure
The postings list is an indexable-list of lists. For example,
[ [1, 2, 3],	[2, 5, 9],	[1, 2, 9]	]
There are three posting lists shown here.

Each list represents the posting list for a particular term. The term
with termID = 0 appears in document 1, 2 and 3.

The termID is allocated in ascending order from 0, and is recorded in
the dictionary.

# Adding the term data to dictionary and posting list
Each time we encounter a term, we check if it already exists in the
dictionary. If it does, we can lookup the termID. For instance, we
are indexing document 10 and encounter the word "book" with termID 1.
We look for the corresponding posting list and append 10 to the end of
the list, resulting in [2, 5, 9, 10] being the new posting list for
the word "book".

Since the size of the posting list has increased, we will also update
the term frequency in the dictionary.
dictionary --> ["book"] --> (3, 1) becomes
dictionary --> ["book"] --> (4, 1)

Note that only the term frequency changes, the termID remains the same.

However, docIDs should be unique within one posting list. That is, it
does not matter how many times the word "book" appears in document 10,
only that it appears. The next time we encounter the word "book" in
document 10, we will have to ignore it.

Another case is when we encounter a new term that does not exist in
the dictionary, say the word "toxic" in document 10. We have to create
a new posting list and dictionary entry. By default, the dictionary
entry would be ["toxic"] --> (1, termID). We generate the termID in the
Posting class. When encountering a new term, we create a list with one
element, as shown below:
[ [1, 2, 3],	[2, 5, 9],	[1, 2, 9]	] becomes
[ [1, 2, 3],	[2, 5, 9],	[1, 2, 9],	[10]	], and we
return 3 as the termID of "toxic". Note that termID is set as a running
counter in the Posting class, allowing us to create a new posting list
and return the index of that list in O(1) time.

We run our algorithm on all the documents, giving us a very large
dictionary and list of postings.

## Saving the data to file
We iterate through all the dictionary terms, and lookup their
respective posting lists using the termID.

We start saving the postings first, so that we can retrieve the actual
byte offset of the postings lists and store these byte offsets in the
dictionary. For example, we store the above posting as
-------------
1 2 3 5 9 10
1 2 3
2 5 9
1 2 9
10
-------------
in postings.txt

The first line is a list of all existing documentIDs, and each
subsequent posting list follows, separated by a newline character '\n'

Before we write each line, we use fileHandler.tell() to retrieve the
position of the pointer. For example, the first posting list could have
an offset of 14 bytes (including the newline character).

We then overwrite the termID earlier to this new byteOffsetValue. Note
that we no longer need that particular termID because we have already
retrieved the posting list and written it to file. The dictionary now
records its actual position in postings.txt, so
["hello"] --> (3, 0) // Term frequency = 3, termID = 0 becomes
["hello"] --> (3, 14) // Term frequency = 3, termOffsetValue = 14 bytes

To retrieve a particular posting list, we only have to
fileHandler.seek() the offset value, and use fileHandler.readline() to
retrieve the entire posting list.

Once the entire posting file is saved, we will have a dictionary
mapping terms to their frequencies and offset values.
dictionary --> [term] --> [termFreq, termOffset]

Since the dictionary is a small enough file that can be read entirely
in-memory, we use the pickle class to serialise and .dump() this
dictionary to dictionary.txt. We can subsequently retrieve the
dictionary by unserialising it using .load().

## Disk-based Indexing of Corpora
Currently, we keep the entire postings data in memory, which would be
unfeasible for larger corpora.

We experimented with ways to index a few documents at a time, that is,
add support to index an additional document given a dictionary and
postings file.

However, our problem was that this requires reading the current
posting list, then appending the new documentID at the back. Yet
again, it is operationally unsafe to write the files currently being
read, and it seems that we are unable to simply edit one line in the
file. Most solutions we found involved reading the entire file,
editing that one particular line, and writing the file back to memory.

In fact, this is not the only problem because adding a few bytes of
data would mean having to correct the offset values for other
dictionary terms. (If dictionary term has an offset value > current
line we are on, then we will add the offset of the byte offset).

To circumvent this problem, we thought of appending the updated
posting list at the bottom of the file, then changing the offset value
for that particular dictionary term. However, this would mean that
there is a lot of wasted space. Say we have 10000 documents and index
1000 documents at each time, then each term could have up to 10
posting lists in the postings file. Of course, we can again do a
post-processing to filter out the unused lines of posting lists.

In the end, we did not do this because of the large complexity and
we were short on time, but it is something we would explore as a
future improvement.

### Processing Queries

First, we retrieve our dictionary and list of all documents.

For every query, we first parse the query. For simplicity, we convert
the query to a postfix notation using the Shunting Yard Algorithm.
Our algorithm only allows for one set of parentheses in the boolean
query, which we collect together as a term when parsing the query.

In order to optimise operations later on, we define an additional
boolean operator, AND NOT. This is faster than applying NOT and then
applying AND, especially since applying NOT would drastically increase
the size of the resulting posting list.

We can then proceed to using a stack to evaluate the postfix query.
When we encounter operators (AND, OR, NOT, AND NOT), we simply pop
operands from the stack and process them. The result is pushed back
to the top of the stack. Since we are using a python list, we do
.pop() and .append() to pop and push posting lists from our stack.

The final result of the boolean query would simply be the one
result in the stack, which is returned and printed to the output file.

## Retrieving posting list of a dictionary term
For every operand on our stack, it could be a query term from the
boolean query, or it could be an intermediate posting list after we
have performed some evaluations on it.

An intermediate posting list is defined as
(sizeOfList, [data...]) e.g. (3, [5, 9, 10])
Keeping track of the size allows us to perform some optimisation on
the AND operation.

Before operands are evaluated, they have to be converted to posting
lists, which is done in our assert_posting method. If the operand is
not a posting, then it is a query term. We look up the query term in
the dictionary to get its byte offset value, then use
fileHandler.seek() and fileHandler.readline() to retrieve the posting
list.

## Evaluating boolean operations

We defined four boolean operations OR, AND, AND NOT and NOT, and their
algorithms are given below:

NOT:
1. Traverse the list of all documents (all_document_list), and also
the term's posting list. DocumentIDs which are in all_document_list
but not in the term's posting list are added to the result.
2. Once the end of the term's posting list is reached, add all
remaining documents in all_document_list (these documentIDs do not
appear in the term posting list) to the result.

AND:
1. Traverse both query term's postings lists using pointers and
perform mergesort with skip pointers.
2. We determine the skip size by taking the square root of the size of
each list. As this may not be an integer, we take floor the result.
3. To determine if a skip pointer exists at a particular index in the
postings list, we check if the index is divisible by the skip size for
the respective list.
4. If there is a skip pointer, and the value it points to is less than
the value the other lists' pointer is pointing to, we move to and
access that index directly.
5. Else, we add 1 to the pointers as we traverse the lists as we do in
regular mergesort.

AND NOT:
1. This is similar to AND. However, instead of adding terms which
appear in both lists to the result, we add terms which appear only in
the first list, and not the second.

OR:
1. Traverse both query term's postings lists using pointers, and add
values which appear in either list but not both.

After evaluating each boolean operation, we return the resulting
posting list and its length, preserving the structure of our
intermediate posting list.

## Skip Pointer Implementation

An interesting structure we did was implicit skip pointers. Since we
were using the python list, we could directly index long lists.
Nevertheless, we considered these alternatives:

(1) Storing byte offset skip pointer
We read the list, and store the byte offset for example:
[1.10, 4, 5, 6.20, 10, 13, 19, 21]

There is a skip pointer 1 to the 10th byte, and at 6 to the 20th byte.
This is impractical because once we read the list in memory, we do not
need the byte offset value.

(2) Store the index of where it is pointing to
[1.3, 4, 5, 6.7, 10, 13, 19, 21]
1 has a skip pointer to the 3rd element, 6.
6 has a skip pointer to the 7th element, 21.

This is impractical because we can just directly calculate the
skip size using sqrt(len(list)). Since we are using pointers to access
the list, we can move to any position quickly.

Instead of iterating down a list,
for element in list:
	do x

our pointers allow us to be flexible
while ptr <  len(posting):
	do x
	ptr += skipsize // a skip is easy to implement

Storing indices has no added benefit, and increases the size of the 
postings file by approximate sqrt(n), where n is the original size of
the postings file.

As such, we directly use list indices as skip pointers.

## AND Query Optimisation

Another way we could have optimised our search was to evaluate multiple
AND queries together. For example, the query A AND B AND C AND D can be
optimised by finding out which query terms A, B, C, D have the smallest
posting lists and merging the smaller posting lists first.

However, this is very difficult to execute in postfix notation since
we have to pop operands and check them. If they are not of the form
having consecutive AND, we would have to push them back to the operand
stack.

### Essay Questions
1. You will observe that a large portion of the terms in the dictionary
 are numbers. However, we normally do not use numbers as query terms to
search. Do you think it is a good idea to remove these number entries
from the dictionary and the postings lists?
Can you propose methods to normalize these numbers?
How many percentage of reduction in disk storage do you observe after
removing/normalizing these numbers?

We could remove number entries from the dictionary and the postings
list if we determine that the search engine's users do not use numbers
as query terms often. Users may still use numbers to conduct research
(e.g. data scientists, or historians) in their domain specific
searches.

To normalise numbers, we could use a regex based approach. With this,
decimal numbers, numbers expressed with commas (e.g. 1,234), dates in
standard formats (dd/mm/yy OR dd.mm.yy OR dd month year etc.), phone
numbers from different areas, etc. can all be normalised. There might
still exist some special edge cases which may be able to be handled
using different methods.

When we remove numbers from the dictionary and postings (by changing
the boolean value of REMOVE_NUMBERS from False to True), the file size
reduces accordingly:

                  	[with numbers] 	[without numbers]
dictionary.txt -> 	1113 kb         653 kb
postings.txt ->  	3103 kb         2819 kb

The dictionary decreases by 41.3% while the postings decreases by 9.15%.
Numbers don't seem to appear frequently but are in many variations.
Hence, the dictionary size decreases a lot while the postings doesn't
decrease by as significant an amount.

2. What do you think will happen if we remove stop words from the
dictionary and postings file? How does it affect the searching phase?

The reuters database actually provides a predefined list of stop words
which can be used to filter out the terms. Stop words will, firstly,
reduce the size of the postings file by a significant
amount. This is especially the case in a news article collection, which
contains text in prose. Nevertheless, the nature of the data
(news articles) also means there are a lot of terms, names and numbers
present. As a result, there is no significant size reduction in the
dictionary file.

			[with stop words]	[stop word removal]
dictionary.txt ->	1113 kb			1111 kb
postings.txt ->		3103 kb			2384 kb

Stop words, when given in search terms, will be ignored (since they
will be read as "do not exist" in the dictionary. It is unlikely that a
stop word will drastically change the result for AND operations.
However, a stop word in OR operations will explode the merging time.
In a NOT operation, it will quickly reduce the size of the resulting
list to be close to zero. This scenario is unlikely because users will
likely not search for documents "without the word 'of'", for instance.

To look at the impact of stop word removal, one can toggle the boolean
value in index.py

3. The NLTK tokenizer may not correctly tokenize all terms. What do you
observe from the resulting terms produced by sent_tokenize() and
word_tokenize()? Can you propose rules to further refine these results?

We observe that the tokens are sometimes not properly split.

For instance, 'I'm a dog and it's great!' splits into
["I", "'m", "a", "dog", "and", "it", "'s", "great", '!'].

If we instead use wordpunct_tokenizer, it would split into
["I", "'", "m", "a", "dog", "and", "it", "'", "s", "great", '!'].

wordpunct_tokenizer splits all the special symbols, which may bring us
closer to the correct tokenization of terms.

We could also implement more constraints for words which seem to lose
meaning after tokenization. For instance, if we expect an apostrophe
in a word, we can create a special case which handles these words.

== Files included with this submission ==

index.py -- program to index the corpus
search.py -- program to process queries
dictionary.txt -- dictionary of terms mapped to frequencies and IDs
postings.txt -- postings list

We also have additional files as proof of our experimentation.
dictionary-stopwords-removed.txt -- dictionary with stopwords removed
postings-stopwords-removed.txt -- postings with stopwords removed
dictionary-numbers-removed.txt -- dictionary with numbers removed
postings-numbers-removed.txt -- postings with numbers removed

== Statement of individual work ==

[X] I, JOYCE YEO SHUHUI, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.

[X] I, ANU KRITI WADHWA, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.

== References ==
# Reading in documents:
	https://www.pythonforbeginners.com/code-snippets-source-code/python-os-listdir-and-endswith
# Using Porter Stemmer:
	http://www.nltk.org/howto/stem.html
	https://pythonprogramming.net/stemming-nltk-tutorial/
# Using tokenizer:
	https://www.nltk.org/api/nltk.tokenize.html
# Changing string to lower case:
	https://www.tutorialspoint.com/python/string_lower.htm
# Using linecache:
	https://docs.python.org/2/library/linecache.html
# Using pickle:
	https://pymotw.com/2/pickle/
	https://stackoverflow.com/questions/22216076/unicodedecodeerror-utf8-codec-cant-decode-byte-0xa5-in-position-0-invalid-s
# Using ast:
	https://docs.python.org/2/library/ast.html
# Setting file current position to offset:
	https://www.tutorialspoint.com/python/file_seek.htm
# Convert list to space-separated string:
	https://stackoverflow.com/questions/13094918/convert-list-of-strings-to-space-separated-string
