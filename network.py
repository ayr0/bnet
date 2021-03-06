import numpy as N
import networkx as nx
import itertools
import pydot
import matplotlib.pyplot as plt

class NodeException(Exception): pass

class Network(nx.DiGraph):
    
    def __init__(self, nodes=(), edges=tuple(), score=None):
        """Creates a Network.
        
        PARAMETERS:
            nodes       list of nodes in the network
            edges       list of edges in the network
            score       score to associate with the network
        
        RETURNS:
            instance of Network class
        """
        
        #nodes is a list of pebl.data.Variable instances.
        #edges can be:
        
            #* a list of edge tuples
            #* an adjacency matrix (as boolean numpy.ndarray instance)
            #* string representation (see Network.as_string() for format)
        
        super(Network, self).__init__()
        #initialize the lut in graph
        self.graph['inlut'] = {}
        self.graph['nilut'] = {}
        self.add_nodes_from(nodes)

        if isinstance(edges, N.ndarray):
            #create edges using adj mat.
            edg = self._adjmat_to_edges(edges)
        elif isinstance(edges, str) and edges:
            edg = [map(int, x.split(",")) for x in edges.split(";")]
        else:
            edg = edges
            
        self.add_edges_from(edg)
        
        #this store the network score.
        #If None, network is not scored, otherwise this is a float
        self.score = score

    def __hash__(self):
        return hash(tuple(self.edges()))

    def __cmp__(self, other):
        return cmp(self.score, other.score)

    def __eq__(self, other):
        return self.score == other.score and hash(self.edges) == hash(other.edges)

    def _add_node_attr(self, node, attr, value):
        """Add an attr to a node's dictionary"""
        
        self.node[node][attr] = value
    
    def _next_lut(self, lut):
        """Return next available id in LUT"""
        try:
            n = max(lut) + 1
        except ValueError:
            n = 0
        
        return n
    
    def _adjmat_to_edges(self, adjmat):
        """Convert adjmat to a tuple of edges"""
        rows,cols = adjmat.shape
        nodes = self.graph['inlut']
        
        return [(nodes[j],nodes[k]) for k in xrange(cols) for j in xrange(rows) if adjmat[j,k]]
    
    @property
    def ordering(self):
        return self.graph['inlut'].values()
        
    @property
    def adj_mat(self):
        return nx.adjacency_matrix(self)
        
    def add_edges_from(self, edges, attr_dict=None, **attr):
        """Add edges from [edges] to the network
        
        Will fail if nodes being connected by edges don't exist.
        This overrides the default behave of nx.DiGraph
        
        PARAMETERS: Same parameters as add_edges_from() of nx.DiGraph
            edges
            attr_dict   
            **attr
            
        RETURNS:
            None
        """
        
        if isinstance(edges, N.ndarray):
            edges = self._adjmat_to_edges(edges)
            
        for edge in edges:
            self.add_edge(edge[0], edge[1], attr_dict=attr_dict, **attr)
    
    def add_edge(self, u, v, attr_dict=None, **attr):
        """Add edge between nodes u and v.  u and v must exist otherwise exception is thrown
        
        Same parameters as add_edge() of nx.DiGraph
        """
        
        u_exist = u in self.nodes()
        
        if u_exist and v in self.nodes():
            super(Network, self).add_edge(u, v, attr_dict=attr_dict, **attr)
        else:
            if u_exist:
                raise NodeException("Node {0} does not exist!".format(v))
            else:
                raise NodeException("Node {0} does not exist!".format(u))
    
    def clear(self):
        """Clear all edges from network, but keep nodes"""
        self.remove_edges_from(self.edges())
        
    def add_nodes_from(self, nodes, **attr):
        """Same behavior as add_nodes_from() of nx.DiGraph"""
        super(Network, self).add_nodes_from(nodes, **attr)
            
        #add the nodes to the lut
        nexti = self._next_lut(self.graph['inlut'])
        self.graph['inlut'] = {i:n for i, n in enumerate(nodes, nexti)}
        self.graph['nilut'] = {n:i for i, n in self.graph['inlut'].iteritems()}
        
    def add_node(self, node, **attr):
        """Same behavior as add_node() of nx.DiGraph"""
        super(Network, self).add_node(node, **attr)
        
        #add the nodes to the lut
        nexti = self._next_lut(self.graph['inlut'])
        self.graph['inlut'].update({nexti: node})
        self.graph['nilut'].update({node: nexti})
        
    def get_id(self, node):
        """Get id of a node"""
        return self.nodes().index(node)
                
    def get_node_by_id(self, id):
        """Get a node by id"""
        
        return self.nodes()[id]
        
    def get_node_subset(self, node_ids):
        """Return a subset of nodes from node ids"""
        return [n for n in nodes() if n in node_ids]
        #return dict((k, self.nodeids[k]) for k in node_ids)
        
    def is_acyclic(self):
        """Uses a depth-first search (dfs) to detect cycles."""

        return nx.is_directed_acyclic_graph(self)    
        
    def cpt(self, node, state):
        """Return the cpt of state
        Since numer and denom are tracked separately,
        this function will divide the two and return the result
        
        PARAMETERS:
            node        Node of which to calculate the conditional  probability
            state       State of which to calculate the conditional probability
            
        RETURNS:
            None
        """
        
        if isinstance(node, int):
            node = self.graph['nilut'][node]
            
        if node in self.node:
            n = self.node[node].get('numer', None)
            d = self.node[node].get('denom', None)
            
            #we don't have frequency counts, so try for existing cpt table
            if n is None or d is None:
                try:
                    return self.node[node]['cpt'][state]
                except IndexError:
                    raise IndexError("Invalid state: ", state)
                except KeyError:
                    raise StandardError("No CPT table in this node")
                except:
                    raise Exception("Something went wrong... :(")
                    
            try:
                top = float(n[state])
                bottom = d[state]
                if d[state] == 0:
                    raise ZeroDivisionError
                else:
                    return float(n[state])/d[state]
            except IndexError:
                raise IndexError("Invalid state: ", state)
            except ZeroDivisionError:
                #no data has been collected, so assume 0 probability
                return 0.
            except:
                raise Exception("Something went wrong... :(")
        else:
            raise StandardError("Node {0} doesn't exist!".format(node))
        
    def jointprob(self, states):
        """Calculate the joint probability of state (2d numpy array)
        Each row is a state vector, and each column the state values
        
        P(state=(0,1,0,2,1,5)) = P(A=0|parents)
                                *P(B=1|parents)
                                *P(C=0|parents)
                                *P(D=2|parents)
        to aid in the computation, logs are used and then added and exponetiated
        at the end.
        
        The order of variables in the state vector should coincide with the indexes
        of the lookup table for network
        
        PARAMETERS:
            states      States to use in calculating the joint probability
            
        RETURNS:
            ndarray     two column array. first column are states
                        second column are the caculated joint probabilities for those states
        """
        states = N.atleast_2d(states)
        probs = N.zeros(states.shape)
        probs.fill(N.finfo(float).tiny)
        _node = self.node
        _graph = self.graph
        for index in N.ndindex(states.shape):
            #i=variable index, v=state value
            
            #get variable label
            var = _graph['inlut'][index[1]]
            #get the variable cpt dimensions (these are the parents of var)
            var_pred = _node[var]['cptdim']
            #get the parents node ids
            var_pred_ind = [_graph['nilut'][x] for x in var_pred]
            
            try:
                #we already have numeric states
                cptstate = tuple([states[index[0],p] for p in var_pred_ind])
            except KeyError:
                #if we already have state indexes
                cptstate = tuple([_node[v]['states_ind'][states[index[0],p]] for v, p in zip(var_pred, var_pred_ind)])
            except:                
                print "Invalid state: no state {1}".format(states[index[0],p])
                continue
            
            #print var, cptstate
            #print self.node[var]['cpt'].shape
            cptprob = self.cpt(var, cptstate)
            #print cptprob
            probs[index] = cptprob if cptprob != 0. else probs[index]
            
        
        probsl = N.sum(N.log(probs), axis=1)
        return N.c_[states, probsl]
        #return zip(states, probs)
       
    def layout(self, prog="dot", args=''): 
        """Determines network layout using Graphviz's dot algorithm.

        width and height are in pixels.
        dotpath is the path to the dot application.

        The resulting node positions are saved in network.node_positions.

        """

        self.node_positions = nx.graphviz_layout(self, prog=prog, args=args)
    
    def as_dotstring(self):
        """Returns network as a dot-formatted string"""

        return self.as_pydot().to_string()

    def as_dotfile(self, filename):
        """Saves network as a dot file."""

        nx.write_dot(self, filename)

    def as_pydot(self):
        """Returns a pydot instance for the network."""

        return nx.to_pydot(self)
    
