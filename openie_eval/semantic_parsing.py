from __future__ import division
import networkx as nx
import json


def get_parsed(sem_out):
    #any relation is of type Head.Child.n (X , Y)
    #special cases being of type OPERATION(X)

    parsed = []
    special = {}
    for part in sem_out:
        #part = 'raga.in.2(7:e , 10:x'
        temp = part.strip(")").split('(')

        HCn = temp[0].split('.')
        #HCn = 'raga.in.2'

        arg_info = temp[1]
        #arg_info = '7:e , 10:x'

        temp = arg_info.split(' , ')
        if len(temp) < 2:
            if HCn[0] in special.keys():
                special[HCn[0]].append(temp[0])
            else:
                special[HCn[0]] = temp #temp is a list
        else:
            X = temp[0]
            #X = '7:e'

            Y = temp[1]
            #Y = '10:x'
            temp = {'X': X, 'Y': Y, 'HCn': HCn}
            parsed.append(temp)
    return [parsed, special]


def graph_relations(parsed, special):
    rg = nx.DiGraph()
    for i in parsed:
        if i['X'][-1] == 'e':
            if len(i['HCn']) == 1:
                pass
                #print 'Unhandled:', i

            elif len(i['HCn']) == 2:
                #same as when len(i['HCn']) == 3 and i['HCn'][0] == i['HCn'][1]
                #X-Y
                if i['HCn'][1] == '1':
                    edge_label = 'subject'
                else:
                    edge_label = 'object'
                rg.add_edge(i['X'], i['Y'], {'label': edge_label})

                #X->H
                rg.add_edge(i['X'], i['HCn'][0], {'label': 'predicate'})

            elif len(i['HCn']) == 3:
                #two cases: eg: H.H.2 (X, Y) and H.C.2 (X, Y)
                #first case: add X->Y with label subject (1) or object (2)
                #            add X->H with label predicate
                #
                #second case: add X->H with label predicate
                #             add H->C with label preposition
                #             add C->Y with label value

                #first case
                if i['HCn'][0] == i['HCn'][1]:
                    #X-Y
                    if i['HCn'][2] == '1':
                        edge_label = 'subject'
                    else:
                        edge_label = 'object'
                    rg.add_edge(i['X'], i['Y'], {'label': edge_label})

                    #X->H
                    if 'NEGATION' in special.keys() and i['X'] in special['NEGATION']:
                        rg.add_edge(i['X'], 'not '+i['HCn'][0], {'label': 'predicate'})
                    else:
                        rg.add_edge(i['X'], i['HCn'][0], {'label': 'predicate'})

                #second case
                else:
                    if 'NEGATION' in special.keys() and i['X'] in special['NEGATION']:
                        rg.add_edge(i['X'], 'not '+i['HCn'][0], {'label': 'predicate'})
                        rg.add_edge(i['HCn'][0], 'not '+i['HCn'][1], {'label': 'preposition', 'rel': i['X']})
                    else:
                        rg.add_edge(i['X'], i['HCn'][0], {'label': 'predicate'})
                        rg.add_edge(i['HCn'][0], i['HCn'][1], {'label': 'preposition', 'rel': i['X']})

                    if i['HCn'][2] == '2':
                        rg.add_edge(i['HCn'][1], i['Y'], {'label': 'value', 'rel': i['X']})
                    else:
                        rg.add_edge(i['X'], i['Y'], {'label': 'subject'})

        elif i['X'][-1] == 's':
            #skip if X and Y have same index number
            x_ind = i['X'].split(':')[0]
            y_ind = i['Y'].split(':')[0]

            if len(i['HCn']) == 1:
                if i['Y'] != i['X']:
                    if x_ind == y_ind:
                        weight = 0.25
                    else:
                        weight = 0.5
                    if 'NEGATION' in special.keys() and i['X'] in special['NEGATION']:
                        rg.add_edge(i['Y'], i['HCn'][0], {'label': 'is not a', 'weight': weight})
                    else:
                        rg.add_edge(i['Y'], i['HCn'][0], {'label': 'is a', 'weight': weight})

            elif len(i['HCn']) == 2:
                if i['HCn'][1] == '1':
                    rg.add_edge(i['Y'], i['HCn'][0], {'label': 'prefix'})
                else:
                    rg.add_edge(i['Y'], i['HCn'][0], {'label': 'suffix'})

            elif len(i['HCn']) == 3:
                if i['HCn'][0] == i['HCn'][1]:
                    pass
                    #print 'Unhandled', i
                else:
                    if x_ind == y_ind:
                        weight = 0.25
                    else:
                        weight = 1
                    if 'NEGATION' in special.keys() and i['X'] in special['NEGATION']:
                        rg.add_edge(i['Y'], i['HCn'][1]+' '+i['HCn'][0], {'label': 'is not a', 'weight': weight})
                    else:
                        rg.add_edge(i['Y'], i['HCn'][1]+' '+i['HCn'][0], {'label': 'is a', 'weight': weight})

                    #rg.add_edge(i['HCn'][1], i['HCn'][0], {'label': 'a type of', 'weight': weight})
    return rg


