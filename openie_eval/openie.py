import re
import codecs

from os.path import expanduser
home = expanduser("~")

import sys
sys.path.append(home + '/workspace')


def get_openie_relations(input_file):
    """
    Each line in the input_file will have 6 fields when split by a tab.

    0. Confidence score
    1. Context (i.e., condition or something that is like a reification)
    2. Argument 1
    3. Relation
    4. Argument 2, 3 ... (Simple/Spatial/Temporal)
    5. The entire input sentence
    """
    relations = codecs.open(input_file, encoding='utf-8').readlines()

    arg_starts = ['SimpleArgument\(', 'SpatialArgument\(', 'TemporalArgument\(']
    rel_start = 'Relation\('
    end = ',List\('

    relations_parsed = []

    for rel_data in relations:
        rel_parts = rel_data.split('\t')

        #We are skipping those relations which have some reification kind of context
        if rel_parts[1]:
            continue

        #Confidence score
        confidence = float(rel_parts[0])

        #First argument
        expr = arg_starts[0] + '(.*)' + end
        arg1 = re.search(expr, rel_parts[2])
        if arg1:
            arg1 = arg1.group(1)
        else:
            continue

        #Relation
        expr = rel_start + '(.*)' + end
        rel_string = re.search(expr, rel_parts[3])
        if rel_string:
            rel_string = rel_string.group(1)
        else:
            continue

        #Second argument, can be multiple ...
        arg2 = []
        temp = rel_parts[4].split(');')
        for chunk in temp:
            for arg_start in arg_starts:
                expr = arg_start + '(.*)' + end
                arg = re.search(expr, chunk)
                if arg:
                    arg2.append(arg.group(1))

        # ... so, we split each argument in a relation
        for arg in arg2:
            rel_dict = {'arg1': arg1.lower(), 'rel': rel_string.lower(), 'arg2':
                        arg.lower(), 'confidence': confidence, 
                        'full_sentence': rel_parts[-1].strip()}
            relations_parsed.append(rel_dict)

    return relations_parsed


def get_reverb_relations(input_file):
    """
    The values in each line are tab separated, with the following information:
    0: file name from which the sentence is read
    1: sent_number
    2: arg1
    3: rel
    4: arg2
    5: arg1 start index
    6: arg1 end index
    7: rel start index
    8: rel end index
    9: arg2 start index
    10: arg2 end index
    11: confidence
    12: the actual sentence
    13: POS tags
    14: Shallow parse output
    15: arg1_normalized
    16: rel_normalized
    17: arg2_normalized
    """
    relations = codecs.open(input_file, encoding='utf-8').readlines()
    relations_parsed = []
    for rel_data in relations:
        rel_data = rel_data.lower().split('\t')
        relation = {}
        relation['arg1'] = rel_data[2]
        relation['rel'] = rel_data[3]
        relation['arg2'] = rel_data[4]
        
        relation['arg1_norm'] = rel_data[15]
        relation['rel_norm'] = rel_data[16]
        relation['arg2_norm'] = rel_data[17]
        
        relation['confidence'] = rel_data[11]
        relation['full_sentence'] = rel_data[12]
        relations_parsed.append(relation)
        
    return relations_parsed
