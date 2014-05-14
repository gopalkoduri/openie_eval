import requests


def spotlight_linker(text):
    res = requests.post('http://itri.s.upf.edu:2222/rest/annotate',
                        data={'text': text, 'confidence': '0.2', 'support': '5'},
                        headers={"Accept": "application/json"})
    return res.json()


def map_arguments(relations):
    for relation in relations:
        for part in ['arg1', 'rel', 'arg2']:
            arg1_entities = spotlight_linker(relation[part])
            if 'Resources' in arg1_entities.keys():
                relation[part+'_entities'] = arg1_entities
    return relations


def clean_by_length(relations, arg_maxlen=40, rel_maxlen=25):
    clean_relations = []
    for rel in relations:
        if 'arg1_entities' not in rel.keys() or 'arg2_entities' not in rel.keys():
            continue
        if len(rel['arg1']) <= arg_maxlen and len(rel['arg2']) <= arg_maxlen \
                and len(rel['rel']) <= rel_maxlen:
            clean_relations.append(rel)
    return clean_relations