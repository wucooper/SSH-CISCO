#!/usr/bin/env python


import yaml
import time
import threading
import random
import re
import shutil
import os.path
import datetime
import paramiko
#from flask import flask, render_template



LOGIN_USR    = "admin"
LOGIN_PASS   = "admin"
LOGIN_DELAY  = 6
CMD_DELAY    = 6 
CONCURR      = 8 
IOS_CMDS     = []
DEV_LIST     = []
CUR_DIR      = "./COLLECT-IOS-OUTPUT/"
CMD_ANALYSE  = []






def Is_Valid_IP(str_ip):
	Is_IP = True
	IP_Split = str_ip.split(".")
	if len(IP_Split) !=4:
		return False
	for x in IP_Split:
		Is_IP = Is_IP and x.isdigit()
	return Is_IP


def RUN_CMD(ra_conn,str_cmd):
	ra_conn.send(str_cmd)
	ra_conn.send("\n")
	time.sleep(CMD_DELAY)
	ra_output = ra_conn.recv(65535)
#	file_log.write("\n\n\n---------command: " + str_cmd + "   ------\n")
#	file_log.writelines(ra_output)
#	file_log.flush()
	return ra_output


def ANALYSE_OUTPUT(str_outpout, str_type="BGP"):

	Neighbor_List = []

        if str_type == "EIGRP":
            str_re = "^[0-9]+"
        
        if str_type == "BGP":
        	str_re = "^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"

        for read_line in str_outpout.splitlines():
                read_line = read_line.strip().lower()
                matchobj = re.match(str_re, read_line, re.I)                
                if matchobj:
                 	neighbor_str = read_line.split()
                 	if str_type == "EIGRP":
                 		neighbor_ip     = neighbor_str[1]
                 		neighbor_uptime = neighbor_str[4]
                 		neighbor_pfxrcd = "1"
                 	else:
                 		neighbor_ip     = neighbor_str[0]
                 		neighbor_uptime = neighbor_str[8]
                 		neighbor_pfxrcd = "_".join(neighbor_str[9:])

                 	if neighbor_pfxrcd.isdigit() == False:
                 		neighbor_state  = "Critical"
                 	elif neighbor_uptime.count(":") > 0:
                 		neighbor_state  = "Warning"
                 	else:
                 		neighbor_state  = "Healthy"

                 	Neighbor_List.append({'PROTOCOL':str_type,'neighbor':neighbor_ip,'DURATION':neighbor_uptime,'STATE':neighbor_state})

        if len(Neighbor_List) == 0:
        	Neighbor_List.append({'PROTOCOL':str_type,         'neighbor':'NONE',    'DURATION':'none',         'STATE':'Critical'})

        return Neighbor_List






def SSH_DEVICE(seq, node_info, login_usr, login_passwd , dev_type="IOS"):

	Node_Name = node_info["NAME"]
	Node_IP   = node_info["IP"]
	Node_Desc = node_info["DESCRIPTION"]
	Node_BGP  = node_info["BGP"]
	Node_EIGRP= node_info["EIGRP"]
	CMDS      = []
	global CMD_ANALYSE
	Node_Output = []


	if Node_BGP == True:
		CMDS.append("show ip bgp summary")

	if Node_EIGRP == True:
		for intf in node_info["EIGRP_INTF"]:
			CMDS.append("show ip eigrp neighbor "+intf)

#	print "Start processing .....", Node_Name

	cur_timestamp = datetime.datetime.now().strftime("%Y-%B-%d-%H:%M")

	remote_ra_pre = paramiko.SSHClient()
	remote_ra_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy)

#	File_OutputLog = open(CUR_DIR + Node_Name+"_output","a+")
#   SFC-AAPT-001 [{'UPTIME': '2w0d', 'PROTOCOL': 'BGP', 'STATE': 'Healthy', 'neighbor': '172.22.0.245'}]
	try:
		remote_ra_pre.connect(Node_IP, username=login_usr, password=login_passwd, timeout=LOGIN_DELAY)		
		remote_ra= remote_ra_pre.invoke_shell()
	except:
