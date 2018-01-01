#!/usr/bin/python
"""
    Python implementation of the TODO.TXT Command Line Interface
    Original conception by: Gina Trapani (http://ginatrapani.org)
    License: GPL, http://www.gnu.org/copyleft/gpl.html
	More information and mailing list at http://todotxt.com
"""

import sys
import os
import shutil

import logging
import argparse
import re
import inspect
import ConfigParser

from datetime import date


###############################################################################

usage_doc = "%(prog)s [options] action [task_number] [task_description]"

longhelp_doc = """
Built-in Actions:

  add "THING I NEED TO DO +project @context"
  a "THING I NEED TO DO +project @context"
    Adds THINK I NEED TO DO to your todo.txt file on its own line.
    Project and context notation optional. 

  archive
    Move all ITEMs marked as done (preceeded with X) from the todo.txt file to
    a done.txt file. Done ITEMS will no longer appear in the todo list when 
    displayed.

  depri ITEM#[, ITEM#, ITEM#, ...]
  dp ITEM#[, ITEM#, ITEM#, ...]
    Deprioritizes (removes the priority) from the task(s) on line ITEM# in 
    todo.txt.

  do ITEM#[, ITEM#, ITEM#, ...]
    Marks task(s) on line ITEM# as done in todo.txt

  del ITEM# 
  rm ITEM# 
    Deletes the task on line ITEM# in todo.txt.
 
  help 
    Display this help message. Use option -h/--help for Usage, Arguments and
    short help listing of available aciion commands.

  list [TERM...]
  ls [TERM...]
    Displays all tasks that contain TERM(s) sorted by priority with line 
    numbers. Each task must match all TERM(s) (logical AND) 
    If no TERM specified, lists entire todo.txt

  pri ITEM# PRIORITY
  p ITEM# PRIORITY
    Adds PRIORITY to task on line ITEM#.  If the task is already
    prioritized, replaces current priority with new PRIORITY.
    PRIORITY must be a letter between A and Z.

  shorthelp
    List the one-line usage of all built-in actions."""
    
shorthelp_doc = """
Actions:
  add|a "THING I NEED TO DO +project @context"
  archive
  del|rm ITEM# [TERM]
  depri|dp ITEM#[, ITEM#, ITEM#, ...]
  do ITEM#[, ITEM#, ITEM#, ...]
  help
  list|ls [TERM...]
  pri|p ITEM# PRIORITY
  shorthelp """

description_doc = """
For detailed instructions on 'action' commands, use: 
  %(prog)s help 
"""

default_cfg_head = """[default]

; Path to the 'todo' directory containing todo.txt and done.txt files. 
todo_dir: """

default_cfg_tail = """
; Colour mode when displaying task list. Command line options over-ride this
; -c for colour mode or -p for plain mode. Values - 'true' or 'false' 
colour_mode = true

; Default action to perform if todo.py is called with no action command
default_action = list

; ANSI colour codes to be used - overrides the defaults used.
; WARNING: incorrect colour codes can make output unreadable.
;BLACK          = [0;30m
;RED            = [0;31m
;GREEN          = [0;32m
;BROWN          = [0;33m
;BLUE           = [0;34m
;PURPLE         = [0;35m
;CYAN           = [0;36m
;LIGHT_GREY     = [0;37m
;DARK_GREY      = [1;30m
;LIGHT_RED      = [1;31m
;LIGHT_GREEN    = [1;32m
;YELLOW         = [1;33m
;LIGHT_BLUE     = [1;34m
;LIGHT_PURPLE   = [1;35m
;LIGHT_CYAN     = [1;36m
;WHITE          = [1;37m

; Colours used when displaying the task list
task_priority_a = YELLOW
task_priority_b = LIGHT_GREEN
task_priority_c = LIGHT_BLUE
task_priority_x = WHITE
task_done       = DARK_GREY
task_normal     = LIGHT_GREY
; Project keywords are prepended with '+' e.g. +GalacticaRepairs
task_project    = RED
; Context keywords are prepended with '@' .e.g. @CylonHomeWorld
task_context    = LIGHT_CYAN
"""

###############################################################################
#  Default Ansi Colours

