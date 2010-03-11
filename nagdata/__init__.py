"""
Python interface to Nagios object and status files. Parses configuration files,
status.dat (status file) and represents information as collection of objects
with corresponding obj_type and attributes. Objects may also be saved.

nagdata package contains following modules:

nagdata        -- main module, interface to nagios object and status files,
                  also provides class with simpler api
exceptions     -- exceptions used by nagdata
parser         -- parsers of nagios configuration and status files (parses list
                  of lines)
cparser_fmt    -- parse file and keep format
cparser_fast   -- just parse file and don't save format
nagfile        -- links together files and parsers, so we can parse files
collection     -- collection of Nagios objects
factory        -- factories to produce different Nagios objects
model          -- Nagios objects (hoststatus, servicestatus, service definition,
                  etc)
fields         -- Types of Nagios object attributes
fmt            -- "Imaginary" format object helping to keep nagios file format
                  and structure

"""