def get_graph(semout, draw=False):
    #print data[n]
    parsed, special = get_parsed(semout)
    #print parsed, special

    rg = graph_relations(parsed, special)
    if draw:
        pos = nx.graphviz_layout(rg)
        nx.draw(rg, pos)
        edge_labels=dict([((u,v,),d['label'])
                     for u,v,d in rg.edges(data=True)])
        nx.draw_networkx_edge_labels(rg, pos, edge_labels=edge_labels)
    return rg


def get_triples_from_graph(rg):
    relations = []
    for node in rg.nodes():
        out_edges = rg.out_edges(node, data=True)
        if get_nodetype(node) == 'relation':
            #look for subject, predicate and object(s)
            #SPO(s)
            edge_labels = {edge[1]: edge[2]['label'] for edge in out_edges}

            subjects = [k for k, v in edge_labels.items() if v == 'subject']
            objects = [k for k, v in edge_labels.items() if v == 'object']
            predicates = [k for k, v in edge_labels.items() if v == 'predicate']
            labels = edge_labels.values()

            if 'subject' in labels and 'object' in labels and 'predicate' in labels:
                for o in objects:
                    #print 'spo: ', subjects[0], predicates[0], o
                    relation = [subjects[0], predicates[0], o]
                    relations.append(relation)
            #SP
            elif 'object' not in labels and 'subject' in labels and 'predicate' in labels:
                resolved_pairs = resolve_prepositions(rg, predicates[0])
                if len(resolved_pairs) == 0:
                    #print 'sp: ', subjects[0], predicates[0]
                    relation = [subjects[0], predicates[0]]
                    relations.append(relation)
                else:
                    for pair in resolved_pairs:
                        #print 'sp: ', subjects[0], predicates[0]+' '+pair[0], pair[1]
                        relation = [subjects[0], predicates[0]+' '+pair[0], pair[1]]
                        relations.append(relation)
            #OP
            elif 'subject' not in labels and 'object' in labels and 'predicate' in labels:
                resolved_pairs = resolve_prepositions(rg, predicates[0])
                if len(resolved_pairs) == 0:
                    #print 'op: ', objects[0], predicates[0]
                    relation = [objects[0], predicates[0]]
                    relations.append(relation)
                else:
                    for pair in resolved_pairs:
                        #print 'op: ', objects[0], predicates[0]+' '+pair[0], pair[1]
                        relation = [objects[0], predicates[0]+' '+pair[0], pair[1]]
                        relations.append(relation)

        elif get_nodetype(node) == 'unnamed':
            #print 'Useless', node
            pass
        elif get_nodetype(node) == 'indexed_leaf' or get_nodetype(node) == 'unindexed_leaf':
            #'is a' relations
            for edge in out_edges:
                if edge[2]['label'] == 'is a' or edge[2]['label'] == 'a type of':
                    if get_nodetype(edge[1]) == 'unindexed_leaf' or get_nodetype(edge[1]) == 'indexed_leaf':
                        #print 'is: ', node, edge[2]['label'], edge[1]
                        relation = [node, edge[2]['label'], edge[1]]
                        relations.append(relation)
        else:
            pass
            #print 'Unhandled: ', node
    return relations


