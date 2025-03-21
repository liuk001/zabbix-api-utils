#!/usr/bin/env python3
#
# zabbix_utils is needed, see https://github.com/zabbix/python-zabbix-utils
#
import argparse
import configparser
import os
import os.path
import sys
import distutils.util
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
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='Tries to find a list of hosts in Zabbix matching a search string.', epilog="""
This program can use .ini style configuration files to retrieve the needed API connection information.
To use this type of storage, create a conf file (the default is $HOME/.zabbix-api.conf) that contains at least the [Zabbix API] section and any of the other parameters:

 [Zabbix API]
 username=johndoe
 password=verysecretpassword
 api=https://zabbix.mycompany.com/path/to/zabbix/frontend/
 no_verify=true

""")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-S', '--search', help='Hostname string to find in Zabbix')
group.add_argument(
    '-A', '--all', help='Returns all hosts Zabbix', action='store_true')
parser.add_argument('-u', '--username', help='User for the Zabbix api')
parser.add_argument('-p', '--password',
                    help='Password for the Zabbix api user')
parser.add_argument('-a', '--api', help='Zabbix API URL')
parser.add_argument(
    '--no-verify', help='Disables certificate validation when using a secure connection', action='store_true')
parser.add_argument(
    '-c', '--config', help='Config file location (defaults to $HOME/.zbx.conf)')
parser.add_argument(
    '-n', '--numeric', help='Return numeric hostids instead of host name', action='store_true')
parser.add_argument('-e', '--extended',
                    help='Return both hostids and host names separated with a ":"', action='store_true')
parser.add_argument('-m', '--monitored',
                    help='Only return hosts that are being monitored', action='store_true')
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

zapi = ZabbixAPI(url=api,user=username,password=password,validate_certs=verify)

##################################
# Start actual API logic
##################################

# Find the hostgroup we are looking for
search_name = args.search

if search_name:
    # Find matching hosts
    if args.monitored:
        hosts = zapi.host.get(output="extend", monitored_hosts=True, search={
                              "host": search_name})
    else:
        hosts = zapi.host.get(output="extend", search={"host": search_name})
elif args.all:
    # Find matching hosts
    if args.monitored:
        hosts = zapi.host.get(output="extend", monitored_hosts=True)
    else:
        hosts = zapi.host.get(output="extend")
else:
    sys.exit("Error: No hosts to find")

if hosts:
    if args.extended:
        # print ids and names
        for host in hosts:
            print((format(host["hostid"])+":"+format(host["host"])))
    else:
        if args.numeric:
            # print host ids
            for host in hosts:
                print((format(host["hostid"])))
        else:
            # print host names
            for host in hosts:
                print((format(host["host"])))
else:
    sys.exit("Error: Could not find any hosts matching \"" + search_name + "\"")

zapi.logout()
# And we're done...