################################################################################
#Factory Functions
################################################################################
def random_network(nodes, required_edges=(), prohibited_edges=(), max_attempts=50):
    """Creates a random network with the given set of nodes.

    Can specify required_edges and prohibited_edges to control the resulting
    random network.  
    
    max_attempts sets how many times to try to achieve the criteria.
    If we use up all max_attempts we cut density in half and try again.
    
    PARAMETERS:
        nodes                   nodes to have in network
        required_edges          edges required to be present in network
        prohibited_edges        edges required to not be present in network
        max_attempts            max number of attempts to create a random network
        
    RETURNS:
        Network         A random network
    """
    def _randomize(net, density=None):
        net.clear()
        n_nodes = len(net.nodes())
        nodes = net.graph['nilut']
        density = density or 1.0/n_nodes

        for attempt in xrange(max_attempts):
            # create an random adjacency matrix with given density
            adjmat = N.random.rand(n_nodes, n_nodes)
            adjmat[adjmat >= (1.0-density)] = 1
            adjmat[adjmat != 1] = 0
            
            # add required edges
            for src,dest in required_edges:
                adjmat[nodes[src], nodes[dest]] = 1

            # remove prohibited edges
            for src,dest in prohibited_edges:
                adjmat[nodes[src], nodes[dest]] = 0

            # remove self-loop edges (those along the diagonal)
            N.fill_diagonal(adjmat, 0)
            
            # set the adjaceny matrix and check for acyclicity
            net.add_edges_from(adjmat)

            if net.is_acyclic():
                return net

        # got here without finding a single acyclic network.
        # so try with a less dense network
        return _randomize(net, density=density/2.0)

    # -----------------------
    
    net = Network(nodes)
    
    return _randomize(net)
    