#		print "------- Unable to ssh ", Node_Name
		CMD_ANALYSE[seq] = ({'Node': Node_Name, 'State':'SSH Unreachable','TimeStamp':cur_timestamp,'result':[{'PROTOCOL':'unknown','neighbor':'unknown','DURATION':'unknow','STATE':'Critical'}]})
#		File_OutputLog.write("Unreable\n")
#		File_OutputLog.flush()
#		File_OutputLog.close()
		return 0

	if dev_type == "WLC":
		remote_ra.send(login_usr)
		remote_ra.send("\n")
		remote_ra.send(login_passwd)
		remote_ra.send("\n")

		
	time.sleep(CMD_DELAY)
	ra_output = remote_ra.recv(65535)

	if "user" in ra_output[-5:].lower() or "password" in ra_output[-8:].lower():
#		print "------ login credential may be wrong for ", Node_Name
		CMD_ANALYSE[seq] = ({'Node':Node_Name, 'State':'Login_Failed','TimeStamp':cur_timestamp,'result':[{'PROTOCOL':'unknown','neighbor':'unknown','DURATION':'unknow','STATE':'Warning'}]})
#		File_OutputLog.write("Credential_Wrong\n")
#		File_OutputLog.flush()
#		File_OutputLog.close()
		ssh_ra.close()	
		return 1


	if dev_type == "IOS":
		RUN_CMD(remote_ra, "term len 0")
		RUN_CMD(remote_ra, "show clock")

	for ios_cmd in CMDS:
		CMD_OUTPUT = RUN_CMD(remote_ra, ios_cmd)
		if ios_cmd.find("show ip bgp") != -1:
#			print Node_Name, ANALYSE_OUTPUT(CMD_OUTPUT, "BGP")
			Node_Output = Node_Output + ANALYSE_OUTPUT(CMD_OUTPUT, "BGP")
		if ios_cmd.find("show ip eigrp neighbor") != -1:
#			print Node_Name, ANALYSE_OUTPUT(CMD_OUTPUT, "EIGRP")
			Node_Output = Node_Output + ANALYSE_OUTPUT(CMD_OUTPUT, "EIGRP")


	CMD_ANALYSE[seq] = {'Node':Node_Name, 'State':Node_Desc,'TimeStamp':cur_timestamp,'result':Node_Output}
#	print CMD_ANALYSE[seq]

	remote_ra.close()	
#	File_OutputLog.close()

#	print "Finshed processing....", Node_Name
					



#  __main__   starts here ....

yml_stream = open(CUR_DIR+"NetworkConfig.yml", "r")
yml_schema = yaml.load(yml_stream)

LOGIN_USR	= yml_schema["CONFIGURATION"]["user"]
LOGIN_PASS	= yml_schema["CONFIGURATION"]["password"]
CONCURR		= yml_schema["CONFIGURATION"]["concurrent"]




yml_stream = open(CUR_DIR+"IP_LIST.yml", "r")
yml_schema = yaml.load(yml_stream)



#IOS_CMDS = yml_schema["IOS_COMMAND"]
DEV_LIST = yml_schema["DEVICE_LIST"]
	
if not os.path.exists(CUR_DIR):
    os.mkdir(CUR_DIR)


i=0
for i in range (len(DEV_LIST)+1):
	CMD_ANALYSE.append("")

i = 0
while(i < len(DEV_LIST)):
    if threading.activeCount() <= CONCURR:
        t = threading.Thread(target=SSH_DEVICE, args=(i, DEV_LIST[i], LOGIN_USR, LOGIN_PASS, "IOS"))
        t.start()
        i = i+1


t.join()

#progress only after all threads end

File_Name_CUR= CUR_DIR + "HA_MONITORING_CUR.yml"
File_Name_New = CUR_DIR + "HA_MONITORING_NEW.yml"



File_Output_Handler = open(File_Name_New,"w")

#for j in CMD_ANALYSE:
#	print j,'\n'

yaml.dump( CMD_ANALYSE, File_Output_Handler, default_flow_style = False)

File_Output_Handler.close()

shutil.move(File_Name_New,File_Name_CUR)

