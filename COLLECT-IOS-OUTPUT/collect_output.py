#!/usr/bin/env python


import yaml
import time
import threading
import random
import re
import os.path
import datetime
import paramiko

LOGIN_USR    = "admin"
LOGIN_PASS   = "admin"
LOGIN_DELAY  = 5
CMD_DELAY    = 2
CONCURR      = 5
IOS_CMDS     = []
DEV_LIST     = []
CUR_DIR      = "./COLLECT-IOS-OUTPUT/SFC-CORE/"
PY_DIR       = "./COLLECT-IOS-OUTPUT/SFC-CORE/"

def RUN_CMD(ra_conn,file_log,str_cmd):
	ra_conn.send(str_cmd)
	ra_conn.send("\n")
	time.sleep(CMD_DELAY)
	ra_output = ra_conn.recv(65535)
	file_log.write("\n\n\n---------command: " + str_cmd + "   ------\n")
	file_log.writelines(ra_output)
	file_log.flush()


def SSH_DEVICE(Node, CMDS, login_usr, login_passwd , dev_type="IOS"):

	print "Start processing .....", Node

	remote_ra_pre = paramiko.SSHClient()
	remote_ra_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy)

	File_OutputLog = open(CUR_DIR + Node+"_output","a+")

	try:
		remote_ra_pre.connect(Node, username=login_usr, password=login_passwd, timeout=LOGIN_DELAY)		
		remote_ra= remote_ra_pre.invoke_shell()
	except:
		print "------- Unable to ssh ", dev_ip
		File_OutputLog.write("Unreable\n")
		File_OutputLog.flush()
		File_OutputLog.close()
		return 0

	if dev_type == "WLC":
		remote_ra.send(login_usr)
		remote_ra.send("\n")
		remote_ra.send(login_passwd)
		remote_ra.send("\n")

		
	time.sleep(CMD_DELAY)
	ra_output = remote_ra.recv(65535)

	if "user" in ra_output[-5:].lower() or "password" in ra_output[-8:].lower():
		print "------ login credential may be wrong for ", dev_ip
		File_OutputLog.write("Credential_Wrong\n")
		File_OutputLog.flush()
		File_OutputLog.close()
		ssh_ra.close()	
		return 1


	if dev_type == "IOS":
		RUN_CMD(remote_ra, File_OutputLog, "term len 0")
		RUN_CMD(remote_ra, File_OutputLog, "show clock")

	for ios_cmd in CMDS:
		RUN_CMD(remote_ra, File_OutputLog, ios_cmd)


	remote_ra.close()	
	File_OutputLog.close()

	print "Finshed processing....", Node 
					



#  __main__   starts here ....

yml_stream = open(PY_DIR+"NetworkConfig.yml", "r")
yml_schema = yaml.load(yml_stream)

LOGIN_USR	= yml_schema["CONFIGURATION"]["user"]
LOGIN_PASS	= yml_schema["CONFIGURATION"]["password"]
CONCURR		= yml_schema["CONFIGURATION"]["concurrent"]

yml_stream = open(PY_DIR+"NetworkDev.yml", "r")
yml_schema = yaml.load(yml_stream)


if type(yml_schema["DEVICE_LIST"]) != "list":
    exit

if type(yml_schema["IOS_COMMAND"]) != "list":
    exit

IOS_CMDS = yml_schema["IOS_COMMAND"]
DEV_LIST = yml_schema["DEVICE_LIST"]
	
i=0

CUR_DIR = CUR_DIR + datetime.datetime.now().strftime("%Y-%m-%d:%H") + "/"

if not os.path.exists(CUR_DIR):
    os.mkdir(CUR_DIR)

while(i < len(DEV_LIST)):
    if threading.activeCount() <= CONCURR:
        t = threading.Thread(target=SSH_DEVICE, args=(DEV_LIST[i], IOS_CMDS , LOGIN_USR, LOGIN_PASS, "IOS"))
        t.start()
        i = i+1


		
