
import random
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-15s [%(process)d:%(processName)s] %(module)s:%(lineno)d %(levelname)s: %(message)s')


class AbstractRelaxOperator():

    def _get_move_assumptions(self, instance, incumbent):
        '''
        returns the assumptions for the next VLNS move i.e. which parts of the solution are fixed
        '''
        pass


class RandomAtomRelaxOperator(AbstractRelaxOperator):

    def __init__(self, rate):
        assert 0 < rate < 1
        self.__lns_rate = rate

    def _get_move_assumptions(self, instance, incumbent):
        '''
        returns the assumptions for the next VLNS move i.e. which parts of the solution are not relaxed according to the given rate
        '''
        asm = []
       
        max_selection_sz = len(incumbent.atoms)

        selection_sz = round(max_selection_sz * (1 - self.__lns_rate))

        asm = random.sample(incumbent.atoms, selection_sz)

        logger.debug(f'neighbourhood: {selection_sz} / {max_selection_sz} elements = {len(asm)} atoms.')

        return asm