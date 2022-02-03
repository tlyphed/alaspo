
import random
import config
import logging
logger = logging.getLogger('root')


class RandomAtomRelaxOperator:

    def __init__(self, rate):
        assert 0 <= rate <= 1
        self.__lns_rate = rate

    def get_move_assumptions(self, incumbent):
        """
        returns the assumptions for the next VLNS move i.e. which parts of the
        solution are not relaxed according to the given rate
        """
        asm = []
       
        max_selection_sz = len(incumbent.model.shown)

        selection_sz = round(max_selection_sz * (1 - self.__lns_rate))

        asm = random.sample(incumbent.model.shown, selection_sz)

        logger.debug(f'atom operator relaxed {max_selection_sz - selection_sz} / {max_selection_sz} atoms.')

        return asm

    def name(self):
        return str(100 * self.__lns_rate) + '% random atoms'


class RandomConstantRelaxOperator:
    
    def __init__(self, rate):
        assert 0 <= rate <= 1
        self.__lns_rate = rate

    def get_move_assumptions(self, incumbent):
        """
        returns the assumptions for the next VLNS move i.e. which parts of the solution
        are not relaxed according to the given rate
        """
        constants = set()
        for s in incumbent.model.shown:
            constants = constants.union(s.arguments)
       
        relaxed_number = int(len(constants) * self.__lns_rate)
        relaxed_constants = set(random.sample(constants, relaxed_number))

        assumptions = [s for s in incumbent.model.shown if relaxed_constants.isdisjoint(s.arguments)]

        logger.debug(f"constant operator relaxed "
                     f"{len(incumbent.model.shown) - len(assumptions)} / {len(incumbent.model.shown)} atoms.")

        return assumptions

    def name(self):
        return str(100 * self.__lns_rate) + '% random constants'


class DeclarativeRelaxOperator:

    def __init__(self, rate, size, name=None):

        if size is None:
            assert 0 <= rate <= 1

        self.__lns_size = size
        self.__lns_rate = rate
        self.__name = name

    def get_move_assumptions(self, incumbent):
        """
        returns the assumptions for the next VLNS move i.e. which parts of the
        solution are not relaxed according to the given rate
        """
        asm = []

        select = []
        fix = []

        for s in incumbent.model.symbols:

            if self.__name is None:
                if s.match(config.SELECT_PRED, 1):
                    select.append(s.arguments[0])

                elif s.match(config.FIX_PRED, 2):
                    fix.append((s.arguments[0], s.arguments[1]))

            else:
                if s.match(config.SELECT_PRED, 2) and s.arguments[0].name == self.__name:
                    select.append(s.arguments[1])

                elif s.match(config.FIX_PRED, 3) and s.arguments[0].name == self.__name:
                    fix.append((s.arguments[1], s.arguments[2]))

        max_selection_sz = len(select)
        assert max_selection_sz > 0

        if self.__lns_size is None:
            selection_sz = round(max_selection_sz * self.__lns_rate)
        else:
            if self.__lns_size > max_selection_sz:
                selection_sz = max_selection_sz
            elif 0 < self.__lns_size <= max_selection_sz:
                selection_sz = self.__lns_size
            elif -max_selection_sz <= self.__lns_size < 0:
                selection_sz = max_selection_sz - abs(self.__lns_size)
            else:
                selection_sz = 0

        selection = random.sample(select, selection_sz)
        for sel in selection:
            for atom, s in fix:
                if sel == s:
                    asm.append(atom)

        logger.debug(f"neighbourhood: {selection_sz} / {max_selection_sz} elements = {len(asm)} atom.")

        return asm

    def name(self):
        return f"lns_select with rate {self.__lns_rate} and size {self.__lns_size}"