ansi_colour = {
        'BLACK':        '\033[0;30m',
        'RED':          '\033[0;31m',
        'GREEN':        '\033[0;32m',
        'BROWN':        '\033[0;33m',
        'BLUE':         '\033[0;34m',
        'PURPLE':       '\033[0;35m',
        'CYAN':         '\033[0;36m',
        'LIGHT_GREY':   '\033[0;37m',
        'DARK_GREY':    '\033[1;30m',
        'LIGHT_RED':    '\033[1;31m',
        'LIGHT_GREEN':  '\033[1;32m',
        'YELLOW':       '\033[1;33m',
        'LIGHT_BLUE':   '\033[1;34m',
        'LIGHT_PURPLE': '\033[1;35m',
        'LIGHT_CYAN':   '\033[1;36m',
        'WHITE':        '\033[1;37m',
        }

PRI_X = ansi_colour['WHITE']
priority_colour = {
        'A': ansi_colour['YELLOW'],
        'B': ansi_colour['LIGHT_GREEN'],
        'C': ansi_colour['LIGHT_BLUE']
        }

PROJECT = ansi_colour['LIGHT_RED']
CONTEXT = ansi_colour['LIGHT_CYAN']
DONE    = ansi_colour['DARK_GREY']
NORMAL  = ansi_colour['LIGHT_GREY']
DEFAULT = '\033[0m'

###############################################################################
# Regexs

# ISO 8601 format date strings
# date_re = re.compile( "(\d{4}-\d{2}-\d{2})\s" )

priority_re = re.compile( "^\(([A-Z])\)" )

project_re = re.compile( "(\W\+\w+)" )

context_re = re.compile( "(\W\@\w+)" )

done_re = re.compile( "^x\s" )

line_no_re = re.compile( "(^\d+\s+)(\S.*)" )


###############################################################################

# define debug and error logging.
debug = logging.debug
    
def print_todo( text ):
    print "--\nTODO:\t%s" % text

def error( err_msg ):
    "Displays debugging error message and exits"
    callerframerecord = inspect.stack()[ 1 ]
    frame = callerframerecord[ 0 ]
    info = inspect.getframeinfo( frame )

    sys.exit("ERROR : %-30s : line %d\n\t%s" % ( 
        info.function, info.lineno, err_msg ) 
        )

def todo_error( err_msg ):
    "Displays runtime error message and exits"
    sys.exit( "--\nTODO:\tERROR: %s" % err_msg )

def add_line_numbers( lines ):
    "Add a line number to a list of strings"
    line_no = 1
    new_lines = []
    for line in lines:
        line = " ".join( [ "%-3d" % line_no, line ] )
        new_lines.append( line )
        line_no += 1
    return new_lines

def remove_line_no( line ):
    "Remove the line number from the start of the string"
    res = line_no_re.match( line )
    if res:
        return res.groups()[1]
    else: 
        return line

def remove_line_numbers( lines ):
    return map( remove_line_no, lines )
    
def build_term_filter( words ):
    "Build and return a regexe AND filter on the word list imported"
    debug( "Words to filter list on" )
    debug( words )

    term_f = []
    for term in words:
        term_f.append( "(?=.*\W%s\\b)" % re.escape( term ) )

    return "".join( term_f )

def create_default_cfg_file( cfg_filename ):
    """
    Creates the default config file and sets the todo directory as being
    under the systems home directory
    """

    home_dir = os.path.abspath( os.path.expanduser("~") )
    todo_dir = os.path.join( home_dir, "todo" )

    with open( cfg_filename, "w" ) as fh:
        fh.write( default_cfg_head )
        fh.write( "%s\n" % todo_dir )
        fh.write( default_cfg_tail )
        fh.close()
        print "\t%s created." % cfg_filename

