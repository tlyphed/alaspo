
import logging

SELECT_PRED = "_lns_select"
FIX_PRED = "_lns_fix"

def setup_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


# global data needed for interactive mode
INTERACTIVE = False         # True if interactive mode is used
BEST_SOLUTION = None        # best solution found so far
SEARCH_OPS = None           # list of registered search operators
RELAX_OPS = None            # list of registered neighbourhood operators
CURRENT_SEARCH_OP = None    # currently used search operator
CURRENT_RELAX_OP = None     # currently used neighbourhood operator