#The following functions are to expand the relations from graph by cleaning the arguments,
# filling in the suffixes and prefixes, removing indices etc.

def get_nodetype(node):
    if ':' in node:
        parts = node.split(':')
        if parts[1] == 'e':
            return 'relation'
        elif parts[1] == 'x':
            return 'unnamed'
        else:
            return 'indexed_leaf'
    else:
        return 'unindexed_leaf'


def resolve_unnamed(g, node):
    """
    Eg: 7:x -> Carnatic music
    """
    out_edges = g.out_edges(node, data=True)
    is_a_relations = [(edge[1], edge[2]['weight']) for edge in out_edges if edge[2]['label'] == 'is a']
    if is_a_relations:
        is_a_relations = sorted(is_a_relations, key=lambda x: x[1], reverse=True)
        if get_nodetype(is_a_relations[0][0]) == 'indexed_leaf':
            return strip_index(is_a_relations[0][0])
        else:
            return is_a_relations[0][0]
    else:
        return '#Unknown'


def strip_index(indexed_node):
    parts = indexed_node.split(':')
    if len(parts) > 1:
        return parts[1]
    return parts[0]


def get_fullname(graph, node):
    """
    Get suffixes and prefixes as available.
    """
    out_edges = graph.out_edges(node, data=True)
    name = strip_index(node)
    for edge in out_edges:
        if edge[2]['label'] == 'prefix':
            name = edge[1]+' '+name
        if edge[2]['label'] == 'suffix':
            name = name+' '+edge[1]
    return name


def resolve_prepositions(graph, predicate_node):
    out_edges = graph.out_edges(predicate_node, data=True)
    prepositions = [(edge[1], edge[2]['rel']) for edge in out_edges if edge[2]['label'] == 'preposition']
    resolved_pairs = []
    for p, prel in prepositions:
        out_edges = graph.out_edges(p, data=True)
        values = [edge[1] for edge in out_edges if edge[2]['label'] == 'value' and edge[2]['rel'] == prel]
        for v in values:
            resolved_pairs.append((p, v))
    return resolved_pairs


def expand_relations(graph, relations):
    expanded_relations = {'valid': [], 'reifications': [], 'unhandled': []}

    for relation in relations:
        if len(relation) == 3:
            if get_nodetype(relation[2]) == 'relation':
                expanded_relations['reifications'].append(relation)
                continue

            if get_nodetype(relation[0]) == 'unnamed':
                relation[0] = get_fullname(graph, resolve_unnamed(graph, relation[0]))
            else:
                relation[0] = get_fullname(graph, relation[0])
            if get_nodetype(relation[2]) == 'unnamed':
                relation[2] = get_fullname(graph, resolve_unnamed(graph, relation[2]))
            else:
                relation[2] = get_fullname(graph, relation[2])

            expanded_relations['valid'].append(relation)
        else:
            expanded_relations['unhandled'].append(relation)
    return expanded_relations


def filter_relations(relations, wiki_entities):
    filtered_relations = []
    for rel in relations:
        if rel['arg1'] in wiki_entities:# or rel[2] in wiki_entities:
            filtered_relations.append(rel)
    return filtered_relations


def get_relations(data):
    relations = []
    #progress = progressbar.ProgressBar(len(data))
    for ind in xrange(len(data)):
        temp = json.loads(data[ind])
        if 'relations' not in temp.keys():
            continue
        rg = get_graph(temp['relations'][0], draw=False)
        res = get_triples_from_graph(rg)
        res = expand_relations(rg, res)
        for rel in res['valid']:
            relations.append({'arg1': rel[0].lower().replace('_', ' '),\
                              'rel': rel[1].lower().replace('_', ' '),\
                              'arg2': rel[2].lower().replace('_', ' '), \
                              'full_sentence': temp['sentence']})
        #progress.animate(ind)
    return relations
