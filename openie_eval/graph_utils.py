import cStringIO
import graph_tool.all as gt
import networkx as nx
import numpy as np


def propmap_len(vertices, propmap):
    count = 0
    for v in vertices:
        if propmap[v]:
            count += 1
    return count


def convert_graph(src_g, to="graphtool"):
    buf = cStringIO.StringIO()
    if to == "graphtool":
        nx.write_graphml(src_g, buf, encoding='utf-8')
        buf.flush()
        buf.reset()
        dest_g = gt.Graph()
        dest_g.load(buf, fmt="xml")
    else:
        src_g.save(buf, fmt="xml")
        buf.flush()
        buf.reset()
        dest_g = nx.read_graphml(buf, node_type=unicode)
    return dest_g


#Node-related tasks

def sample_graph(g, num_nodes=100):
    nodes = np.array(g.nodes())
    indices = np.unique(np.random.random_integers(0, len(nodes), num_nodes+100))[:num_nodes]
    nodes = nodes[indices]
    sub_graph = g.subgraph(nodes)
    return sub_graph


#Edge-related tasks

def filter_by_edgeweight(g, thresh, weight_type="similarity"):
    filt_g = g.copy()
    for u, v, d in filt_g.edges(data=True):
        if weight_type == "distance":
            if d["weight"] > thresh:
                filt_g.remove_edge(u, v)
        elif weight_type == "similarity":
            if d["weight"] < thresh:
                filt_g.remove_edge(u, v)

    nodes = filt_g.nodes()
    for n in nodes:
        if filt_g.degree(n) == 0:
            filt_g.remove_node(n)

    return filt_g


def invert_weights(g):
    for u, v, d in g.edges(data=True):
        d["weight"] = 1.0-d["weight"]+0.000001
    return g


def filter_graph_edges(g, disparity_filter_signif_level):
    """
    A large number of complex systems find a natural abstraction in the form of weighted networks whose nodes represent
    the elements of the system and the weighted edges identify the presence of an interaction and its relative strength.
    In recent years, the study of an increasing number of large-scale networks has highlighted the statistical
    heterogeneity of their interaction pattern, with degree and weight distributions that vary over many orders of
    magnitude. These features, along with the large number of elements and links, make the extraction of the truly
    relevant connections forming the network's backbone a very challenging problem. More specifically, coarse-graining
    approaches and filtering techniques come into conflict with the multiscale nature of large-scale systems. Here, we
    define a filtering method that offers a practical procedure to extract the relevant connection backbone in complex
    multiscale networks, preserving the edges that represent statistically significant deviations with respect to a
    null model for the local assignment of weights to edges. An important aspect of the method is that it does not
    belittle small-scale interactions and operates at all scales defined by the weight distribution. We apply our
    method to real-world network instances and compare the obtained results with alternative backbone
    extraction techniques. (http://www.pnas.org/content/106/16/6483.abstract)
    """

    print 'Filtering with ' + str(100*(1-disparity_filter_signif_level))+'% confidence ...',

    if type(g) == nx.classes.digraph.DiGraph:
        indegree = g.in_degree(weight=None)
        outdegree = g.out_degree(weight=None)
        instrength = g.in_degree(weight='weight')
        outstrength = g.out_degree(weight='weight')

        edges = g.edges()
        for i, j in edges:
            pij = float(g[i][j]['weight'])/float(outstrength[i])
            pji = float(g[i][j]['weight'])/float(instrength[j])
            aij = (1-pij)**(outdegree[i]-1)
            aji = (1-pji)**(indegree[j]-1)
            if aij < disparity_filter_signif_level or aji < disparity_filter_signif_level:
                continue
            g.remove_edge(i, j)

        nodes = g.nodes()
        for n in nodes:
            if g.degree(n) < 1:
                # print n
                g.remove_node(n)

    elif type(g) == nx.classes.digraph.Graph:
        degree = g.degree(weight=None)
        strength = g.degree(weight='weight')

        edges = g.edges()
        for i, j in edges:
            pij = float(g[i][j]['weight'])/float(strength[i])
            aij = (1-pij)**(degree[i]-1)
            if aij < disparity_filter_signif_level:
                continue
            g.remove_edge(i, j)

        nodes = g.nodes()
        for n in nodes:
            if g.degree(n) < 1:
                # print n
                g.remove_node(n)

    return g
