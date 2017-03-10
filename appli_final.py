##################################BIBLIOTEQUE################################
# coding: utf8
from __future__ import unicode_literals
import operator 
import json
import sys
from collections import Counter
import re
import nltk
from nltk.tokenize import word_tokenize
import redis
from nltk.corpus import stopwords
import string
from nltk import bigrams 
from unidecode import unidecode
from nltk.stem.snowball import SnowballStemmer
from gensim import corpora
import os
from collections import defaultdict
from pprint import pprint  # pretty-printer
import redis
import sys
import re
import json
from gensim import models ,corpora, similarities
#############################FONCTIONS####################################



def json2redis(filename,database):
    with open(filename, 'r') as f:
        for line in f:
            m = re.search(".",line) # Permet D'éviter le bug lorsqu'il y a un saut de ligne    
            if m != None :
                try :                
                    tweet = json.loads(line)
                    date = json.dumps(tweet['created_at'])
                    database.hset(filename,date,tweet)
                    print('Importation réussi')
                except:
                    print('failed try push json into redis')
                    pass

def getTweetText(tweet):
    print('getTweetText')
    print(type(tweet))
    print(tweet)
    tweet = json.loads(tweet)
    print(type(tweet))
    text = json.dumps(tweet['text'],ensure_ascii = False) # récupere le texte du tweet
    return text

def redis2json(hashname, database):
    jsonfile = database.hvals(hashname)
    return jsonfile

def json2tweet(line):
    print('json2tweet')
    tweet = json.loads(line)
    return tweet

# Trait un texte en entrer (unicode) et retourne le texte tokeniser (mode = t),  stemmer (mode = s)
def text2tokens(text,mode):
    
    emoticons_str = r"""
        (?:
            [:=;] # Eyes
            [oO\-]? # Nose (optional)
            [D\)\]\(\]/\\OpP] # Mouth
        )"""
     
    regex_str = [
        emoticons_str,
        r'<[^>]+>', # HTML tags
        r'(?:@[\w_]+)', # @-mentions
        r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)", # hash-tags
        r'http[s]?://(?:[a-z]|[0-9]|[$-_@.&amp;+]|[!*\(\),]|(?:%[0-9a-f][0-9a-f]))+', # URLs
     
        r'(?:(?:\d+,?)+(?:\.?\d+)?)', # numbers
        r"(?:[a-z][a-z'\-_]+[a-z])", # words with - and '
        r'(?:[\w_]+)', # other words
        r'(?:\S)', # anything else
        
    ]
        
    tokens_re = re.compile(r'('+'|'.join(regex_str)+')', re.VERBOSE | re.IGNORECASE)
    emoticon_re = re.compile(r'^'+emoticons_str+'$', re.VERBOSE | re.IGNORECASE)
    """
    The regular expressions are compiled with the flags re.VERBOSE, to allow spaces in the regexp to be ignored (see the multi-line emoticons regexp),
    and re.IGNORECASE to catch both upper and lowercases. The tokenize() function simply catches all the tokens in a string and returns them as a list.
    This function is used within preprocess(), which is used as a pre-processing chain: in this case we simply add a lowercasing feature for all the
    tokens that are not emoticons (e.g. :D doesn’t become :d).
    """
    punctuation = list(string.punctuation)
    stop = stopwords.words('french') + punctuation + ['>>','<<','<','>','via','le','les','a','rt'] # Liste des tokens à effacer

    stemmer = SnowballStemmer('french')
    tokens = tokens_re.findall(unidecode(text))
    tokens = [token if emoticon_re.search(token) else token.lower() for token in tokens]
    if mode == 't' :
        return tokens
    terms_stop = [term for term in tokens if term not in stop] # Crée une liste avec tout les termes sauf les termes stopé
    if mode == 's' :
        terms_stem = [stemmer.stem(term) for term in terms_stop ]
        return terms_stem

