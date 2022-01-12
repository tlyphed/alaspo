
import random
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')



class RandomAtomRelaxOperator():

    def __init__(self, rate):
        assert 0 < rate < 1
        self.__lns_rate = rate

    def get_move_assumptions(self, incumbent):
        '''
        returns the assumptions for the next VLNS move i.e. which parts of the solution are not relaxed according to the given rate
        '''
        asm = []
       
        max_selection_sz = len(incumbent.model.shown)

        selection_sz = round(max_selection_sz * (1 - self.__lns_rate))

        asm = random.sample(incumbent.model.shown, selection_sz)

        logger.debug(f'atom operator relaxed {max_selection_sz - selection_sz} / {max_selection_sz} atoms.')

        return asm

    def name(self):
        return str(100 * self.__lns_rate) + '% random atoms'

class RandomConstantRelaxOperator():
    
    def __init__(self, rate):
        assert 0 < rate < 1
        self.__lns_rate = rate

    def get_move_assumptions(self, incumbent):
        '''
        returns the assumptions for the next VLNS move i.e. which parts of the solution are not relaxed according to the given rate
        '''
        constants = set()
        for s in incumbent.model.shown:
            constants = constants.union(s.arguments)
       
        relaxed_number = int(len(constants) * self.__lns_rate)
        relaxed_constants = set(random.sample(constants, relaxed_number))

        assumptions = [ s for s in incumbent.model.shown if relaxed_constants.isdisjoint(s.arguments) ]

        logger.debug(f'constant operator relaxed {len(incumbent.model.shown) - len(assumptions)} / {len(incumbent.model.shown)} atoms.')

        return assumptions

    def name(self):
        return str(100 * self.__lns_rate) + '% random constants'