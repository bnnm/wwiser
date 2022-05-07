from .generator.render import wnode_rtpc


class Tests(object):
    def __init__(self):
        pass
        
    def main(self):
        print("tests")
        
        GraphTests().start()
        pass

    def _info(self):
        #try:
            #import objgraph
            #objgraph.show_most_common_types()

            #from guppy import hpy; h=hpy()
            #h.heap()

            #from . import wmodel
            #import sys
            #print("NodeElement: %x" % sys.getsizeof(wmodel.NodeElement(None, 'test')))
            #getsizeof(wmodel.NodeElement()), getsizeof(Wrong())
        #except:
            #pass

        pass

class GraphTests(object):
    def __init__(self):
        self.tests = [
            GraphTest('ACB whispers - GP_MP_DISTANCE_CHASER_FROM_PLAYER', 40, 2, [
                    (0.0, 19.806190490722656, 9), 
                    (18.694889068603516, 19.806190490722656, 6), 
                    (25.472000122070312, -96.30000305175781, 9),
                    (32.0, -96.30000305175781, 9),
                    (50.0, -96.30000305175781, 9),
                ],
                [-1.0, 0.0, 10.0, 19.0, 20.0, 25.0, 30.0, 55.0]
            ),
            GraphTest('ACB track - GP_MP_DISTANCE_PLAYER_FROM_TARGET', 40, 2, [
                    (0.0, 50.86879348754883, 5), 
                    (4.351779937744141, 15.675174713134766, 7), 
                    (9.646302223205566, -0.47163546085357666, 4),
                    (50.0, -0.26096510887145996, 4),
                ],
                [-1.0, 0.0, 2.0, 5.0, 10.0, 40.0, 55.0]
            ),
            GraphTest('DMC5 nero - bgm_srank_param 375889460', 160, 2, [
                    (0.0, -1.0, 9),
                    (4.2288498878479, -1.0, 4),
                    (4.599999904632568, 0.0, 9),
                    (5.0, 0.0, 9),
                    (7.0, 0.0, 4),
                ],
                [-1.0, 1.0, 4.25, 4.60, 10.0]
            ),
            GraphTest('DMC5 nero - bgm_srank_param 525203653', 160, 2, [
                    (0.0, -1.0, 9),
                    (3.755729913711548, -1.0, 4),
                    (4.0, 0.0, 4),
                    (4.193260192871094, -0.12219105660915375, 4),
                    (4.515379905700684, -0.9930070042610168, 4),
                    (7.0, -1.0, 4),
                ],
                [-1.0, 1.0, 3.85, 4.05, 4.70, 6.0, 10.0]
            ),
            GraphTest('DMC5 nero - bgm_srank_param 385813821', 160, 2, [
                    (0.0, 0.0, 9),
                    (4.0, 0.0, 4),
                    (4.462500095367432, -0.1541711390018463, 4),
                    (4.599999904632568, -0.6837722063064575, 4),
                    (5.0, -1.0, 9),
                    (7.0, -1.0, 4),
                ],
                [-1.0, 1.0, 4.25, 4.50, 4.80, 10.0]
            ),
        ]

    def start(self):
        for t in self.tests:
            self._test(t)
        return

    def _test(self, t):
        graph = wnode_rtpc.NodeGraph(None, 0)
        graph.version = t.version
        graph.scaling = t.scaling

        for x, y, i in t.points:
            p = wnode_rtpc.NodeGraphPoint(None)
            p.x = x
            p.y = y
            p.i = i
            graph.points.append(p)

        print("- %s" % (t.name))
        for x in t.values:
            y = graph.get(x)            
            print(" x=%s, y=%s" % (x, y))
        print("")

class GraphTest(object):
    def __init__(self, name, version, scaling, points, values):
        self.name = name
        self.version = version
        self.scaling = scaling
        self.points = points
        self.values = values