def txt2lda(monfichier):    
    
    with open(monfichier,'r') as f:    
        texts = [[tokens for tokens in text2tokens(line.decode('unicode-escape'),"s") if len(tokens) != 0 ] for line in f ]
        # remove words that appear only once            
        frequency = defaultdict(int)
        for text in texts:
            for token in text:
                frequency[token] += 1
        texts = [[token for token in text if frequency[token] > 1] for text in texts]
        dictionary = corpora.Dictionary(texts)
        dictionary.save('/tmp/emploi.dict')  # store the dictionary, for future reference
        print(dictionary)
        corpus = [dictionary.doc2bow(text) for text in texts]
        corpora.MmCorpus.serialize('/tmp/emploi.mm', corpus)  # store to disk, for later use
        print(corpus)
        print(len(texts))
        
        lda = models.LdaModel(corpus, id2word=dictionary, num_topics=len(texts))
        print("Génération d'un model LDA...")
        pprint(lda)
        print("LDA généré")
        
        doc = " Le marche de l'emploi est en chute libre, le nombre de chomeur ne cesse d'augmenter "
        doc_bow = dictionary.doc2bow(text2tokens(doc.decode('unicode-escape'),"s"))
        print(lda[doc_bow]) # get topic probability distribution for a document
        vec_lda = lda[doc_bow]
        for i in vec_lda : 
            topicid = i[0]
            print(i[0])
            print(lda.get_topic_terms(topicid, topn=10))
        index = similarities.MatrixSimilarity(lda[corpus]) # transform corpus to LDA space and index it

        index.save('/tmp/emploi.index')
        index = similarities.MatrixSimilarity.load('/tmp/emploi.index')

        sims = index[vec_lda]# perform a similarity query against the corpus
       # print(list(enumerate(sims))) # print (document_number, document_similarity) 2-tuples
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        print(sims) # print sorted (document number, similarity score) 2-tuples
        print(sorted(dictionary.token2id))
        f.close()
    return lda
       
        
    
       


######################################## MAIN ################################

while True :
    print("1 : Tracker des tweet sur twitter ")
    print("2 : Stocker JSON dans redis ")
    print("3 : Recuperer texte d'un JSON provenant de redis ")
    print("4 : tokeniser un text ")
    print('5 : Créer un corpus avec le model LDA')
    mode = input("Quel mode choisir ? ")
    if mode == 1 :
        print('Non implémenté')
    if mode == 2 :
        basejson = redis.StrictRedis(host='127.0.0.1',port=6379,db=0)  
        filename = input(" Nom fichier json : ")
        json2redis(filename,basejson)
    if mode == 3 :
        basejson = redis.StrictRedis(host='127.0.0.1',port=6379,db=0)
        filename = input(" Nom fichier json : ")
        jsonfile = redis2json(filename,basejson)

        for line in jsonfile:            
            print('line')
            print(line)
            # tweet = json2tweet(line)
            text = getTweetText(line.decode('unicode-escape'))
            print(text)
            
    if mode == 4 :
        print('1 : tokeniser un fichier .txt')
        print('2 : tokeniser un une chaine de caractere')
        sousmode = input("Quel mode choisir ? ") 
        if sousmode == 1 :        
            filename = input("Quel est le nom du fichier ou chemain d'acces ? ")
            try :
                with open(filename,'r') as f:    
                    for line in f:        
                        tokens = text2tokens(line.decode('unicode-escape'),"s")
                        print(tokens)
            except :
                print(" Erreur 41 ")
                print("le nom du fichier doit être de la forme 'monfichier.txt' ou '/sousdossier/monfichier.txt' encodé en ANSII")

        if sousmode == 2 :        
            chaine = input("Entrez la chaine de caractere :  ")
            try :                                        
                tokens = text2tokens(chaine.decode('unicode-escape'),"s")
                print(tokens)
            except :
                print(" Erreur 42 ")
               


    if mode == 5 :
        filename = input("Quel est le nom du fichier ou chemain d'acces ? ")
        lda = txt2lda(filename)
       
