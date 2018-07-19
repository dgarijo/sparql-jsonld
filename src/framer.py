from rdflib.term import Variable, Literal, URIRef
from rdflib.plugins.sparql.sparql import CompValue
from pyparsing import ParseResults
from rdflib.plugins.sparql.parserutils import plist


class Framer(object):
    def __init__(self, context):
        self.current_naming = 1
        self.context = context
        self.prefix = {}
        self.exist_triples = {}

    def frame(self, tree, frame):

        temp = tree[1]['projection'][0]
        parent = temp['var'] if 'var' in temp else temp['evar']

        self.prefix = self.prefix2dict(tree[0])
        self.exist_triples = self.where2triples(tree[1]['where']['part'])
        # print(self.exist_triples)
        # print(frame)

        triples = []
        extra = []

        # convert the frame to triples in the same structure with parsed query
        self.frame2triple(frame, parent, triples, extra)
        # print(extra)
        # print(triples)

        # generate the ConstructQuery CompValue
        new_query = CompValue(name='ConstructQuery')

        new_template = plist([ParseResults(x) for x in triples])
        new_query['template'] = new_template

        for k, v in tree[-1].items():
            if k not in ['projection', 'modifier']:
                if k == 'where' and 'part' in v:
                    v['part'].append(
                        CompValue(
                            'OptionalGraphPattern',
                            graph=CompValue('TriplesBlock',
                                            triples=plist([ParseResults(triples[x]) for x in extra]))))
                    # v['part'].append(CompValue('TriplesBlock',
                    #                            triples=plist([ParseResults(triples[x]) for x in extra])))
                new_query[k] = v

        return ParseResults([tree[0], new_query])

    def frame2triple(self, root, parent, triples, extra):
        for k, v in root.items():
            p = self.to_node(k)
            if isinstance(v, str):
                o = self.to_node(v)
            else:
                if (parent.toPython(), k) in self.exist_triples:
                    o = Variable(self.exist_triples[(parent.n3(), k)])
                else:
                    o = Variable('var%d' % self.current_naming)
                    self.current_naming += 1
                    extra.append(len(triples))
            triples.append([parent, p, o])
            if isinstance(v, dict) and len(v):
                self.frame2triple(v, o, triples, extra)

    def to_node(self, value: str):
        if value in self.context and '@id' in self.context[value]:
            full = self.context[value]['@id']
            local_name = full.split('/')[-1]
            pre = full[:-len(local_name)]
            if pre in self.prefix:
               return CompValue(name='pname', prefix=self.prefix[pre], localname=local_name)
            return URIRef(self.context[value]['@id'])
        else:
            split = value.split(':')
            if len(split) == 2:
                return CompValue(name='pname', prefix=split[0], localname=split[1])
            # TODO: rdf:type? @type ?
            if value.startswith('@'):
                return CompValue(name='pname', prefix='rdf', localname=value[1:])
            return Literal(value)

    @staticmethod
    def where2triples(triple_blocks):
        from src.stringify import ele2str
        ret = {}
        for block in triple_blocks:
            if isinstance(block, CompValue) and block.name == 'TriplesBlock' and 'triples' in block:
                for tri in block['triples']:
                    s, p, o = [ele2str(x).split(':')[-1] for x in tri]
                    # p = '@type' if p == 'type' else p
                    ret[(s, p)] = o
        return ret


    @staticmethod
    def prefix2dict(tree_prefix):
        try:
            ret = {}
            for pre in tree_prefix:
                if isinstance(pre, CompValue) and pre.name == 'PrefixDecl':
                    ret[pre['iri'].toPython()] = pre['prefix'] if 'prefix' in pre else ''
            return ret
        except Exception as e:
            print(e)
            return {}