def randomDAG(nodes, white_edges=(), black_edges=(), prob=.5):
    """Generate a random DAG
    
    PARAMETERS:
        nodes           Nodes to have present in network
        white_edges     edges required to be present in network
        black_edges     not implemented yet
        prob            probability of adding an edge
        
    RETURNS:
        Network         A random directed acyclic graph
    """
    
    #shuffle the nodes
    N.random.shuffle(nodes)
    
    #add the white edges
    net = Network(nodes, white_edges)
    
    for e in itertools.combinations(nodes, 2):
        if N.random.randn() < prob:
            net.add_edge(*e)
    
    return net
    
def dist(net1, net2):
    """Return the distance between two networks
    Defined as how many edges must be added and removed to make net1==net2
    Networks must have the same number of nodes
    
    PARAMETERS:
        net1    Network
        net2    Network
    
    RETURNS:
        int     distance between networks
    """
    x, y = map(nx.adj_matrix, (net1, net2))

    if x.shape != y.shape:
        if x.shape > y.shape:
            #make it so y is always >= to x
            tmp = x
            x = y
            y = tmp
            
        x_tmp = N.zeros(y.shape)
        for i, v in N.ndenumerate(x):
            x_tmp[i] = v
        x = x_tmp
        
    return N.sum(N.abs(x-y))
    
def is_strongly_connected(G):
    """Can be passed and edge dictionary or Graph"""
    if isinstance(G, dict):
        return len(G.keys()) == nx.strongly_connected.number_strongly_connected_components(G)
    else:
        return nx.strongly_connected.is_strongly_connected(G)

def drawnet(g):
    nx.draw_graphviz(g)
    plt.show()
    
def pydotnet(control, cand, colorsame='black', controldiff='purple', canddiff='red'):
    """nets is a sequence of network objects.  The edges of the first are taken to be
    the universal set
    
    colorsame = color common edges
    color diffenrent = color unique edges
    """
    
    pdnet = pydot.Dot(graph_type='digraph')
    
    #add the nodes to the Graph
    nodes = control.nodes()
    [pdnet.add_node(n) for n in map(pydot.Node, nodes)]
    
    edges = [set(n.edges()) for n in (control, cand)]
    
    #intersection give edges in both networks
    sameedges = set.intersection(*edges)
    #get the unique edges in each network
    controluniqedges = set(control.edges())-sameedges
    canduniqedges = set(cand.edges())-sameedges
    
    samecol = lambda e: pydot.Edge(*e, color=colorsame)
    diffcol = lambda e: pydot.Edge(*e, color=controldiff, style='dashed')
    uniquecol = lambda e: pydot.Edge(*e, color=canddiff)
    [pdnet.add_edge(e) for e in map(samecol, sameedges)]
    [pdnet.add_edge(e) for e in map(diffcol, controluniqedges)]
    [pdnet.add_edge(e) for e in map(uniquecol, canduniqedges)]
    print "Same Edges: ",len(sameedges)
    print "Control Edges: ", len(controluniqedges)
    print "Cand Edges: ", len(canduniqedges)
    return pdnet
    