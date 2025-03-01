#!/usr/bin/env python3
#
# zabbix_utils is needed, see https://github.com/zabbix/python-zabbix-utils
#
# Pillow is also needed, see https://github.com/python-pillow/Pillow
#
#
import argparse
import configparser
import os
import os.path
import distutils.util
import requests
import time
import sys
from io import StringIO
#from PIL import Image
from zabbix_utils import ZabbixAPI

# define config helper function

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print(("exception on %s!" % option))
            dict1[option] = None
    return dict1


# set default vars
defconf = os.getenv("HOME") + "/.zabbix-api.conf"
username = ""
password = ""
api = ""
noverify = ""

# Define commandline arguments
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='Get item values from Zabbix history', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zabbix-api.conf) that contains at least the [Zabbix API] section and any of the other parameters:

 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
parser.add_argument(
    'itemid', help='The item that we are going to query the history from')
parser.add_argument('-u', '--username',
                    help='User for the Zabbix api and frontend')
parser.add_argument('-p', '--password', help='Password for the Zabbix user')
parser.add_argument('-a', '--api', help='Zabbix URL')
parser.add_argument(
    '--no-verify', help='Disables certificate validation when using a secure connection', action='store_true')
parser.add_argument(
    '-c', '--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument('-s', '--starttime', type=int,
                    help='Starting time for the graph in seconds from Unix Epoch')
parser.add_argument('-t', '--timeperiod', type=int, default=3600,
                    help='Timeperiod for the graph in seconds (defaults to 3600)')
parser.add_argument('-C', '--count', type=int,
                    help='Number of values returned')
parser.add_argument('-e', '--extended',
                    help='Returns timestamps (Unixtime in nanoseconds), units and values seperated by a ":"', action='store_true')
args = parser.parse_args()

# load config module
Config = configparser.ConfigParser()
Config

# if configuration argument is set, test the config file
if args.config:
    if os.path.isfile(args.config) and os.access(args.config, os.R_OK):
        Config.read(args.config)

# if not set, try default config file
else:
    if os.path.isfile(defconf) and os.access(defconf, os.R_OK):
        Config.read(defconf)

# try to load available settings from config file
try:
    username = ConfigSectionMap("Zabbix API")['username']
    password = ConfigSectionMap("Zabbix API")['password']
    api = ConfigSectionMap("Zabbix API")['api']
    noverify = bool(distutils.util.strtobool(
        ConfigSectionMap("Zabbix API")["no_verify"]))
except:
    pass

# override settings if they are provided as arguments
if args.username:
    username = args.username

if args.password:
    password = args.password

if args.api:
    api = args.api

if args.no_verify:
    noverify = args.no_verify

# test for needed params
if not username:
    sys.exit("Error: API User not set")

if not password:
    sys.exit("Error: API Password not set")

if not api:
    sys.exit("Error: API URL is not set")

if noverify == True:
    verify = False
else:
    verify = True

# Create instance, get url, login and password from user config file
zapi = ZabbixAPI(url=api,user=username,password=password,validate_certs=verify)

##################################
# Start actual API logic
##################################

# set the hostname we are looking for
itemid = args.itemid

# Find graph from API
item = zapi.item.get(output="extend", itemids=itemid)

if item:

    # Get the right valuetype for the item
    # 0 - float
    # 1 - character
    # 2 - log
    # 3 - numeric unsigned
    # 4 - text
    valtype = item[0]['value_type']

    # Get units for the item
    unit = item[0]['units']

    # Set time period
    period = args.timeperiod

    # set the starting time for the item
    if args.starttime:
        stime = int(args.starttime)
    else:
        stime = int(time.time()-period)

    etime = int(stime+period)

    if args.count:
        # count to use for limiit
        count = int(args.count)
        itemhist = zapi.history.get(itemids=itemid, history=valtype,
                                    time_from=stime, time_till=etime, output='extend', limit=count)
    else:
        itemhist = zapi.history.get(
            itemids=itemid, history=valtype, time_from=stime, time_till=etime, output='extend')
    if itemhist:
        if args.extended:
            for record in itemhist:
                print((format(record['clock'])+"."+format(record['ns']
                                                         )+":"+format(unit)+":"+format(record["value"])))
        else:
            for record in itemhist:
                print((format(record["value"])))
    else:
        print("No values returned for itemid " + itemid)
else:
        print("Could not find itemid " + itemid)

zapi.logout()
# And we're done...
