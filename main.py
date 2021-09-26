import sys
from draw import *

start_arg = sys.argv[1]
try:
    end_arg = sys.argv[2]
except IndexError:
    end_arg = None
    
main(start_arg, end_arg)