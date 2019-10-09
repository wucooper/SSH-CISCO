#! /usr/bin/python

import sys
import csv
import time
import re
import os.path
import datetime
import paramiko


usr_wlc = "xxx"
pwd_wlc = "xxx"

LOGIN_TIMEOUT   = 10
CMD_TIMEOUT		= 3

COLUMN_IP_IN_DEV_FILE	= 1

export_file_1 	= "WLC_POST_CONFIG_STATUS.csv"
export_file_log = "WLC_POST_CONFIG_LOG.log"

ISE_ORDER   = []
ISE_AMS   = ["10.xx.xx.xx","10.xx.xx.xx","10.xx.xx.xx"]
ISE_OCA   = ["10.xx.xx.xx","10.xx.xx.xx","10.xx.xx.xx"]
ISE_EMEA  = ["10.xx.xx.xx","10.xx.xx.xx","10.xx.xx.xx"]
ISE_GB    = ["10.xx.xx.xx","10.xx.xx.xx","10.xx.xx.xx"]
ISE_ASIA  = ["10.xx.xx.xx","10.xx.xx.xx","10.xx.xx.xx"]

def Is_Valid_IP(str_ip_subnet):
	Is_IP = True
	str_1 = str_ip_subnet.split("/")
	if len(str_1)!=2:
		return False,str_ip_subnet
	str_ip = str_1[0]

	IP_Split = str_ip.split(".")
	if len(IP_Split) !=4:
		return False,str_ip
	for x in IP_Split:
		Is_IP = Is_IP and x.isdigit()
	return Is_IP,str_ip



def ssh_wlc(wlc_ip, login_usr, login_passwd):
	remote_ra_pre = paramiko.SSHClient()
	remote_ra_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	try:
		remote_ra_pre.connect(wlc_ip, username=login_usr,password=login_passwd,timeout=LOGIN_TIMEOUT)		
		remote_ra= remote_ra_pre.invoke_shell()
	except:
		return 0, 0

	remote_ra.send(login_usr)
	remote_ra.send("\n")
	remote_ra.send(login_passwd)
	remote_ra.send("\n")

	time.sleep(CMD_TIMEOUT)

	ra_output = remote_ra.recv(65535)

	if "user" in ra_output[-5:].lower():
		return 1, remote_ra
	else:
		return 2, remote_ra



def ssh_output(ra_conn,file_log):
	time.sleep(2)
	ra_output = ra_conn.recv(65535)
	file_log.write(ra_output)
	return ra_output


def ssh_cmd(ra_conn,file_log,str_cmd):
	ra_conn.send(str_cmd)
	ra_conn.send("\n")
	time.sleep(1)
	ra_output = ra_conn.recv(65535)
	file_log.writelines(ra_output)
	print ra_output



if __name__ == '__main__':


# Column 0 : Hostname
# Column 2 : IP/subnet
# Column 5 : Location|Dev_Type
# Column 39: TACACS_Shared-Secret

	WLC_IP = []

	File_Output_1 = open(export_file_1,"a+")
	File_Log      = open(export_file_log,"a+")
	with open(sys.argv[1],"r") as Dev_File:
		for row in csv.reader(Dev_File):
#			print row[0],row[2],row[5],row[39]
			WLC_IP = Is_Valid_IP(row[2])	
			if WLC_IP[0] == True:
				if row[5].upper().find("#AMERICAS") != -1:
					ISE_ORDER = ISE_AMS
				elif row[5].upper().find("#OCEAN") != -1:
					ISE_ORDER = ISE_OCA
				elif row[5].upper().find("#ASIA") != -1:
					ISE_ORDER = ISE_ASIA
				elif row[5].upper().find("#BRANCH-GBR") != -1:
					ISE_ORDER = ISE_GB
				elif row[5].upper().find("#BRANCH-ME") != -1:
					ISE_ORDER = ISE_EMEA
				else:
					ISE_ORDER = ISE_OCA
				print WLC_IP[1], ISE_ORDER
				i = 1
				ssh_ra_status, ssh_ra = ssh_wlc(WLC_IP[1],usr_wlc, pwd_wlc)
				if ssh_ra_status==2:
					for ISE_IP in ISE_ORDER:
						ssh_cmd(ssh_ra, File_Log, "config tacacs auth add "+ str(i)+" "+ISE_IP+" 49 ascii "+row[39])
						ssh_cmd(ssh_ra, File_Log, "config tacacs auth server-timeout "+ str(i)+ " 5")
						ssh_cmd(ssh_ra, File_Log, "config tacacs auth enable "+ str(i))

						ssh_cmd(ssh_ra, File_Log, "config tacacs athr add "+ str(i)+" "+ISE_IP+" 49 ascii "+row[39])
						ssh_cmd(ssh_ra, File_Log, "config tacacs athr server-timeout "+ str(i)+ " 5")
						ssh_cmd(ssh_ra, File_Log, "config tacacs athr enable "+ str(i))

						ssh_cmd(ssh_ra, File_Log, "config tacacs acct add "+ str(i)+" "+ISE_IP+" 49 ascii "+row[39])
						ssh_cmd(ssh_ra, File_Log, "config tacacs acct server-timeout "+ str(i)+ " 5")
						ssh_cmd(ssh_ra, File_Log, "config tacacs acct enable "+ str(i))

						i+=1
#	 				print "config aaa auth mgmt tacacs local"
					ssh_cmd(ssh_ra, File_Log, "config tacacs fallback-test interval 600")

					ssh_cmd(ssh_ra, File_Log, "config aaa auth mgmt tacacs local")

					ssh_cmd(ssh_ra, File_Log, "config mgmtuser add net-admin xxxxxx read-write NETWORK_ADMIN_LOCAL_ACCOUNT")

					ssh_cmd(ssh_ra, File_Log, "config mgmtuser add wlc-monitor xxxxx read-only COMMS_MONITOR_LOCAL_ACCOUNT")


					ssh_cmd(ssh_ra, File_Log, "config snmp community delete public")

					ssh_cmd(ssh_ra, File_Log, "config snmp community delete private")

					ssh_cmd(ssh_ra, File_Log, "config snmp community create xxxx")

					ssh_cmd(ssh_ra, File_Log, "config snmp community accessmode ro xxxx")

					ssh_cmd(ssh_ra, File_Log, "config snmp community ipaddr 10.x.0.0 255.255.224.0 xxx")

					ssh_cmd(ssh_ra, File_Log, "config network mgmt-via-wireless disable")

					ssh_cmd(ssh_ra, File_Log, "config network ssh enable")

					ssh_cmd(ssh_ra, File_Log, "config network telnet disable")

#					ssh_cmd(ssh_ra, File_Log, "config network secureweb enable")

					ssh_cmd(ssh_ra, File_Log, "config network webmode disable ")

					ssh_cmd(ssh_ra, File_Log, "save config")

					ssh_cmd(ssh_ra, File_Log, "y")

					File_Log.flush()

					ssh_ra.close()

				if ssh_ra_status==0:
					Output_Entry = ",".join([row[0],row[2], "Ureachable"])
				elif ssh_ra_status==1:
					Output_Entry = ",".join([row[0],row[2], "Credential_Wrong"])
				else:
					Output_Entry = ",".join([row[0],row[2], "Succeed"])

				File_Output_1.write(Output_Entry + "\n")

# config snmp community create ghdro
# config snmp community accessmode ro ghdro 
# config snmp community mode enable ghdro			
# config snmp community delete private
# config snmp community delete public


		File_Output_1.close()
		File_Log.close()