def process_cfg_file( cfg_filename ):
    """
    Process the TODO cfg file. Command line args override cfg file.
    This is where colour codes are updated.
    """

    global ansi_colour
    global priority_colour
    global PRI_X
    global DONE
    global NORMAL
    global PRstr_to_intOJECT
    global CONTEXT
    
    cfg_parser = ConfigParser.SafeConfigParser()
    cfg_parser.read( cfg_filename )
    
    # get the config values and convert to a dictionary.
    cfg = {}
    for (name, value) in cfg_parser.items('default'):
        cfg[ name ] = value

    debug("cfg")
    debug( cfg )

    # Validate the todo dir
    if not "todo_dir" in cfg:
        todo_error( "No \"todo_dir\" specified in %s" % cfg_filename )

    # Process colour setting options
    for key in ansi_colour.keys():
        if key.lower() in cfg.keys():
            ansi_colour[ key ] = "".join( [ '\033', cfg[ key.lower() ] ] )

    # Process task priority colours
    for key in priority_colour.keys(): 
        if key.lower() in cfg.keys() and cfg[key.lower()] in ansi_colour.keys():
            priority_colour[ key ] = ansi_colour[ cfg[ key.lower() ] ]

    if "x" in cfg.keys() and cfg[ "x" ] in ansi_colour.keys():
        PRI_X = ansi_colour[ cfg[ "x" ] ]

    if "done" in cfg.keys() and cfg[ "done" ] in ansi_colour.keys():
        DONE = ansi_colour[ cfg[ "done" ] ]

    if "normal" in cfg.keys() and cfg[ "normal" ] in ansi_colour.keys():
        NORMAL = ansi_colour[ cfg[ "normal" ] ]

    if "project" in cfg.keys() and cfg[ "project" ] in ansi_colour.keys():
        PROJECT = ansi_colour[ cfg[ "project" ] ]

    if "context" in cfg.keys() and cfg[ "context" ] in ansi_colour.keys():
        CONTEXT = ansi_colour[ cfg[ "context" ] ]

    return cfg

def str_to_int( value ):
    "Converts string to int and indicates error if not int"
    try:
        number = int( value ) 
    except ValueError:
        todo_error( "Non-numeric used for ITEM# \"%s\"." % value )

    return number


###############################################################################
#
# todo Class
#
###############################################################################

