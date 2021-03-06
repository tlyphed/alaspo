
import random
import config
import logging
logger = logging.getLogger('root')


class AbstractRelaxOperator():

    def __init__(self, sizes):
        """
        initializes the operator with a non-empty set of relaxation sizes and an optional initial size. 
        the sizes are either all relative (between zero and one) or all absolute (integers bigger than zero)
        """
        if len(sizes) <= 0:
            raise ValueError('list of sizes is empty')

        absolute = None
        self._sizes = sorted(sizes)
        relative = True
        for size in sizes:
            if not (size > 0.0 and size < 1.0):
                relative = False
                break

        absolute = True
        for size in sizes:
            if not (size > 0 and type(size) == int):
                absolute = False
                break

        if not (absolute or relative):
            raise ValueError('sizes have to be all relative or all absolute!')

        self.__current_index = 0
       
        self._size = self._sizes[self.__current_index]
        self._absolute = absolute

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
        if self.__current_index < len(self._sizes) - 1:
            self.__current_index += 1
            self._size = self._sizes[self.__current_index]
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
            self._size = self._sizes[self.__current_index]
        else:
            return False

        return True

    def reset_size(self):
        """
        resets the size of the operator to the lowest value
        """
        self.__current_index = 0
        self._size = self._sizes[self.__current_index]


    def minimize_size(self):
        """
        decreases the relaxation rate to the next defined rate. 
        returns False if no decrease is possible and True otherwise
        """
        if self.__current_index > 0:
            self._size = self._sizes[0]
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

        for size in self._sizes:
            operators += [ type(self)(sizes=[size]) ]

        return operators

class RandomAtomRelaxOperator(AbstractRelaxOperator):

    def __init__(self, sizes):
        super().__init__(sizes)

    def get_move_assumptions(self, incumbent):
        asm = []

        max_selection_sz = len(incumbent.model.shown)

        if self._absolute:
            selection_sz = min(max_selection_sz, self._size)
            selection_sz = max_selection_sz - selection_sz
        else:
            selection_sz = round(max_selection_sz * (1 - self._size))

        asm = random.sample(incumbent.model.shown, selection_sz)

        logger.debug(
            f'atom operator relaxed {max_selection_sz - selection_sz} / {max_selection_sz} atoms.')

        return asm

    def name(self):
        return 'random atoms: ' + str(self._sizes)


class RandomConstantRelaxOperator(AbstractRelaxOperator):

    def __init__(self, sizes):
        super().__init__(sizes)

    def get_move_assumptions(self, incumbent):
        constants = set()
        for s in incumbent.model.shown:
            constants = constants.union(s.arguments)

        if self._absolute:
            relaxed_number = min(len(constants), self._size)
        else:
            relaxed_number = int(len(constants) * self._size)
        relaxed_constants = set(random.sample(constants, relaxed_number))

        assumptions = [
            s for s in incumbent.model.shown if relaxed_constants.isdisjoint(s.arguments)]

        logger.debug(f"constant operator relaxed "
                     f"{len(incumbent.model.shown) - len(assumptions)} / {len(incumbent.model.shown)} atoms.")

        return assumptions

    def name(self):
        return 'random constants: ' + str(self._sizes)

class DeclarativeRelaxOperator(AbstractRelaxOperator):

    def __init__(self, sizes, name=None):
        super().__init__(sizes)
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
        if max_selection_sz <= 0:
            raise ValueError('empty selection')

        if self._absolute:
            selection_sz = min(max_selection_sz, self._size)
            selection_sz = max_selection_sz - selection_sz
        else:
            selection_sz = round(max_selection_sz * (1 - self._size))

        selection = random.sample(select, selection_sz)
        for sel in selection:
            for atom, s in fix:
                if sel == s:
                    asm.append(atom)

        logger.debug(f"lns_select operator relaxed "
                     f"{max_selection_sz - selection_sz} / {max_selection_sz} atoms.")

        return asm

    def name(self):
        if self.__name != None:
            return 'lns_select "' + self.__name + '": ' + str(self._sizes)
        else:
            return 'lns_select: ' + str(self._sizes)

    def flatten(self):
        """
        returns a list of operators where each contains only one of the rates
        """
        operators = []

        for size in self._sizes:
            operators += [ type(self)(sizes=[size], name=self.__name) ]

        return operators

# RelaxOperator Factory

def get_operator(type, args):
    """
    returns a new relax operator of the given type with given args
    """
    sizes = args['sizes']

    if type == 'randomAtoms':
        return RandomAtomRelaxOperator(sizes)
    elif type == 'randomConstants':
        return RandomConstantRelaxOperator(sizes)
    elif type == 'declarative':
        name = None
        if 'name' in args:
            name = args['name']

        return DeclarativeRelaxOperator(sizes, name=name)
    else:
        raise ValueError('unknown relax operator "%s"' % type)