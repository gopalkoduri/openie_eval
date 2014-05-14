import re
import pickle
import codecs
import collections
from os.path import exists, basename, expanduser

import requests
from unidecode import unidecode

home = expanduser("~")
extracted_wiki_data = home+"/data/wiki/extracted"

import sys
sys.path.append(home + '/workspace/')

from wiki_tools import wiki_indexer as wi
reload(wi)


class Page():
    """
    A page object has all the information about a given page.

    -> Clean content (cleaned by removeing braces and quotes,
    and filtering out sentences that are too short to be sentences)

    -> Parsed content from Stanford NLP tools

    -> Entity linked content from DBpedia spotlight

    -> Also contains functions to handle some I/O
    """

    def __init__(self, title, index=None, keyword='carnatic_music'):
        self.title = title
        self.keyword = keyword

        if index:
            path = home + '/data/text-analysis/plain_text/' + keyword + '/' + unicode(index) + '.pickle'
            try:
                self.content = pickle.load(file(path))
            except IOError:
                print "Unable to locate the file with text content, tried to look here: ", path
            path = home + '/data/text-analysis/parsed_text/' + keyword + '/' + unicode(index) + '.pickle'
            try:
                self.parsed_content = pickle.load(file(path))
            except IOError:
                print "Unable to locate the file with text content, tried to look here: ", path

    def set_content(self, wiki_index):
        """
        Call this function if it fails to locate the file with text content.
        """
        self.content = wi.get_page_content(self.title, wiki_index)
        #self.content = p.clean_content(self.content)

    def serialize(self, path):
        pickle.dump(self, file(path, 'w'))

    def serialize_content(self, path):
        codecs.open(path, "w", "utf-8").write(self.content)


class Processor():
    def __init__(self):
        self.max_chars_reference = 30
        self.min_chars_clean_line = 10
        self.min_words_clean_line = 3

    def clean_content(self, content):
        if content == "":
            return
        #Remove content in braces and remove quotes
        braces = re.findall('\(.*?\)', content)
        braces.extend(re.findall('\[.*?\]', content))
        for b in braces:
            content = content.replace(b, '')
        content = content.replace('"', '')
        content = content.replace("'", '')

        #Discard the lines too short
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if len(line) >= self.min_chars_clean_line and len(line.split()) >= self.min_words_clean_line:
                clean_lines.append(line.strip('.'))

        content = unidecode('. '.join(clean_lines))
        return content

    @staticmethod
    def tokenized_sentences(parsed_content):
        sentences = []
        for sentence in parsed_content['root']['document']['sentences']['sentence']:
            sentences.append(' '.join([token['word'] for token in sentence['tokens']['token']
                                       if type(token) == collections.OrderedDict]))
        return sentences

    #The following funcitons are for anaphora resolution

    def get_patch(self, dictdata, replacement_info):
        sent_index = replacement_info[1]
        token_start = replacement_info[2]
        token_end = replacement_info[3]
        replacement = ' '.join(i['word'] for i in dictdata['root']['document']['sentences']['sentence'][sent_index]['tokens']['token'][token_start:token_end])
        return replacement

    def stitch_sentence(self, sent_index, replacements, dictdata):
        """
        replacements is a dictionary with the folliwing structure:
        replacements[begin_index] = [end_index, repl_sent_index, repl_word_begin, repl_word_end]
        """
        words = dictdata['root']['document']['sentences']['sentence'][sent_index]['tokens']['token']
        i = 0
        stitched_sentence = ""
        while i < len(words):
            if i in replacements.keys():
                #add the replacement to the stitched sentence
                stitched_sentence += " "+self.get_patch(dictdata, replacements[i])
                #skip to the next word after the replacement
                i = replacements[i][0]
            else:
                stitched_sentence += " "+words[i]['word']
                i += 1
        return stitched_sentence

    def get_replacements(self, parsed_content):
        replacements = {}
        for coref_bunch in parsed_content['root']['document']['coreference']['coreference']:
            #Heuristic 1: replace the coreference if it is a single word
            #Heuristic 2: the reference and the replacement should not be too long (50 chars?)
            #Heuristic 3: the reference must have alteast one capitalized letter

            #Improvement 1: map the reference and the coreference onto wiki using spotlight.
            #If the reference has more than one mapping, choose the 'closest'/'most relevant' one.
            #The closeness/relevance can be obtained by constraining the 'relevance' to set of pages
            #in the domain and/or whether the mapped argument in the reference refers to the
            #same subject as the mention. Check this improvement, with and without Heuristics.

            reference = coref_bunch['mention'][0]
            capitalized = any([c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in reference['text']])
            if len(reference['text']) > self.max_chars_reference or not capitalized:
                #print reference['text'], 'discarded for a seed as it is not capitalized/long'
                continue

            #remember that sentence and word indexes should be adjusted from 1 to 0
            for mention in coref_bunch['mention'][1:]:
                if len(mention['text']) > self.max_chars_reference or int(mention['end'])-int(mention['start']) != 1:
                    #print mention['text'], 'is not being replaced as it is long/not a single word'
                    continue
                if int(mention['sentence'])-1 in replacements.keys():
                   replacements[int(mention['sentence'])-1][int(mention['start'])-1] = [int(mention['end'])-1, int(reference['sentence'])-1,
                                                                                   int(reference['start'])-1, int(reference['end'])-1]
                else:
                   replacements[int(mention['sentence'])-1] = {int(mention['start'])-1: [int(mention['end'])-1, int(reference['sentence'])-1,
                                                                                   int(reference['start'])-1, int(reference['end'])-1]}
        return replacements

    def anaphora_resolution(self, parsed_content):
        all_sentences = Processor.tokenized_sentences(parsed_content)
        replacements = self.get_replacements(parsed_content)
        for sent_index, sent_replacements in replacements.items():
            all_sentences[sent_index] = self.stitch_sentence(sent_index, sent_replacements, parsed_content)
        return all_sentences


#wiki_index = pickle.load(file(expanduser('~')+'/data/text-analysis/wiki_index.pickle'))
wiki_index = {}
tp = Processor()

from celery import Celery
app = Celery('text_processor', broker='amqp://guest:guest@devaraya.s.upf.edu')


@app.task
def plain_text(page, f_path):
    """
    Gets the plain text, cleans them
    """
    if exists(f_path):
        print False
    p = Page(page)
    p.set_content(wiki_index)
    try:
        p.content = tp.clean_content(p.content)
    except:
        print False
    try:
        p.serialize_content(f_path)
    except:
        print False
    print True


@app.task
def entity_link(input_file, out_dir, spotlight_server):
    text = codecs.open(input_file).read()
    res = requests.post('http://'+spotlight_server+'.s.upf.edu:2222/rest/annotate',
                        data={'text': text, 'confidence': '0.2', 'support': '5'},
                        headers={"Accept": "application/json"})
    output_file = out_dir+basename(input_file)[:-4]+'.pickle'
    pickle.dump(res.json(), file(output_file, 'w'))