class todo( object ):
    "Class to manage todo actions"

    def __init__( self, todo_dir, **kwargs ):
        "Load the todo list"
        self.todo_file = os.path.join( todo_dir, "todo.txt" )
        self.done_file = os.path.join( todo_dir, "done.txt" )
        
        if os.path.exists( self.todo_file ):
            with open( self.todo_file ) as fh:
                self.__lines = fh.readlines()
                fh.close()
        else:
            self.__lines = []

        self.__list_size = len( self.__lines )

        # remove Carriage returns.
        self.__lines = [line.strip() for line in self.__lines]

        self.__kwargs = kwargs

        self.__dispatcher = {
                "a":            self.__add,
                "add":          self.__add,
                "archive":      self.__archive,
                "del":          self.__delete,
                "depri":        self.__deprioritise,
                "do":           self.__do,
                "dp":           self.__deprioritise,
                "help":         self.__help,
                "ls":           self.__list,
                "list":         self.__list,
                "pri":          self.__priority,
                "p":            self.__priority,
                "rm":           self.__delete,
                "shorthelp":    self.__shorthelp
                }

    def command( self, action ):
        "Process command"
        debug( action )

        if not len(action):
            error( "Empty action list passed!" )

        cmd = self.__dispatcher.get( action[0] )
        if cmd:
            return cmd( action[1:] ) 
        else:
            todo_error( "Unknown action: %s" % action[0] )

    def __add(self, args):
        "Add a new task to the list"
        
        # prepend the date to the start of the task
        args.insert( 0, "%s" % date.today().strftime("%Y-%m-%d") )

        # Join everything together - this works if the task was in
        # quotes or was a list of words as args
        task = " ".join( args )

        self.__lines.append( task )
    
        self.__write_todo()

        print_todo( "Added new task\n\t%s" % self.__colour( task)  )
        print "--"
        self.__list()

    def __archive(self, args):
        "Takes all completed tasks and archives them in the 'done.txt' file"

        completed = []
        for task in self.__lines:
            if done_re.match( task ):
                completed.append(task)

        # Can't archive if not tasks are completed
        if not completed:
            todo_error("No tasks marked done.")

        # just in case.
        completed.sort()

        # Now remove completed tasks from the main task list
        for task in completed:
            self.__lines.remove( task )

        # Back up the original file before writing a new one, if it exists.
        # Also determines wethe the file mode is 'append' or 'write'.
        if os.path.exists( self.done_file ):
            (path_name, ext) = os.path.splitext( self.done_file )
            backup_filename = ".".join( [ path_name, "bak"] )
            shutil.copyfile( self.done_file, backup_filename )
            mode = "a"
        else:
            mode = "w"

        with open( self.done_file, mode ) as fh:
            for task in completed:
                fh.write( "%s\n" % task )
            fh.close()

        self.__write_todo()

        print_todo("The following tasks have been archived:")
        for task in completed:
            print "\t%s" % self.__colour( task )
        print "--"
        self.__list()

    def __colour( self, text ):
        "Colour the text using ANSI colours for output"

        # Don't do it unless colour option is set.
        if not self.__kwargs["colour"]:
            return text

        colour = NORMAL

        # split the line# from the task
        res = line_no_re.match( text )
        if res:
            line_no, text = res.groups()
        else:
            line_no = ""

        # if the text has a priority, set the colour accordingly
        priority = priority_re.match( text )
        if priority:
            # Get the colour based on priority A, B, C or default X
            colour = priority_colour.get( priority.groups()[0], PRI_X ) 
        else:
            # Check if this task has been done
            done = done_re.match( text )
            if done:
                colour = DONE
         
        # Add the colour coding to the start of the text
        text = "".join( [ line_no, colour, text, DEFAULT ] )

        # always colour code Project and Context
        text = project_re.sub(
                "%s\\1%s" % (PROJECT, colour),
                text 
                )

        text = context_re.sub(
                "%s\\1%s" % (CONTEXT, colour),
                text
                )

        return text

    def __delete(self, args):
        "Delete task(s) from the to do list"
        items = self.__items_from_args( args )

        print "--\nTODO:",
    
        # reverse sort the items so that tasks are deleted from the 
        # bottom up and avoid an IndexError.
        items.reverse()

        for item in items:
            task = self.__lines.pop( item )
            print "\tDeleted task: %s" % self.__colour( task )

        self.__write_todo()
        print "--"
        self.__list()

    def __deprioritise(self, args):
        "Remove the prioritisation from a task, if it has one."
        items = self.__items_from_args( args )

        print "--\nTODO:",

        for item in items:
            task = self.__lines[ item ]

            # Check the task hasn't already been completed
            if done_re.match( task ):
                print"\tERROR: Task completed: %s" % self.__colour( task )
                continue

            res = priority_re.match( task )
            if res:
                task = priority_re.sub( "", task )
                
                # Get rid of extra whitespace too.
                task = task.strip()

                print "\tDeprioritised: %s" % self.__colour( task )

            else:
                print "\tERROR: No priority: %s" % self.__colour( task )
                continue

            self.__lines[ item ] = task

        self.__write_todo()
        print "--"
        self.__list()

    def __do(self, args):
        "Mark a task(s) as done and add a completion date"

        items = self.__items_from_args( args )

        print "--\nTODO:",

        for item in items:
            task = self.__lines[ item ]

            # Check the task hasn't already been marked done.
            if not done_re.match( task ):
                self.__lines[ item ] = " ".join( [
                    "x",
                    date.today().strftime("%Y-%m-%d"),
                    task
                    ] )

            print "\tMarked done: %s" % self.__colour( task )

        self.__write_todo()
        print "--"
        self.__list()

    def __items_from_args( self, args ):
        "Converts a list of arg ITEMS# into a list of validated ints"

        # Strip any commas from the args
        args = [ arg.replace( ",","" ) for arg in args ]

        # Convert args to integers 
        items = [ str_to_int( arg ) for arg in args ]

        # Range check items (decrements by 1 at thes same time)
        items = [ self.__range_check( item ) for item in items ]

        return items

    def __list(self, args=None):
        """List tasks
        NEVER changes or writes the the todo file.
        """
        self.__lines = add_line_numbers( self.__lines )

        # Sort list alphabetically, ignoring line number
        self.__lines.sort( key=remove_line_no )

        if args:
            terms_regex = build_term_filter( args )
            debug( terms_regex )
            self.__lines = [
                    line for line in self.__lines if \
                    re.search( terms_regex, line) 
                    ]

        for line in self.__lines:
            print self.__colour( line )

        print_todo ("%s of %s tasks" % ( 
            len( self.__lines ), self.__list_size )
            )
 
    def __help(self, args):
        "Display help" 
        print longhelp_doc

    def __priority(self, args):
        """
        Set the priority of a task.
        If it already has a piority setting replace it.
        If it's done - ignore with error message
        """

        # Validate the arguments
        if len(args) != 2:
            todo_error( 
                    "\"pri\" action requires ITEM# and PRIORITY arguments." 
                    )
        # First arg is the ITEM#
        item = str_to_int( args[0] )
        item = self.__range_check( item )

        priority = args[1]
        # Second arg is the priority
        if not re.match( "^[A-Z]$", priority ):
            todo_error( "PRIORITY must be A to Z, not \"%s\"" % priority )
    
        task = self.__lines[ item ]

        # Check the task hasn't already been done.
        if done_re.match( task ):
            todo_error( 
                    "Task is completed\n\t%s" % self.__colour( task )
                    )

        # If the task already has a prority, change it
        res = priority_re.match( task )
        if res:
            task = priority_re.sub( "(%s)" % priority, task )
        else:
            task = " ".join( [ "(%s)" % priority, task ] )

        self.__lines[ item ] = task
        self.__write_todo()

        print_todo( "Task priority set.\n\t%s" % self.__colour( task ) )
        print "--"
        self.__list()

    def __range_check( self, item ):
        "Check that this item is within the task list range"

        if item < 1 or item > self.__list_size:
            todo_error( "%d is outside todo list range." % item )

        # Decrement item so that it can be used as an index to self.__lines.
        return item - 1

    def __shorthelp(self, args):
        "Display short help"
        print shorthelp_doc

    def __write_todo(self):
        "Writes the todo file. The tasks are sorted before the file is written"

        # Back up the original file before writing a new one, if it exists
        if os.path.exists( self.todo_file ):
            (path_name, ext) = os.path.splitext( self.todo_file )
            backup_filename = ".".join( [ path_name, "bak"] )
            shutil.copyfile( self.todo_file, backup_filename )

        self.__lines.sort()

        with open( self.todo_file, "w" ) as fh:
            for line in self.__lines:
                fh.write( "%s\n" % line )
            fh.close() 


