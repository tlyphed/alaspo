
import random
import config
import logging
logger = logging.getLogger('root')


class AbstractRelaxOperator():

    def __init__(self, rates, initial_rate=None):
        """
        initializes the operator with a non-empty set of relaxation rates and an optional initial rate
        """
        if len(rates) <= 0:
            raise ValueError('list of rates is empty')
        p = None
        for rate in rates:
            if not 0 <= rate <= 1:
                raise ValueError('rate is not between zero and one')
            if p == None:
                p = rate
            elif p >= rate:
                raise ValueError('rates have to strictly increase')
        self.__rates = rates

        self.__current_index = 0
        if initial_rate != None:
            if not initial_rate in self.__rates:
                raise ValueError('initial rate is not in list of all rates')

            self.__current_index = self.__rates.index(initial_rate)

        self._rate = self.__rates[self.__current_index]

    def get_move_assumptions(self, incumbent):
        """
        returns the assumptions for the next VLNS move i.e. which parts of the
        solution are not relaxed according to the given rate
        """
        pass

    def increase_size(self):
        """
        increases the relaxation rate to the next defined rate. 
        returns False if no increase is possible and True otherwise
        """
        if self.__current_index < len(self.__rates) - 1:
            self.__current_index += 1
            self._rate = self.__rates[self.__current_index]
        else:
            return False

        return True

    def decrease_size(self):
        """
        decreases the relaxation rate to the next defined rate. 
        returns False if no decrease is possible and True otherwise
        """
        if self.__current_index > 0:
            self.__current_index -= 1
            self._rate = self.__rates[self.__current_index]
        else:
            return False

        return True

    def name(self):
        """
        return a string identifier for the operator (used for logging and statistics)
        """
        pass

    def flatten(self):
        """
        returns a list of operators where each contains only one of the rates
        """
        operators = []

        for rate in self.__rates:
            operators += [ type(self)(rates=[rate]) ]

        return operators


class RandomAtomRelaxOperator(AbstractRelaxOperator):

    def __init__(self, rates, initial_rate=None):
        super().__init__(rates, initial_rate)

    def get_move_assumptions(self, incumbent):
        asm = []

        max_selection_sz = len(incumbent.model.shown)

        selection_sz = round(max_selection_sz * (1 - self._rate))

        asm = random.sample(incumbent.model.shown, selection_sz)

        logger.debug(
            f'atom operator relaxed {max_selection_sz - selection_sz} / {max_selection_sz} atoms.')

        return asm

    def name(self):
        return str(100 * self._rate) + '% random atoms'


class RandomConstantRelaxOperator(AbstractRelaxOperator):

    def __init__(self, rates, initial_rate=None):
        super().__init__(rates, initial_rate)

    def get_move_assumptions(self, incumbent):
        constants = set()
        for s in incumbent.model.shown:
            constants = constants.union(s.arguments)

        relaxed_number = int(len(constants) * self._rate)
        relaxed_constants = set(random.sample(constants, relaxed_number))

        assumptions = [
            s for s in incumbent.model.shown if relaxed_constants.isdisjoint(s.arguments)]

        logger.debug(f"constant operator relaxed "
                     f"{len(incumbent.model.shown) - len(assumptions)} / {len(incumbent.model.shown)} atoms.")

        return assumptions

    def name(self):
        return str(100 * self._rate) + '% random constants'


class DeclarativeRelaxOperator(AbstractRelaxOperator):

    def __init__(self, rates, initial_rate=None, name=None):
        super().__init__(rates, initial_rate)
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

        selection_sz = round(max_selection_sz * (1 - self._rate))

        selection = random.sample(select, selection_sz)
        for sel in selection:
            for atom, s in fix:
                if sel == s:
                    asm.append(atom)

        logger.debug(f"lns_select operator relaxed "
                     f"{selection_sz} / {max_selection_sz} atoms.")

        return asm

    def name(self):
        return f"lns_select with rate {self._rate}"


# RelaxOperator Factory

def get_operator(type, args):
    """
    returns a new relax operator of the given type with given args
    """
    rates = args['rates']
    initial_rate = None
    if 'initialRate' in args:
        initial_rate = args['initialRate']

    if type == 'randomAtoms':
        return RandomAtomRelaxOperator(rates, initial_rate=initial_rate)
    elif type == 'randomConstants':
        return RandomConstantRelaxOperator(rates, initial_rate=initial_rate)
    elif type == 'declarative':
        name = None
        if 'name' in args:
            name = args['name']

        return DeclarativeRelaxOperator(rates, initial_rate=initial_rate, name=name)
    else:
        raise ValueError('unknown relax operator "%s"' % type)