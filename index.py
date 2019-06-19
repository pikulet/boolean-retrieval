#!/usr/bin/python
import re
import nltk
import sys
import getopt

from nltk.stem.porter import *
import os
import linecache
import pickle
import ast

########################### DEFINE CONSTANTS ###########################
PORTER_STEMMER = PorterStemmer()
END_LINE_MARKER = '\n'
STOP_WORD_REMOVAL = False
REMOVE_NUMBERS = False
STOP_WORD_FILE = 'stopwords'

######################## COMMAND LINE ARGUMENTS ########################

### Read in the input files as command-line arguments
###
def read_files():
    def usage():
        print("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")

    input_directory = output_file_dictionary = output_file_postings = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for o, a in opts:
        if o == '-i': # input directory
            input_directory = a
        elif o == '-d': # dictionary file
            output_file_dictionary = a
        elif o == '-p': # postings file
            output_file_postings = a
        else:
            assert False, "unhandled option"

    if input_directory == None or output_file_postings == None or output_file_dictionary == None:
        usage()
        sys.exit(2)

    return input_directory, output_file_dictionary, output_file_postings

############################## DOCUMENT INDEXING ##############################

### Driver function
###
def main():
    input_directory, output_file_dictionary, output_file_postings = read_files()
    buildList(input_directory, output_file_dictionary, output_file_postings)

### The main algorithm to read through the corpus and process the data
###

def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)

def buildList(corpus, dictionary_file, postings_file):

    stop_words = {}
    # retrieve stop words
    if STOP_WORD_REMOVAL:
        with open(STOP_WORD_FILE, 'r') as f:
            stop_words = set(f.read().splitlines())

    dictionary = Dict(dictionary_file)
    postings = Postings(postings_file)


    # search through a given path (".") for all files that endswith ".txt"
    # sort docIDs in increasing order
    allFiles = sorted([int(f) for f in os.listdir(corpus)])

    for docID in allFiles:          # for every document
        fileName = str(docID)
        postings.addDoc(docID)      # record documentID in postings file

        lineNum = 1             # start at the first line
        # retrieve data on first line
        line = linecache.getline(os.path.join(corpus, fileName), lineNum)

        while len(line) != 0:   # iterate through whole document until empty line is encountered
            # add data information
            buildListHelper(line, dictionary, postings, docID, stop_words)
            # proceed to the next line
            lineNum += 1
            # retrieve data on next line
            line = linecache.getline(os.path.join(corpus, fileName), lineNum)

    # save the postings to the disk, update offset for each term in dictionary
    postings.saveToDisk(dictionary)
    dictionary.saveToDisk()

### Normalise a token to standard form
### Here, we apply the porter stemmer and case folding
###
def normalise_term(term):
    stemmedWord = PORTER_STEMMER.stem(term)
    lowerStemmedWord = stemmedWord.lower()
    return lowerStemmedWord

### Add the data to our dictionary and postings record.
### Note that docName and docID are the same in this scenario
###
def buildListHelper(line, dictionary, postings, docID, stop_words):
    sentences = nltk.sent_tokenize(line)            # split line into sentences

    for s in sentences:
        words = nltk.word_tokenize(s)               # split sentences into words
        for w in words:
            if STOP_WORD_REMOVAL and w in stop_words:   # ignore stop words
                continue

            if REMOVE_NUMBERS and hasNumbers(w):
                continue

            normalisedTerm = normalise_term(w)

            # add data to dictionary and postings
            if dictionary.hasTerm(normalisedTerm):
                termID = dictionary.getTermID(normalisedTerm)

                # add docID to posting list for term
                addedNewDocID = postings.addDocIDToPosting(docID, termID)

                # add term frequency if a new document was encountered
                if addedNewDocID:
                    dictionary.addFreq(normalisedTerm)
            else:
                # term currently does not exist in dictionary
                termID = postings.addTermAndDocID(docID)        # returns index of added set, which is the new termID
                dictionary.addTerm(normalisedTerm, termID)
                postings.addDocIDToPosting(docID, termID)       # adds docID to posting list

########################## HELPER DATA STRUCTURES ##########################

### A dictionary class that keeps track of terms --> termFrequency, termOffset.
### termOffset is equivalent to termID, and is unique to every dictionary term.
### Initially, termOffset increases sequentially. After saving the postings file to disk,
### termOffset is the exact position (in bytes) of the term posting list in postings.txt
###
class Dict():
    def __init__(self, file):
        self.terms = {} # every term maps to a tuple of termFrequency, termOffset
        self.file = file

    def addTerm(self, term, termID):
        self.terms[term] = [1, termID]

    def hasTerm(self, term):
        return term in self.terms

    def getTerms(self):
        return self.terms

    def addFreq(self, term):
        self.terms[term][0] += 1

    def getTermID(self, term):
        return self.terms[term][1]

    def setOffset(self, term, offsetVal):
        self.terms[term][1] = offsetVal

    def saveToDisk(self):
        with open(self.file, 'wb') as d:
            pickle.dump(self.terms, d)

### A Postings class that collects all the posting lists, and all existing docIDs
###
class Postings(object):
    def __init__(self, file):
        self.file = file
        self.postingsList = []
        self.docsList = []
        self.currentID = -1

    def addTermAndDocID(self, docID):
        newPostingList = [docID]    # new list with one entry
        self.postingsList.append(newPostingList)

        self.currentID += 1
        return self.currentID       # return the index of the new posting list (termID)

    # Adds docID to the list of all docIDs. Since documents are processed in order,
    # docID is always strictly increasing
    def addDoc(self, docID):
        self.docsList.append(docID)

    # Add the docID to the posting list of termID if not already there
    def addDocIDToPosting(self, docID, termID):
        postingList = self.postingsList[termID]
        if docID != postingList[-1]:
            self.postingsList[termID].append(docID)
            return True
        return False

    # Saves the posting lists to file, and update offset value in the dictionary
    def saveToDisk(self, dictionary):
        with open(self.file, 'w') as p:
            p.write(' '.join([str(x) for x in self.docsList]) + END_LINE_MARKER)   # the first line is the list of all documents

            for t in dictionary.getTerms():
                termID = dictionary.getTermID(t)
                posting_list = self.postingsList[termID]

                dictionary.setOffset(t, p.tell()) # update dictionary with actual byte offset
                p.write(' '.join([str(x) for x in posting_list]) + END_LINE_MARKER)

if __name__ == "__main__":
    main()