###############################################################################
#
# Main
#
###############################################################################

if __name__ == "__main__":

    # Logging - by default, only output errors
    format = "%(levelname)s : %(funcName)-30s : line %(lineno)d\n\t%(message)s\n"
    logging.basicConfig(format=format)
    logging.getLogger().setLevel(logging.ERROR)

    # Command line options and help
    parser = argparse.ArgumentParser( 
            usage           = usage_doc,
            formatter_class = argparse.RawDescriptionHelpFormatter,
            description     = description_doc,
            epilog          = shorthelp_doc
            )

    colour_group = parser.add_mutually_exclusive_group()

    colour_group.add_argument(
            '-c', '--colour', action = 'store_true',
            help = 'Colour mode. Cannot be used with -p --plain.'
            )
    
    colour_group.add_argument(
            '-p', '--plain', action = 'store_true',
            help = 'plain mode. Cannot be used with -c --colour.'
            )

    parser.add_argument(
            '-v', '--verbose', action = 'store_true', 
            help = 'Output extra debug information.' 
            )

    parser.add_argument(
            'action', nargs='*',
            help = 'Action to be performed, use "help" action for list'
            )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel( logging.DEBUG ) 

    debug( "Logging activated." ) 
    debug( args ) 

    # Get the cfg file name from the script file name in argv[0]
    cfg_filename = os.path.splitext( sys.argv[ 0 ] )[ 0 ] + '.cfg'   
    cfg_filename = os.path.abspath( cfg_filename )

    # If the config file does not exist, offer to create it. Either, way
    # quit execution.
    if not os.path.exists( cfg_filename ):
        print_todo( "%s config file does not exist." % cfg_filename )
        answer = raw_input( "\tCreate a default config file [y/n]? " )
        if "y" in answer.lower()[0]:
            create_default_cfg_file( cfg_filename )
        else:
            todo_error("No config file")

    cfg = process_cfg_file( cfg_filename )

    # Does the todo directory exist?
    if not os.path.exists( cfg["todo_dir"] ):
        print_todo( "%s does not exist" % cfg[ "todo_dir" ] )
        answer = raw_input( "\tCreate it [y/n]? " )
        if "y" in answer.lower()[0]:
            os.makedirs( cfg["todo_dir"] )
        else:
            todo_error("todo directory does not exist")

    # Should it use colour in the display
    use_colour = args.colour or "true" in cfg["colour_mode"].lower()
    if args.plain: 
        use_colour = False

    if use_colour:
        try:
            import colorama
            colorama.init()
        except ImportError:
            print "TODO:\tWARNING: \'colorama\' package missing"
            print "\tInstall from https://pypi.python.org/pypi/colorama"
            print "\tor set plain mode option -p"
            use_colour = False

    # Load the todo list into an object
    td = todo( 
            cfg["todo_dir"], 
            colour = use_colour
            )

    # arg is always chosen over cfg but if arg.action is None, then 
    # default_action is used, unless that is none too!
    action = [ "help" ]
    if args.action:
        action = args.action
    elif cfg.get("default_action"):
        action = [ cfg.get("default_action") ]

    td.command( action )
