# -*- coding: utf-8 -*-
#
# dBackup Plugin by gutemine
#
dbackup_version="0.27"
#
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config, ConfigSubsection, ConfigText, ConfigBoolean, ConfigInteger, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Plugins.Plugin import PluginDescriptor
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox 
from Screens.InputBox import InputBox
from Components.Input import Input
from Screens.ChoiceBox import ChoiceBox
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from Screens.Console import Console                                                                           
from Components.MenuList import MenuList       
from Components.Slider import Slider       
from enigma import  ePoint, getDesktop, quitMainloop, eConsoleAppContainer, eDVBVolumecontrol, eTimer, eActionMap
from Tools.LoadPixmap import LoadPixmap
import Screens.Standby  
import sys, os, struct, stat, time
from twisted.web import resource, http
import gettext, datetime, shutil

dbackup_plugindir="/usr/lib/enigma2/python/Plugins/Extensions/dBackup" 
dbackup_bin="/bin"
dbackup_busy="/tmp/.dbackup"
dbackup_script="/tmp/dbackup.sh"
dbackup_backup="/tmp/.dbackup-result"
dbackup_backupscript="/tmp/dbackup.sh"
dbackup_log="/tmp/dbackup.log"

# add local language file
dbackup_sp=config.osd.language.value.split("_")
dbackup_language = dbackup_sp[0]
if os.path.exists("%s/locale/%s" % (dbackup_plugindir,dbackup_language)):
	_=gettext.Catalog('dbackup', '%s/locale' % dbackup_plugindir,dbackup_sp).gettext

boxtype="dm7080hd"
if os.path.exists("/proc/stb/info/model"):
	f=open("/proc/stb/info/model")
	boxtype=f.read()
	f.close()
	boxtype=boxtype.replace("\n","").replace("\l","")
	
yes_no_descriptions = {False: _("no"), True: _("yes")}    

config.plugins.dbackup = ConfigSubsection()
f=open("/proc/mounts", "r")
m = f.read()                                                    
f.close()
if m.find("/media/hdd") is not -1:
	config.plugins.dbackup.backuplocation = ConfigText(default = "/media/hdd/backup", fixed_size=True, visible_width=20)
else:
	config.plugins.dbackup.backuplocation = ConfigText(default = "/autofs/sda1", fixed_size=True, visible_width=20)
config.plugins.dbackup.backupdeb = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.backupimagetype = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.backupboxtype = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.backupdate = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.backuptime = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.sig = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.loaderextract = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.loaderflash = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.kernelextract = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.kernelflash = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.sort = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
config.plugins.dbackup.delay = ConfigInteger(default = 0, limits=(0,60))

if not os.path.exists("/var/lib/opkg/status"):
	config.plugins.dbackup.aptclean = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
	config.plugins.dbackup.epgdb = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
	config.plugins.dbackup.webinterface = ConfigBoolean(default = True, descriptions=yes_no_descriptions)
else:
	config.plugins.dbackup.aptclean = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
	config.plugins.dbackup.epgdb = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
	config.plugins.dbackup.webinterface = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.settings = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.timers = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
config.plugins.dbackup.picons = ConfigBoolean(default = False, descriptions=yes_no_descriptions)

dbackup_options = []                                                     
dbackup_options.append(( "settings",_("Settings") ))
dbackup_options.append(( "plugin",_("Pluginlist") ))   
dbackup_options.append(( "extension",_("Extension") ))
dbackup_options.append(( "both",_("both") ))
dbackup_options.append(( "all",_("all") ))
config.plugins.dbackup.showing = ConfigSelection(default = "settings", choices = dbackup_options)

flashtools=[]
flashtools.append(( "rescue", _("Rescue Bios") ))
#flashtools.append(( "recovery", _("Recovery USB") ))
flashtools.append(( "direct", _("direct") ))
config.plugins.dbackup.flashtool = ConfigSelection(default = "direct", choices = flashtools)
config.plugins.dbackup.console = ConfigBoolean(default = True, descriptions=yes_no_descriptions)

config.plugins.dbackup.transparency = ConfigInteger(default = 0, limits=(0,255))
config.plugins.dbackup.verbose = ConfigBoolean(default = False, descriptions=yes_no_descriptions)
	
backuptools=[]
backuptools.append(( "tar.gz", _("tar.gz") ))
backuptools.append(( "tar.xz", _("tar.xz") ))
backuptools.append(( "tar.bz2", _("tar.bz2") ))
backuptools.append(( "tar", _("tar") ))
config.plugins.dbackup.backuptool = ConfigSelection(default = "tar.gz", choices = backuptools)
config.plugins.dbackup.overwrite = ConfigBoolean(default = False, descriptions=yes_no_descriptions)

exectools=[]
exectools.append(( "daemon", _("daemon") ))
exectools.append(( "system", _("system") ))
exectools.append(( "container", _("container") ))
config.plugins.dbackup.exectool = ConfigSelection(default = "system", choices = exectools)

fileupload_string=_("Select tar.*z image for flashing")
disclaimer_header=_("Disclaimer")
info_header=_("Info")
disclaimer_string=_("This way of flashing your Dreambox is not supported by DMM.\n\nYou are using it completely at you own risk!\nIf you want to flash your Dreambox safely use the Recovery Webinterface!\n\nMay the Power button be with you!")
disclaimer_wstring=disclaimer_string.replace("\n","<br>")
plugin_string=_("Dreambox Backup Plugin by gutemine Version %s") % dbackup_version
flashing_string=_("Flashing") 
backup_string=_("Backup") 
setup_string=_("Configuring")
checking_string=_("Checking")
running_string=_("dBackup is busy ...")
backupimage_string=_("Enter Backup Imagename")
backupdirectory_string=_("Enter Backup Path")
unsupported_string=_("Sorry, currently not supported on this Dreambox type")
notar_string=_("Sorry, no correct tar.*z file selected")
noxz_string=_("Sorry, no xz binary found")
refresh_string=_("Refresh")
mounted_string=_("Nothing mounted at %s")
barryallen_string=_("Sorry, use Barry Allen for Backup")
lowfat_string=_("Sorry, use LowFAT for Backup")
noflashing_string=_("Sorry, Flashing works only in Flash")
nowebif_string=_("Sorry, dBackup webinterface is currently disabled")

header_string  =""
header_string +="<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\""
header_string +="\"http://www.w3.org/TR/html4/loose.dtd\">"
header_string +="<head><title>%s</title>" % plugin_string
header_string +="<link rel=\"shortcut icon\" type=\"/web-data/image/x-icon\" href=\"/web-data/img/favicon.ico\">"
header_string +="<meta content=\"text/html; charset=UTF-8\" http-equiv=\"content-type\">"
header_string +="</head><body bgcolor=\"black\">"
header_string +="<font face=\"Tahoma, Arial, Helvetica\" color=\"yellow\">"
header_string +="<font size=\"3\" color=\"yellow\">"

dbackup_backbutton=_("use back button in browser and try again!") 
dbackup_flashing=""
dbackup_flashing += header_string
dbackup_flashing += "<br>%s ...<br><br>" % flashing_string
dbackup_flashing +="<br><img src=\"/web-data/img/dbackup.png\" alt=\"%s ...\"/><br><br>" % (flashing_string)

dbackup_backuping  =""
dbackup_backuping += header_string
dbackup_backuping += "<br>%s<br><br>" % running_string
dbackup_backuping +="<br><img src=\"/web-data/img/ring.png\" alt=\"%s ...\"/><br><br>" % (backup_string)
dbackup_backuping +="<br><form method=\"GET\">"
dbackup_backuping +="<input name=\"command\" type=\"submit\" size=\"100px\" title=\"%s\" value=\"%s\">" % (refresh_string,"Refresh")
dbackup_backuping +="</form>"                        

global dbackup_progress
dbackup_progress=0

class dBackup(Screen):
	skin = """
		<screen position="center,80" size="680,70" title="Flashing" >
		<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
		<widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
		<widget name="slider" position="10,55" size="660,5"/>
	</screen>"""
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.onShown.append(self.setWindowTitle)      
                self.onLayoutFinish.append(self.byLayoutEnd)
		self["logo"] = Pixmap()
		self["buttonred"] = Label(_("Cancel"))
		self["buttongreen"] = Label(_("Backup"))
		self["buttonyellow"] = Label(_("Flashing"))
		self["buttonblue"] = Label(setup_string)
		self.slider = Slider(0, 500)
	        self["slider"] = self.slider
		                         
                self.dimmed=config.av.osd_alpha.value
		self.onShow.append(self.connectHighPrioAction) 
		self.onHide.append(self.disconnectHighPrioAction)
		if config.plugins.dbackup.flashtool.value == "rescue":
			config.plugins.dbackup.backuplocation.value = "/data/.recovery"
			config.plugins.dbackup.backuptool.value = "tar.gz"
			config.plugins.dbackup.backuplocation.save()
			config.plugins.dbackup.backuptool.save()
		        
		self["setupActions"] = ActionMap([ "ColorActions", "SetupActions" ],
			{
			"green": self.backup,
			"red": self.leaving,
			"blue": self.config,
			"yellow": self.flash,
			"save": self.leaving,
			"cancel": self.leaving,
			})

	def connectHighPrioAction(self):
		self.highPrioActionSlot = eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.doUnhide)

	def disconnectHighPrioAction(self):
		self.highPrioAction = None

	def setWindowTitle(self):
		if os.path.exists(dbackup_busy):                                                                   
       			self["logo"].instance.setPixmapFromFile("%s/ring.png" % dbackup_plugindir)
		else:                                                                            
       			self["logo"].instance.setPixmapFromFile("%s/dbackup.png" % dbackup_plugindir)
		self.setTitle(backup_string+" & "+flashing_string+" V%s" % dbackup_version)

        def byLayoutEnd(self):
                self["logo"].instance.setPixmapFromFile("%s/dbackup.png" % dbackup_plugindir)
                self.slider.setValue(0)
                
	def leaving(self):
	        if os.path.exists(dbackup_busy):
#			os.remove(dbackup_busy)
			self.session.openWithCallback(self.forcedexit,MessageBox, running_string, MessageBox.TYPE_WARNING)
		else:
			self.forcedexit([1,1])
			
	def forcedexit(self,status):
		if status > 0:
		        self.doUnhide(0, 0)                                  
			self.close()

        def checking(self):      
	       self.session.open(dBackupChecking)
                
	def doHide(self):
		if config.plugins.dbackup.transparency.value < config.av.osd_alpha.value:
			print "[dBackup] hiding"
	                self.dimmed=config.av.osd_alpha.value
			self.DimmingTimer = eTimer()
			if not os.path.exists("/var/lib/opkg/status"):
	 			self.DimmingTimer_conn = self.DimmingTimer.timeout.connect(self.doDimming)
			else:
				self.DimmingTimer.callback.append(self.doDimming)
			self.DimmingTimer.start(200, True)
		else:
			print "[dBackup] no hiding"

	def doDimming(self):
		self.DimmingTimer.stop()
		if self.dimmed > 5:
			self.dimmed=self.dimmed-5
		else:
			self.dimmed=0
#		print self.dimmed
	        f=open("/proc/stb/video/alpha","w")
        	f.write("%i" % self.dimmed)
	        f.close()
		# continue dimming ?
		if self.dimmed > config.plugins.dbackup.transparency.value:
			self.DimmingTimer.start(200, True)
		else:
			# do final choosen transparency
			f=open("/proc/stb/video/alpha","w")
        		f.write("%i" % config.plugins.dbackup.transparency.value)
	        	f.close()
	     	      
        def doUnhide(self, key, flag):                                                                 
		print "[dBackup] unhiding"
		if config.plugins.dbackup.transparency.value < config.av.osd_alpha.value:
			# reset needed
        	        f=open("/proc/stb/video/alpha","w")
                	f.write("%i" % (config.av.osd_alpha.value))
                	f.close()
			if os.path.exists(dbackup_busy):
				self.doHide()
		else:
			print "[dBackup] no unhiding"
		return 0

	def flash(self):
		k=open("/proc/cmdline","r")       
		cmd=k.read()     
		k.close()                
	        if os.path.exists(dbackup_busy):
			self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
		elif os.path.exists("/.bainfo"):
			self.session.open(MessageBox, noflashing_string, MessageBox.TYPE_ERROR)
		elif os.path.exists("/.lfinfo"):
			self.session.open(MessageBox, noflashing_string, MessageBox.TYPE_ERROR)
		elif cmd.find("root=/dev/mmcblk0") is -1:
			self.session.open(MessageBox, noflashing_string, MessageBox.TYPE_ERROR)
		else:
			if config.plugins.dbackup.flashtool.value != "rescue":
       				self.session.openWithCallback(self.askForImage,ChoiceBox,fileupload_string,self.getImageList())
			else:
				print "[dBackup] boots rescue mode ..."
				self.nfifile="recovery"
				self.session.openWithCallback(self.doFlash, MessageBox, _("Press OK now for flashing\n\n%s\n\nBox will reboot automatically when finished!") % self.nfifile, MessageBox.TYPE_INFO)

	def askForImage(self,image):
        	if image is None:
			self.session.open(MessageBox, notar_string, MessageBox.TYPE_ERROR)
        	else:
			print "[dBackup] flashing ..."
			self.nfiname=image[0]
			self.nfifile=image[1]
			self.nfidirectory=self.nfifile.replace(self.nfiname,"")
			if os.path.exists(dbackup_busy):
				os.remove(dbackup_busy)
			if self.nfifile.endswith("tar.xz") and not os.path.exists("%s/bin/xz" % dbackup_plugindir) and not os.path.exists("/usr/bin/xz"):
				self.session.open(MessageBox, noxz_string, MessageBox.TYPE_ERROR)
			else:
        	       		self.session.openWithCallback(self.startFlash,MessageBox,_("Are you sure that you want to flash now %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)

        def getImageList(self):                                               
        	liststart = []                                                        
        	list = []                                                        
        	liststart.append((_("Recovery Image from Feed"), "recovery" ))                         
        	for name in os.listdir("/tmp"):                          
			if (name.endswith(".tar.gz") or name.endswith(".tar.xz") or name.endswith(".tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
        	       		list.append(( name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar",""), "/tmp/%s" % name ))                         
#		if not config.plugins.dbackup.backuplocation.value.startswith("/media/net"):
		if os.path.exists(config.plugins.dbackup.backuplocation.value):
        		for name in os.listdir(config.plugins.dbackup.backuplocation.value):                          
				if (name.endswith(".tar.gz") or name.endswith(".tar.xz") or name.endswith(".tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
	        	       		list.append(( name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar",""), "%s/%s" % (config.plugins.dbackup.backuplocation.value,name) ))                         
           	for directory in os.listdir("/media"):                          
			if os.path.exists("/media/%s" % directory) and os.path.isdir("/media/%s" % directory) and not directory.endswith("net") and not directory.endswith("hdd"):
           			for name in os.listdir("/media/%s" % directory):                          
					if (name.endswith(".tar.gz") or name.endswith(".tar.xz") or name.endswith(".tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
		        	       		list.append(( name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar",""), "%s/%s" % (directory,name) ))                         
		if config.plugins.dbackup.sort.value:
			list.sort()
		# recovery image is always first ...
		liststart=liststart+list
        	return liststart                                                

	def startFlash(self,option):
        	if option:
			self.session.openWithCallback(self.doFlash, MessageBox, _("Press OK now for flashing\n\n%s\n\nBox will reboot automatically when finished!") % self.nfifile, MessageBox.TYPE_INFO)
        	else:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
				
	def getDeviceList(self):                                                                                                                     
                found=False                                                                                                                             
                f=open("/proc/partitions","r")                                                                                                          
                devlist= []                                                                                                                          
                line = f.readline()                                                                                                                  
                line = f.readline()                                                                                                                  
               	sp=[]                                                                                                                
                while (line):                                                                                                                        
        		line = f.readline()                                                                                                          
                        if line.find("sd") is not -1:                                                                                                  
                                sp=line.split()                                                                                                   
                                print sp
                                devsize=int(sp[2])                                                                                       
                                mbsize=devsize/1024                                                                                      
                                devname="/dev/%s" % sp[3]                                                                                        
                                print devname, devsize
				if config.plugins.dbackup.flashtool.value == "usb":
                        		if len(devname) == 8 and mbsize < 36000 and mbsize > 480:
						# only sticks from 512 MB up to 32GB are used as recovery sticks
	                        		found=True
        	                                devlist.append(("%s %d %s" % (devname,mbsize,"MB"), devname,mbsize))
				else:
	                        	if len(devname) > 8 and mbsize > rambo_minpartsize:
                        			found=True
                                        	devlist.append(("%s %d %s" % (devname,mbsize,"MB"), devname,mbsize))
                f.close()                                                                                         
                if not found:                                                                                    
                	devlist.append(("no device found, shutdown, add device and reboot" , "nodev", 0))         
                return devlist                                                                                    
                
	def askForDevice(self,device):                                                                            
		if device is None:                                                                                
			self.session.open(MessageBox, _("Sorry, no device choosen"), MessageBox.TYPE_ERROR)
	        elif device[1] == "nodev":                                                                        
			self.session.open(MessageBox, _("Sorry, no device found"), MessageBox.TYPE_ERROR)
	        else:                                                                                             
	                self.device=device[1]                                                                                                         
			if config.plugins.dbackup.flashtool.value == "usb":
				self.session.openWithCallback(self.strangeFlash,MessageBox,_("Are you sure that you want to FORMAT recovery device %s now for %s ?") % (self.device, self.nfifile), MessageBox.TYPE_YESNO)
			else:
				self.session.openWithCallback(self.strangeFlash,MessageBox,_("Are you sure that you want to flash now %s ?") %(self.nfifile), MessageBox.TYPE_YESNO)
	        
	def strangeFlash(self,option):                                                                            
        	if option is False:
			self.session.open(MessageBox, _("Sorry, Flashing of %s was canceled!") % self.nfifile, MessageBox.TYPE_ERROR)
		else:
############################################################
			return
############################################################
                        open(dbackup_busy, 'a').close()
                        if not os.path.exists("/tmp/strange"):
	                        os.mkdir("/tmp/strange")
	                else:
                        	os.system("umount /tmp/strange")                                                            
			if config.plugins.dbackup.flashtool.value == "rawdevice":
                       		self["logo"].instance.setPixmapFromFile("%s/ring.png" % dbackup_plugindir)                      
                               	command="%s/nfiwrite -r %s %s" % (dbackup_bin, self.device, self.nfifile)                                
                        else:
				if config.plugins.dbackup.flashtool.value != "usb":
	        	                os.system("mount %s /tmp/strange" % self.device)                                                            
	               		f=open("/proc/mounts", "r")
     	  		 	m = f.read()                                                    
       			 	f.close()
       		 		if m.find("/tmp/strange") is not -1 or config.plugins.dbackup.flashtool.value == "usb":
                        		self["logo"].instance.setPixmapFromFile("%s/ring.png" % dbackup_plugindir)                      
					if config.plugins.dbackup.flashtool.value == "rambo":
		                       		for name in os.listdir("/tmp/strange"):                                                          
			                               	if name.endswith(".nfi"):                                                              
	        		                               	os.remove("/tmp/strange/%s" % name)                                              
	                        	        command="cp %s /tmp/strange/%s.nfi" % (self.nfifile,self.nfiname)                                
					elif config.plugins.dbackup.flashtool.value == "recoverystick":
						if os.path.exists("/usr/lib/enigma2/python/Plugins/Bp/geminimain/lib/libgeminimain.so"):
							libgeminimain.setHWLock(1)
					   	os.system("umount /media/RECOVERY")
					   	os.system("umount /media/recovery")
					   	os.system("umount %s1" % self.device)
					   	os.system("umount %s1" % self.device)
					   	os.system("umount %s2" % self.device)
					   	os.system("umount %s2" % self.device)
					   	os.system("umount %s3" % self.device)
					   	os.system("umount %s3" % self.device)
					   	os.system("umount %s4" % self.device)
					   	os.system("umount %s4" % self.device)
						f=open("/proc/mounts","r")
						lll=f.readline()
						mp=[]
						while (lll):                                                                                                                        
							mp=lll.split()
#							print mp
							if os.path.islink(mp[0]):
			                       			path=os.readlink(mp[0])
			                       			path=path.replace("../../","/dev/")
			                       			if path.find(self.device) is not -1:
			     	                  			print "[dBackup] umounts also path: %s link: %s mount: %s" % (path,mp[0], mp[1])
							   		os.system("umount -f %s" % mp[1])
							lll=f.readline()
						f.close()
					   	# check if umounts failed
						f=open("/proc/mounts","r")
						mm=f.read()
						f.close()
						if mm.find(self.device) is not -1:
							self.session.open(MessageBox, _("umount failed, Sorry!"), MessageBox.TYPE_ERROR)
							if os.path.exists(dbackup_busy):
								os.remove(dbackup_busy)
							return
						else:
							self.session.open(MessageBox, running_string, MessageBox.TYPE_INFO, timeout=30)
						# let's partition and format now as FAT on 
						# a single primary partition to be sure that device is ONLY for recovery
	   					command ="#!/bin/sh\n"
					   	command +="fdisk %s << EOF\n" % self.device
						command +="d\n" 
						command +="1\n" 
						command +="d\n" 
						command +="2\n" 
						command +="d\n" 
						command +="3\n" 
						command +="d\n" 
						command +="n\n" 
						command +="p\n" 
						command +="1\n" 
						command +="\n" 
						command +="\n" 
						command +="w\n" 
					   	command +="EOF\n"
						command +="partprobe %s\n" % self.device  
				   		command +="fdisk %s << EOF\n" % self.device
					  	command +="t\n"
					  	command +="6\n"
					  	command +="a\n"
					  	command +="1\n"
					  	command +="w\n"
					   	command +="EOF\n"
						command +="partprobe %s\n" % self.device  
		                        	command +="mkdosfs -n RECOVERY %s1\n" % self.device
					   	command +="exit 0\n"
		                        	os.system(command)                                                            
						if os.path.exists("/usr/lib/enigma2/python/Plugins/Bp/geminimain/lib/libgeminimain.so"):
							libgeminimain.setHWLock(0)
		                        	modules_ipk="dreambox-dvb-modules"
		        	                os.system("mount %s1 /tmp/strange" % self.device)                                                            
		        	                # dirty check for read only filesystem
		       		 		os.system("mkdir /tmp/strange/sbin")
		       		 		if not os.path.exists("/tmp/strange/sbin"):
							if os.path.exists(dbackup_busy):
								os.remove(dbackup_busy)
							self.session.open(MessageBox, _("Sorry, %s device not mounted writeable") % self.device, MessageBox.TYPE_ERROR)
							return
		                       		for name in os.listdir("/tmp/strange"):                                                          
			                               	if name.endswith(".nfi"):                                                              
	        		                               	os.remove("/tmp/strange/%s" % name)                                              
		       		 		if not os.path.exists("/tmp/strange/sbin"):
			       		 		os.mkdir("/tmp/strange/sbin")
		       		 		if not os.path.exists("/tmp/strange/etc"):
			       		 		os.mkdir("/tmp/strange/etc")
		       		 		if not os.path.exists("/tmp/strange/tmp"):
			       		 		os.mkdir("/tmp/strange/tmp")
						if os.path.exists("/tmp/boot"):
							for file in os.listdir("/tmp/boot"):
  								os.remove("/tmp/boot/%s" % file)
  						else:
  							os.mkdir("/tmp/boot")
						if os.path.exists("/tmp/out") is True:
							os.remove("/tmp/out")
						os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s -O /tmp/out" % self.boxtype)
						if not os.path.exists("/tmp/out"):
							# use kernel from flash as we seem to be offline ...
		                        	        command="cp %s/nfiwrite /tmp/strange/sbin/nfiwrite; cp /boot/vmlinux*.gz /tmp/strange; cp /boot/bootlogo*elf* /tmp/strange; cp %s/recovery.jpg /tmp/strange; cp %s /tmp/strange/%s.nfi" % (dbackup_bin, dbackup_bin, self.nfifile,self.nfiname)                                
						else:
							# use kernel from OoZooN feed as we seem to be online ...
		                        	        command="cp %s/nfiwrite /tmp/strange/sbin/nfiwrite; cp /tmp/boot/vmlinux*.gz /tmp/strange; cp /boot/bootlogo*elf* /tmp/strange; cp %s/recovery.jpg /tmp/strange; cp %s /tmp/strange/%s.nfi" % (dbackup_bin, dbackup_bin, self.nfifile,self.nfiname)                                
					   		f = open("/tmp/out", "r")
							line = f.readline()
   							sp=[]
							sp2=[]
							while (line):
								line = f.readline()
								if line.find("kernel-image") is not -1:
#									print line
									sp = line.split("kernel-image")
									if len(sp) > 0:
#									       	print sp[1]
										sp2= sp[1].split(".ipk")
#								 	        print sp2[0]
										kernel="kernel-image%s.ipk" % sp2[0]
										print "[dBackup] found %s" % kernel
										if os.path.exists("/tmp/kernel.ipk"):
											os.remove("/tmp/kernel.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/kernel.ipk" % (self.boxtype,kernel))
										if os.path.exists("/tmp/kernel.ipk"):
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											os.system("cd /tmp; ar -x /tmp/kernel.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp")
											os.remove("/tmp/kernel.ipk")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
       								if line.find(modules_ipk) is not -1:
#     	  								print line
          								sp = line.split(modules_ipk)
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="%s%s.ipk" % (modules_ipk,sp2[0])
    									      	print "[dBackup] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img"):
	    									      		print "[dBackup] loop mounts %s ..." % modules
												os.system("mount -t squashfs -o ro,loop /tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img /media/union")
												os.system("mkdir -p /tmp/strange/lib/modules/3.2-%s/extra" % self.boxtype)
												os.system("cp /media/union/lib/modules/3.2-%s/extra/* /tmp/strange/lib/modules/3.2-%s/extra" % (self.boxtype,self.boxtype))
												os.system("umount /media/union")
												os.remove("/tmp/strange/squashfs-images/dreambox-dvb-modules-sqsh-img")
												os.rmdir("/tmp/strange/squashfs-images")
												os.rmdir("/tmp/strange/media/squashfs-images/dreambox-dvb-modules-sqsh-img")
												os.rmdir("/tmp/strange/media/squashfs-images")
												os.rmdir("/tmp/strange/media")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
       								if line.find("kernel-module-snd-pcm") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-pcm")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-pcm%s.ipk" % sp2[0]
    									      	print "[dBackup] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-snd-timer") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-timer")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-timer%s.ipk" % sp2[0]
    									      	print "[dBackup] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-snd-page-alloc") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-snd-page-alloc")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-snd-page-alloc%s.ipk" % sp2[0]
    									      	print "[dBackup] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
       								if line.find("kernel-module-stv0299") is not -1:
#     	  								print line
          								sp = line.split("kernel-module-stv0299")
									if len(sp) > 0:
#									       	print sp[1]
								          	sp2= sp[1].split(".ipk")
#								  	        print sp2[0]
								          	modules="kernel-module-stv0299%s.ipk" % sp2[0]
    									      	print "[dBackup] found %s ..." % modules
										if os.path.exists("/tmp/modules.ipk"):
											os.remove("/tmp/modules.ipk")
										os.system("wget -q http://www.oozoon-dreamboxupdate.de/opendreambox/2.0/experimental/%s/%s -O /tmp/modules.ipk" % (self.boxtype,modules))
										if os.path.exists("/tmp/modules.ipk"):
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
											os.system("cd /tmp; ar -x /tmp/modules.ipk")
											os.system("tar -xzf /tmp/data.tar.gz -C /tmp/strange")
											os.remove("/tmp/modules.ipk")
											if os.path.exists("/tmp/data.tar.gz"):
												os.remove("/tmp/data.tar.gz")
											if os.path.exists("/tmp/control.tar.gz"):
												os.remove("/tmp/control.tar.gz")
											if os.path.exists("/tmp/debian-binary"):
												os.remove("/tmp/debian-binary")
							f.close()
							os.system("depmod -b /tmp/strange")
						if os.path.exists("/tmp/strange/lib"):
							bootfile ="/boot/bootlogo-%s.elf.gz filename=/boot/recovery.jpg\n/boot/vmlinux-3.2-%s.gz console=ttyS0,115200 init=/sbin/nfiwrite rootdelay=10 root=LABEL=RECOVERY rootfstype=vfat rw\n" % (self.boxtype,self.boxtype)
	                        	        	a=open("/tmp/strange/autoexec_%s.bat" % self.boxtype, "w")
	                        	        	a.write(bootfile)
	                        	        	a.close()
	                        	        else:
							self.session.open(MessageBox, _("recovery stick creation failed, Sorry!"), MessageBox.TYPE_ERROR)
							if os.path.exists(dbackup_busy):
								os.remove(dbackup_busy)
							return
		                else:
					if os.path.exists(dbackup_busy):
						os.remove(dbackup_busy)
					self.session.open(MessageBox, _("Sorry, %s device not mounted") % self.device, MessageBox.TYPE_ERROR)
					return
	def doFlash(self,option):
		if option:
			print "[dBackup] is flashing now %s" % self.nfifile
			FlashingImage(self.nfifile)
		else:
			print "[dBackup] cancelled flashing %s" % self.nfifile

	def cancel(self):
		self.close(False)

	def backup(self):
		global dbackup_progress
		if os.path.exists(dbackup_backup):
 			print "[dBackup] found finished backup ..."
			dbackup_progress=0
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if os.path.exists(dbackup_busy):
				os.remove(dbackup_busy)
			if config.plugins.dbackup.transparency.value < config.av.osd_alpha.value:
				# reset needed
	                	f=open("/proc/stb/video/alpha","w")
        	        	f.write("%i" % (config.av.osd_alpha.value))
                		f.close()
			f=open(dbackup_backup)
			line=f.readline()
			f.close()
			os.remove(dbackup_backup)
			sp=[]
			sp=line.split("	")
			print sp
			length=len(sp)
			size=""
			image=""
			path=""
			if length > 0:
				size=sp[0].rstrip().lstrip()
				sp2=[]
				sp2=sp[length-1].split("/")
				print sp2
				length=len(sp2)
				if length > 0:
					image=sp2[length-1]
					path=line.replace(size,"").replace(image,"")
					image=image.replace(".nfi\n","")
					image=image.rstrip().lstrip()
			print "[dBackup] found backup %s" % line
			# checking for IO Errors
			l=""
			if os.path.exists(dbackup_log):
				b=open(dbackup_log)
				l=b.read()
				b.close()
			if l.find("Input/output err") is not -1:
				self.session.open(MessageBox,size+"B "+_("Flash Backup to %s\n\nfinished with imagename:\n\n%s.%s\n\nBUT it has I/O Errors") % (path,image,config.plugins.dbackup.backuptool.value),  MessageBox.TYPE_ERROR)                 
			else:
				self.session.open(MessageBox,size+"B "+_("Flash Backup to %s\n\nfinished with imagename:\n\n%s.%s") % (path,image,config.plugins.dbackup.backuptool.value),  MessageBox.TYPE_INFO)                 
		else:
	        	if os.path.exists(dbackup_busy):
				self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
			elif os.path.exists("/.bainfo"):
				self.session.open(MessageBox, barryallen_string, MessageBox.TYPE_ERROR)
			elif os.path.exists("/.lfinfo"):
				self.session.open(MessageBox, lowfat_string, MessageBox.TYPE_ERROR)
			else:
				if config.plugins.dbackup.flashtool.value == "rescue":
	               			self.askForBackupPath(config.plugins.dbackup.backuplocation.value)      
				else:
	               			self.session.openWithCallback(self.askForBackupPath,InputBox, title=backupdirectory_string, text="%s                                 " % config.plugins.dbackup.backuplocation.value, maxSize=48, type=Input.TEXT)

        def askForBackupPath(self,path):
	        self.imagetype=""                                       
	        self.creator=""               
           	if path is None:
              		self.session.open(MessageBox,_("nothing entered"),  MessageBox.TYPE_ERROR)                 
		elif path == "/data/.recovery":
			if not os.path.exists("/data"):
				os.mkdir("/data")
			os.system("mount /dev/mmcblk0p2 /data")
		        self.backupname="backup"
                	self.askForBackupName("backup")
           	else:
			if not os.path.exists("path"):
				os.system("ls %s" % path)
			sp=[]
			sp=path.split("/")
			print sp
			if len(sp) > 1:
				if sp[1] != "media" and sp[1] != "autofs":
 	             			self.session.open(MessageBox,mounted_string % path,  MessageBox.TYPE_ERROR)                 
					return
               		f=open("/proc/mounts", "r")
     	  		m = f.read()                                                    
       			f.close()
       		 	if m.find("/media/%s" % sp[2]) is -1 and m.find("/autofs/%s" % sp[2]) is -1 :
 	             		self.session.open(MessageBox,mounted_string % path,  MessageBox.TYPE_ERROR)                 
				return
			path=path.lstrip().rstrip("/").rstrip().replace(" ","")
	      		config.plugins.dbackup.backuplocation.value=path
	      		config.plugins.dbackup.backuplocation.save()
		        if not os.path.exists(config.plugins.dbackup.backuplocation.value):
		 		os.mkdir(config.plugins.dbackup.backuplocation.value,0777)
  			f=open("/proc/stb/info/model")
  			self.boxtype=f.read()
  			f.close()
  			self.boxtype=self.boxtype.replace("\n","").replace("\l","")
			name="dreambox-image"
			if os.path.exists("/etc/image-version"):
				f=open("/etc/image-version")
	 			line = f.readline()                                                    
        			while (line):                                             
        				line = f.readline()                                                 
        				if line.startswith("creator="):                                    
						name=line
        			f.close()                                                              
				name=name.replace("creator=","")
				sp=[]
				if len(name) > 0:
					sp=name.split(" ")
					if len(sp) > 0:
						name=sp[0]
						name=name.replace("\n","")
			self.creator=name.rstrip().lstrip()
			self.imagetype="exp"
			if name == "OoZooN" and os.path.exists("/etc/issue.net"):
				f=open("/etc/issue.net")
				i=f.read()
				f.close()
				if (i.find("xperimental") is -1) and (i.find("unstable") is -1):
					self.imagetype="rel"
			cdate=str(datetime.date.today())
			ctime=str(time.strftime("%H-%M"))
			suggested_backupname=name
			if config.plugins.dbackup.backupdeb.value:
				suggested_backupname=suggested_backupname+"-deb"
			if config.plugins.dbackup.backupboxtype.value:
				suggested_backupname=suggested_backupname+"-"+self.boxtype
			if config.plugins.dbackup.backupimagetype.value:
				suggested_backupname=suggested_backupname+"-"+self.imagetype
			if config.plugins.dbackup.backupdate.value:
				suggested_backupname=suggested_backupname+"-"+cdate
			if config.plugins.dbackup.backuptime.value:
				suggested_backupname=suggested_backupname+"-"+ctime
			if config.plugins.dbackup.flashtool.value == "rescue":
				suggested_backupname="backup"
			print "suggested backupname !%s!" % suggested_backupname
                	self.session.openWithCallback(self.askForBackupName,InputBox, title=backupimage_string, text=suggested_backupname, maxSize=40, type=Input.TEXT)

        def askForBackupName(self,name):
           if name is None:
		self.session.open(MessageBox,_("nothing entered"),  MessageBox.TYPE_ERROR)                 
           else:
		self.backupname=name.replace(" ","").replace("[","").replace("]","").replace(">","").replace("<","").replace("|","").rstrip().lstrip()
	      	if os.path.exists("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value,self.backupname,config.plugins.dbackup.backuptool.value)):
        		self.session.openWithCallback(self.confirmedBackup,MessageBox,"%s.%s" % (self.backupname,config.plugins.dbackup.backuptool.value) +"\n"+_("already exists,")+" "+_("overwrite ?"), MessageBox.TYPE_YESNO)
		else:
			self.confirmedBackup(True)

        def confirmedBackup(self,answer):
	      if answer:
	      	 	if os.path.exists("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value,self.backupname,config.plugins.dbackup.backuptool.value)):
	      			os.remove("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value,self.backupname,config.plugins.dbackup.backuptool.value))
	      	 	if os.path.exists("%s/%s.sig" % (config.plugins.dbackup.backuplocation.value,self.backupname)):
	      			os.remove("%s/%s.sig" % (config.plugins.dbackup.backuplocation.value,self.backupname))
                 	self.session.openWithCallback(self.startBackup,MessageBox, _("Press OK for starting backup to") + "\n\n%s.%s" % (self.backupname,config.plugins.dbackup.backuptool.value) + "\n\n" + _("Be patient, this takes 1-2 min ..."), MessageBox.TYPE_INFO)
	      else:
         		 self.session.open(MessageBox,_("not confirmed"),  MessageBox.TYPE_ERROR)                 
		
        def startBackup(self,answer):
		if answer:
			print "[dBackup] is doing backup now ..."
			self["logo"].instance.setPixmapFromFile("%s/ring.png" % dbackup_plugindir)
			self.doHide()
			self.backuptime=0
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if not os.path.exists("/var/lib/opkg/status"):
				self.TimerBackup_conn = self.TimerBackup.timeout.connect(self.backupFinishedCheck)
			else:
				self.TimerBackup.callback.append(self.backupFinishedCheck)
			self.TimerBackup.start(10000,True)                                 
			BackupImage(self.backupname,self.imagetype,self.creator)
		else:
	        	print "[dBackup] was not confirmed"
		 
        def backupFinishedCheck(self):
		global dbackup_progress
		self.backuptime=self.backuptime+10
		if not os.path.exists(dbackup_backup):
			# not finished - continue checking ...
			rsize=0
			working="%s/%s.%s" % (config.plugins.dbackup.backuplocation.value,self.backupname,config.plugins.dbackup.backuptool.value)
			print working
			if os.path.exists(working):
				rsize=os.path.getsize(working)
			total_size=rsize
			st = os.statvfs("/")                                                    
			rused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			used=rused
			if used < 0:
				used=0
			print "[dBackup] total size %d used %d\n" % (total_size,used)
			if total_size > 0:
# for xz
#	                	dbackup_progress=300*total_size/used
# for gz
	                	dbackup_progress=250*total_size/used
			else:
	                	dbackup_progress=self.backuptime/10
			self.slider.setValue(dbackup_progress)
 			print "[dBackup] checked if backup is finished after %d sec ..." % self.backuptime
			self.TimerBackup.start(10000,True)                                 
		else:
 			print "[dBackup] found finished backup ..."
			dbackup_progress=0
	                self.slider.setValue(0)
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if os.path.exists(dbackup_busy):
				os.remove(dbackup_busy)
			f=open(dbackup_backup)
			line=f.readline()
			f.close()
			os.remove(dbackup_backup)
			sp=[]
			sp=line.split("	")
			print sp
			length=len(sp)
			size=""
			image=""
			path=""
			if length > 0:
				size=sp[0].rstrip().lstrip()
				sp2=[]
				sp2=sp[length-1].split("/")
				print sp2
				length=len(sp2)
				if length > 0:
					image=sp2[length-1]
					path=line.replace(size,"").replace(image,"").lstrip().rstrip()
					image=image.replace(".tar.gz\n","").replace(".tar.xz\n","").replace(".tar.bz2\n","").replace(".tar\n","")
				else:
					image=""
			if config.plugins.dbackup.transparency.value < config.av.osd_alpha.value:
				# reset needed
	                	f=open("/proc/stb/video/alpha","w")
        	       		f.write("%i" % (config.av.osd_alpha.value))
                		f.close()
				self.DimmingTimer = eTimer()
				self.DimmingTimer.stop()                                           
			print "[dBackup] found backup %s" % line
			# checking for IO Errors
			l=""
			if os.path.exists(dbackup_log):
				b=open(dbackup_log)
				l=b.read()
				b.close()
			if config.plugins.dbackup.flashtool.value == "rescue":
				os.system("umount /data")
			try:
				if l.find("Input/output err") is not -1:
					self.session.open(MessageBox,"%sB " % (size) +_("Flash Backup to %s\n\nfinished with imagename:\n\n%s.%s\n\nBUT it has I/O Errors") % (path,image,config.plugins.dbackup.backuptool.value),  MessageBox.TYPE_ERROR)                 
				else:
					self.session.open(MessageBox,"%sB " % (size) +_("Flash Backup to %s\n\nfinished with imagename:\n\n%s.%s") % (path,image,config.plugins.dbackup.backuptool.value),  MessageBox.TYPE_INFO)                 
			except:
				# why crashes even this
#				self.session.open(MessageBox,_("Flash Backup to %s finished with imagename:\n\n%s.%s") % (path,image,config.plugins.dbackup.backuptool.value),  MessageBox.TYPE_INFO)                 
				self.session.open(MessageBox,_("Flash Backup finished"),  MessageBox.TYPE_INFO)                 

	def config(self):
	        if os.path.exists(dbackup_busy):
			self.session.open(MessageBox, running_string, MessageBox.TYPE_ERROR)
		else:
        	 	self.session.open(dBackupConfiguration)

def startdBackup(session, **kwargs):
       	session.open(dBackup)   

def autostart(reason,**kwargs):
        if kwargs.has_key("session") and reason == 0:           
		session = kwargs["session"]                       
		print "[dBackup] autostart"
		if os.path.exists(dbackup_busy):
			os.remove(dbackup_busy)
		if os.path.exists("/dbackup.new"):
			shutil.rmtree("/dbackup.new",True)
		if os.path.exists("/dbackup.old"):
			shutil.rmtree("/dbackup.old",True)
		if config.plugins.dbackup.flashtool.value == "rescue":
			config.plugins.dbackup.backuplocation.value = "/data/.recovery"
			config.plugins.dbackup.backuptool.value = "tar.gz"
			config.plugins.dbackup.backuplocation.save()
			config.plugins.dbackup.backuptool.save()

def sessionstart(reason, **kwargs):                                               
        if reason == 0 and "session" in kwargs:                                                        
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/WebChilds/Toplevel.py"):
                       	from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
                       	addExternalChild( ("dbackup", wFlash(), "dBackup", "1", True) )          
                else:                                                                                  
			print "[dBackup] Webif not found"

def main(session,**kwargs):                                                     
     session.open(dBackup)       
def Plugins(**kwargs):
     if config.plugins.dbackup.showing.value=="plugin":
	 	return [PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_PLUGINMENU, icon="dbackup.png", fnc=main),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where=PluginDescriptor.WHERE_MENU, fnc=mainconf),
       			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)]
     elif config.plugins.dbackup.showing.value=="extension":
		return [PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_EXTENSIONSMENU, icon="g3icon_dbackup.png", fnc=main),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where=PluginDescriptor.WHERE_MENU, fnc=mainconf),
       			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)]
     elif config.plugins.dbackup.showing.value=="both":
	    	return [PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_PLUGINMENU, icon="dbackup.png", fnc=main),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_EXTENSIONSMENU, icon="g3icon_dbackup.png", fnc=main),
       			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)]
     elif config.plugins.dbackup.showing.value=="all":
	    	return [PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_PLUGINMENU, icon="dbackup.png", fnc=main),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where=PluginDescriptor.WHERE_MENU, fnc=mainconf),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where = PluginDescriptor.WHERE_EXTENSIONSMENU, icon="g3icon_dbackup.png", fnc=main),
       			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)]
     else: # classic in setup menu ...
		return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
			PluginDescriptor(name=backup_string+" & "+flashing_string, description=backup_string+" & "+flashing_string, where=PluginDescriptor.WHERE_MENU, fnc=mainconf),
       			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart, needsRestart=False)]

def mainconf(menuid):
    if menuid != "setup":                                                  
        return [ ]                                                     
    return [(backup_string+" & "+flashing_string, startdBackup, "dbackup", None)]    

###############################################################################
# dBackup Webinterface by gutemine
###############################################################################

class wFlash(resource.Resource):

	def render_GET(self, req):
		global dbackup_progress
		file = req.args.get("file",None)
		directory = req.args.get("directory",None)
		command = req.args.get("command",None)
		print "[dBackup] received %s %s %s" % (command,directory,file)
		req.setResponseCode(http.OK)
		req.setHeader('Content-type', 'text/html')
                req.setHeader('charset', 'UTF-8')
	        if not config.plugins.dbackup.webinterface.value:
			return header_string+nowebif_string
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/dbackup.png") is False:
			os.symlink("%s/dbackup.png" % dbackup_plugindir,"/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/dbackup.png")
		if os.path.exists("/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/ring.png") is False:
			os.symlink("%s/ring.png" % dbackup_plugindir,"/usr/lib/enigma2/python/Plugins/Extensions/WebInterface/web-data/img/ring.png")
		if os.path.exists(dbackup_busy):
			dbackup_backuping_progress  =""
			dbackup_backuping_progress += header_string
			dbackup_backuping_progress += "<br>%s<br><br>" % running_string
			dbackup_backuping_progress +="<br><img src=\"/web-data/img/ring.png\" alt=\"%s ...\"/><br><br>" % (backup_string)
			if dbackup_progress > 0:
				dbackup_backuping_progress +="<div style=\"background-color:yellow;width:%dpx;height:20px;border:1px solid #000\"></div> " % (dbackup_progress)
			dbackup_backuping_progress +="<br><form method=\"GET\">"
			dbackup_backuping_progress +="<input name=\"command\" type=\"submit\" size=\"100px\" title=\"%s\" value=\"%s\">" % (refresh_string,"Refresh")
			dbackup_backuping_progress +="</form>"                        
			return header_string+dbackup_backuping_progress
		if command is None or command[0] == "Refresh":
			b=open("/proc/stb/info/model","r")
			dreambox=b.read().rstrip("\n")
			b.close()
			htmlnfi=""
			htmlnfi += "<option value=\"%s\" class=\"black\">%s</option>\n" % ("recovery",_("Recovery Image from Feed"))
			entries=os.listdir("/tmp")
	 		for name in sorted(entries):                          
				if (name.endswith(".tar.gz") or name.endswith("tar.xz") or name.endswith("tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
       			       		name2=name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar","")                        
					htmlnfi += "<option value=\"/tmp/%s\" class=\"black\">%s</option>\n" % (name,name2)
#			if not config.plugins.dbackup.backuplocation.value.startswith("/media/net"):
			if os.path.exists(config.plugins.dbackup.backuplocation.value):
				entries=os.listdir(config.plugins.dbackup.backuplocation.value)
       				for name in sorted(entries):                          
					if (name.endswith(".tar.gz") or name.endswith("tar.xz") or name.endswith("tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
				       		name2=name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar","")                        
						htmlnfi += "<option value=\"%s/%s\" class=\"black\">%s</option>\n" % (config.plugins.dbackup.backuplocation.value,name,name2)
			entries=os.listdir("/media")
       			for directory in sorted(entries):                          
				if os.path.exists("/media/%s" % directory) and os.path.isdir("/media/%s" % directory) and not directory.endswith("net") and not directory.endswith("hdd"):
       					for name in os.listdir("/media/%s" % directory):                          
						if (name.endswith(".tar.gz") or name.endswith("tar.xz") or name.endswith("tar.bz2") or name.endswith(".tar")) and not name.startswith("enigma2settings") and not name.endswith("enigma2settingsbackup.tar.gz"):
		       			       		name2=name.replace(".tar.gz","").replace(".tar.xz","").replace(".tar.bz2","").replace(".tar","")                        
							htmlnfi += "<option value=\"%s/%s\" class=\"black\">%s</option>\n" % (directory,name,name2)
  			f=open("/proc/stb/info/model")
  			self.boxtype=f.read()
  			f.close()
  			self.boxtype=self.boxtype.replace("\n","").replace("\l","")
			name="dreambox-image"
			if os.path.exists("/etc/image-version"):
				f=open("/etc/image-version")
	 			line = f.readline()                                                    
        			while (line):                                             
        				line = f.readline()                                                 
        				if line.startswith("creator="):                                    
						name=line
        			f.close()                                                              
				name=name.replace("creator=","")
				sp=[]
				if len(name) > 0:
					sp=name.split(" ")
					if len(sp) > 0:
						name=sp[0]
						name=name.replace("\n","")
			self.creator=name.rstrip().lstrip()
			self.imagetype="exp"
			if name == "OoZooN" and os.path.exists("/etc/issue.net"):
				f=open("/etc/issue.net")
				i=f.read()
				f.close()
				if (i.find("xperimental") is -1) and (i.find("unstable") is -1):
					self.imagetype="rel"
			cdate=str(datetime.date.today())
			ctime=str(time.strftime("%H-%M"))
			suggested_backupname=name
			if config.plugins.dbackup.backupdeb.value:
				suggested_backupname=suggested_backupname+"-deb"
			if config.plugins.dbackup.backupboxtype.value:
				suggested_backupname=suggested_backupname+"-"+self.boxtype
			if config.plugins.dbackup.backupimagetype.value:
				suggested_backupname=suggested_backupname+"-"+self.imagetype
			if config.plugins.dbackup.backupdate.value:
				suggested_backupname=suggested_backupname+"-"+cdate
			if config.plugins.dbackup.backuptime.value:
				suggested_backupname=suggested_backupname+"-"+ctime
			if config.plugins.dbackup.flashtool.value == "rescue":
				suggested_backupname="backup"
			print "suggested backupname !%s!" % suggested_backupname
		 	return """
				<html>
				%s<br>
				<u>%s</u><br><br>
				%s:<br><br>
                                %s<hr>
				%s @ Dreambox<br>
				<form method="GET">
                	       	<select name="file">%s
                                <input type="reset" size="100px"> 
                		<input name="command" type="submit" size=="100px" title=\"%s\" value="%s"> 
				</select>
                               	</form>                             
				<img src="/web-data/img/dbackup.png" alt="%s ..."/><br><br>
                               	<hr>
				%s & %s @ Dreambox<br>
				<form method="GET">
 				<input name="directory" type="text" size="48" maxlength="48" value="%s">
 				<input name="file" type="text" size="48" maxlength="48" value="%s">
                                <input type="reset" size="100px"> 
                		<input name="command" type="submit" size=="100px" title=\"%s\" value="%s"> 
				</select>
                               	</form>                             
				<img src="/web-data/img/ring.png" alt="%s ..."/><br><br>
                               	<hr>
    			""" % (header_string,plugin_string,info_header,disclaimer_wstring,fileupload_string, htmlnfi,flashing_string, "Flashing",flashing_string,backupdirectory_string,backupimage_string,config.plugins.dbackup.backuplocation.value,suggested_backupname,backup_string,"Backup",backup_string)
		else:
		   if command[0]=="Flashing":
			k=open("/proc/cmdline","r")       
			cmd=k.read()     
			k.close()                
			if os.path.exists("/.bainfo"):
				return header_string+noflashing_string
			elif os.path.exists("/.lfinfo"):
				return header_string+noflashing_string
			elif cmd.find("root=/dev/mmcblk0") is -1:
				return header_string+noflashing_string
		        # file command is received and we are in Flash - let the fun begin ...
			self.nfifile=file[0]
			if os.path.exists(self.nfifile):
		 		if self.nfifile.endswith(".tar.gz"):
					print "[dBackup] is flashing now %s" % self.nfifile
					FlashingImage(self.nfifile)
					return dbackup_flashing
		 		elif self.nfifile.endswith(".tar.xz"):
		 			if os.path.exists("%s/bin/xz" % dbackup_plugindir) or os.path.exists("/usr/bin/xz"):
						print "[dBackup] is flashing now %s" % self.nfifile
						FlashingImage(self.nfifile)
						return dbackup_flashing
					else:
						print "[dBackup] xz binary missing"
 						return header_string+noxz_string
		 		elif self.nfifile.endswith(".tar.bz2"):
					print "[dBackup] is flashing now %s" % self.nfifile
					FlashingImage(self.nfifile)
					return dbackup_flashing
		 		elif self.nfifile.endswith(".tar"):
					print "[dBackup] is flashing now %s" % self.nfifile
					FlashingImage(self.nfifile)
					return dbackup_flashing
				else:
					print "[dBackup] wrong filename"
 					return header_string+notar_string
		 	else:
	 			if self.nfifile == "recovery":
					print "[dBackup] is flashing now %s" % self.nfifile
					FlashingImage(self.nfifile)
					return dbackup_flashing
				else:
					print "[dBackup] filename not found"
					return header_string+notar_string

		   elif command[0]=="Backup":
		        if os.path.exists("/.bainfo"):
				return header_string+" "+barryallen_string+", "+dbackup_backbutton
		        elif os.path.exists("/.lfinfo"):
				return header_string+" "+lowfat_string+", "+dbackup_backbutton
			if config.plugins.dbackup.flashtool.value == "rescue":
				path="/data/.recovery"
				if not os.path.exists("/data"):
					os.mkdir("/data")
				os.system("mount /dev/mmcblk0p2 /data")
				self.backupname="backup"
				if os.path.exists("/data/.recovery/backup.tar.gz"):
					os.remove("/data/.recovery/backup.tar.gz")
			else:
				self.backupname=file[0].replace(" ","").replace("[","").replace("]","").replace(">","").replace("<","").replace("|","").rstrip().lstrip()
				path=directory[0]
			if config.plugins.dbackup.flashtool.value != "rescue":
				if not os.path.exists("path"):
					os.system("ls %s" % path)
				sp=[]
				sp=path.split("/")
				print sp
				if len(sp) > 1:
					if sp[1] != "media" and sp[1] != "autofs":
						return header_string+" "+mounted_string % path +", "+dbackup_backbutton
	               		f=open("/proc/mounts", "r")
     		  		m = f.read()                                                    
       				f.close()
	       		 	if m.find("/media/%s" % sp[2]) is -1 and m.find("/autofs/%s" % sp[2]) is -1 :
					return header_string+" "+mounted_string % path +", "+dbackup_backbutton
			path=path.lstrip().rstrip("/").rstrip().replace(" ","")
	      		config.plugins.dbackup.backuplocation.value=path
	      		config.plugins.dbackup.backuplocation.save()
		        if not os.path.exists(config.plugins.dbackup.backuplocation.value):
		 		os.mkdir(config.plugins.dbackup.backuplocation.value,0777)
			if os.path.exists("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value,self.backupname,config.plugins.dbackup.backuptool.value)):
				print "[dBackup] filename already exists"
				return header_string+self.backupname+"."+config.plugins.dbackup.backuptool.value+" "+_("already exists,")+" "+dbackup_backbutton
			else:
		 		if self.backupname.endswith(".tar") or self.backupname.endswith(".tar.gz") or self.backupname.endswith(".tar.bz2") or self.backupname.endswith(".tar.xz") or len(self.backupname) < 1:
					print "[dBackup] filename with .tar.*"
 					return header_string+notar_string+", "+dbackup_backbutton
				elif self.backupname.find(" ") is not -1:
					print "[dBackup] filename with blank"
 					return header_string+notar_string+", "+dbackup_backbutton
				else:
					# backupfile request
					self.backuptime=0
					self.TimerBackup = eTimer()                                       
					self.TimerBackup.stop()                                           
					if not os.path.exists("/var/lib/opkg/status"):
						self.TimerBackup_conn = self.TimerBackup.timeout.connect(self.backupFinishedCheck)
					else:
						self.TimerBackup.callback.append(self.backupFinishedCheck)
					self.TimerBackup.start(10000,True)                                 
                 			BackupImage(self.backupname,self.imagetype,self.creator)
					return header_string+dbackup_backuping
		   else:
			print "[dBackup] unknown command"
              		return header_string+_("nothing entered")                 

        def backupFinishedCheck(self):
		global dbackup_progress
		self.backuptime=self.backuptime+10
		if not os.path.exists(dbackup_backup):
			# not finished - continue checking ...
			rsize=0
			
			if os.path.exists("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value, self.backupname, config.plugins.dbackup.backuptool.value)):
				rsize=os.path.getsize("%s/%s.%s" % (config.plugins.dbackup.backuplocation.value, self.backupname, config.plugins.dbackup.backuptool.value))
			total_size=rsize
			st = os.statvfs("/")                                                    
			rused = (st.f_blocks - st.f_bfree) * st.f_frsize        
			used=rused
			if used < 0:
				used=0
			print "[dBackup] total size %d used %d\n" % (total_size,used)
			if total_size > 0:
# for xz
#	                	dbackup_progress=300*total_size/used
# for gz
	                	dbackup_progress=250*total_size/used
			else:
	                	dbackup_progress=self.backuptime/10
 			print "[dBackup] checked if backup is finished ..."
			self.TimerBackup.start(10000,True)                                 
		else:
 			print "[dBackup] found finished backup ..."
			dbackup_progress=0
			self.TimerBackup = eTimer()                                       
			self.TimerBackup.stop()                                           
			if os.path.exists(dbackup_busy):
				os.remove(dbackup_busy)
			f=open(dbackup_backup)
			line=f.readline()
			f.close()
			os.remove(dbackup_backup)
			sp=[]
			sp=line.split("	")
			print sp
			length=len(sp)
			size=""
			image=""
			path=""
			if length > 0:
				size=sp[0].rstrip().lstrip()
				sp2=[]
				sp2=sp[length-1].split("/")
				print sp2
				length=len(sp2)
				if length > 0:
					image=sp2[length-1]
					path=line.replace(size,"").replace(image,"")
					image=image.replace(".tar.gz\n","").replace(".tar.xz\n","").replace(".tar.bz2\n","").replace(".tar\n","")
					image=image.rstrip().lstrip()
			print "[dBackup] found backup %s" % line
			print "[dBackup] finished webif backup"
			
class FlashingImage(Screen):                                                      
        def __init__(self,flashimage):            
        	print "[dBackup] does flashing %s" % flashimage
                open(dbackup_busy, 'a').close()
		if config.plugins.dbackup.flashtool.value == "rescue":
			command  = "#!/bin/sh -x\n"
			command += "echo rescue > /proc/stb/fp/boot_mode\n"
			command += "shutdown -r now\n"
			command += "exit 0\n"
			b=open(dbackup_script,"w")
			b.write(command)
			b.close()
			os.system("chmod 755 %s" % dbackup_script)
			print "[dBackup] %s created and is now booting to recue mode\n" % (dbackup_script)
			os.system("/sbin/start-stop-daemon -S -b -n dbackup.sh -x %s" % dbackup_script)
		elif config.plugins.dbackup.flashtool.value == "recovery":
			command  = "#!/bin/sh -x\n"
			command += "mkdir /tmp/recovery\n"
			command += "mount -t ext4 /dev/mmcblk0p2 /tmp/recovery\n"
			command += "cp %s /tmp/recovery/.recovery/backup.tar.gz\n" % flashimage
			command += "umount /tmp/recovery\n"
			command += "systemctl stop enigma2\n"
			command += "sleep 5\n"
			command += "shutdown -h now\n"
			command += "exit 0\n"
			b=open(dbackup_script,"w")
			b.write(command)
			b.close()
			os.system("chmod 755 %s" % dbackup_script)
			print "[dBackup] %s created and is now flashing %s\n" % (dbackup_script,flashimage)
			os.system("/sbin/start-stop-daemon -S -b -n dbackup.sh -x %s" % dbackup_script)
		elif config.plugins.dbackup.flashtool.value == "usb":
	        	print "[dBackup] recovery usb stick is not yet supported"
		else:
			if os.path.exists("/dbackup.new"):
				shutil.rmtree("/dbackup.new",True)
			if not os.path.exists("/dbackup.new"):
				os.mkdir("/dbackup.new")
			if os.path.exists("/dbackup.old"):
				shutil.rmtree("/dbackup.old",True)
			if not os.path.exists("/dbackup.old"):
				os.mkdir("/dbackup.old")
			command  = "#!/bin/sh -x\n"
			if flashimage == "recovery":
				# default values from DMM recovery Image
				url="http://dreamboxupdate.com/download/recovery/dm7080/release"
				img="dreambox-image-dm7080.tar.xz"
				os.mkdir ("/tmp/recovery")
			        os.system("mount -t ext4 /dev/mmcblk0p2 /tmp/recovery")
				if os.path.exists("/tmp/recover/.recovery/recovery"):
					r=open("/tmp/recover/.recovery/recovery")
			                line = r.readline()                                                                                                                  
         		       		while (line):                                                                                                                        
        					line = f.readline()                                                                                                          
                        			if line.startswith("BASE_URI="):                                                                                                  
							url=line.replace("BASE_URI=","")
                	        		if line.startswith("FILENAME="):                                                                                                  
							img=line.replace("FILENAME=","")
					r.close()
				recovery_image="%s/%s" % (url,img)
				flashimage="%s/%s" % (config.plugins.dbackup.backuplocation.value,img)
		        	print "[dBackup] downloads %s to %s" % (recovery_image,flashimage)
				os.system("umount /tmp/recovery")
				command += "wget %s -O %s\n" % (recovery_image,flashimage)
			if flashimage.endswith(".tar.gz"):
				if os.path.exists("%s/bin/pigz" % dbackup_plugindir):
					command += "%s/bin/pigz -d -f -k %s\n" % (dbackup_plugindir,flashimage)
					tarimage=flashimage.replace("tar.gz","tar")
					if config.plugins.dbackup.verbose.value:
						command += "tar -xvf %s -C /dbackup.new\n" % (tarimage)
					else:
						command += "tar -xf %s -C /dbackup.new\n" % (tarimage)
#					if os.path.exists(tarimage):
#						os.remove(tarimage)
				else:
					if config.plugins.dbackup.verbose.value:
						command += "tar -xvzf %s -C /dbackup.new\n" % (flashimage)
					else:
						command += "tar -xzf %s -C /dbackup.new\n" % (flashimage)
			elif flashimage.endswith(".tar.xz"):
#				if os.path.exists("%s/bin/xz" % dbackup_plugindir):
				if False:
					command += "%s/bin/xz -d -c %s > %s\n" % (dbackup_plugindir,flashimage,flashimage.replace("tar.xz","tar"))
					tarimage=flashimage.replace("tar.xz","tar")
					if config.plugins.dbackup.verbose.value:
						command += "tar -xvf %s -C /dbackup.new\n" % (tarimage)
					else:
						command += "tar -xf %s -C /dbackup.new\n" % (tarimage)
					if os.path.exists(tarimage):
						os.remove(tarimage)
				else:
					if config.plugins.dbackup.verbose.value:
						command += "tar -xvJf %s -C /dbackup.new\n" % (flashimage)
					else:
						command += "tar -xJf %s -C /dbackup.new\n" % (flashimage)
			elif flashimage.endswith(".tar.bz2"):
				if config.plugins.dbackup.verbose.value:
					command += "tar -xvjf %s -C /dbackup.new\n" % (flashimage)
				else:
					command += "tar -xjf %s -C /dbackup.new\n" % (flashimage)
			else:
				tarimage=flashimage
				if config.plugins.dbackup.verbose.value:
					command += "tar -xvf %s -C /dbackup.new\n" % (tarimage)
				else:
					command += "tar -xf %s -C /dbackup.new\n" % (tarimage)

			if config.plugins.dbackup.kernelflash.value:
				command += "flash-kernel -a /dbackup.new/usr/share/fastboot/lcd_anim.bin -m 0x10000000 -o A  /dbackup.new/boot/vmlinux.bin*\n"
	
			command += "cp %s/bin/swaproot /tmp/swaproot\n" % dbackup_plugindir
			command += "chmod 755 /tmp/swaproot\n"
			command += "/tmp/swaproot %s\n" % config.plugins.dbackup.delay.value
			command += "exit 0\n"
			b=open(dbackup_script,"w")
			b.write(command)
			b.close()
			os.system("chmod 755 %s" % dbackup_script)
			print "[dBackup] %s created and is now flashing %s\n" % (dbackup_script,flashimage)
			os.system("/sbin/start-stop-daemon -S -b -n dbackup.sh -x %s" % dbackup_script)

class BackupImage(Screen):                                                      
        def __init__(self,backupname,imagetype,creator):            
        	print "[dBackup] does backup"
                open(dbackup_busy, 'a').close()
	        self.backupname=backupname               
	        self.imagetype=imagetype                                        
	        self.creator=creator                 
		exclude=""
		if config.plugins.dbackup.epgdb.value:
			exclude +=" --exclude=epg.db"	
		if config.plugins.dbackup.timers.value:
			exclude +=" --exclude=timers.xml"	
		if config.plugins.dbackup.settings.value:
			exclude +=" --exclude=settings"	
		f=open("/proc/stb/info/model")
		self.boxtype=f.read()
		f.close()
		self.boxtype=self.boxtype.replace("\n","").replace("\l","")
        	for name in os.listdir("/lib/modules"):                          
			self.kernel = name
		self.kernel = self.kernel.replace("\n","").replace("\l","").replace("\0","")
		print "[dBackup] boxtype %s kernel %s" % (self.boxtype,self.kernel)
		# don't backup left overs from flashing ...
		if os.path.exists("/dbackup.new"):
			shutil.rmtree("/dbackup.new",True)
		if not os.path.exists("/dbackup.new"):
			os.mkdir("/dbackup.new")
		
		# here comes the fun ...
		
		command  = "#!/bin/sh -x\n"
		command += "exec > %s 2>&1\n" % dbackup_log
		command +="cat %s\n" % dbackup_backupscript
		command +="df -h\n"
		if os.path.exists("/etc/init.d/openvpn"):
			command +="/etc/init.d/openvpn stop\n"
		if config.plugins.dbackup.aptclean.value:
			command += "apt-get clean\n"
			
		# make root filesystem ...
			
		command +="umount /tmp/root\n"
		command +="rmdir /tmp/root\n"
		command +="mkdir /tmp/root\n"
		command +="mount -o bind / /tmp/root\n"
		if config.plugins.dbackup.picons.value and os.path.exists("/usr/share/enigma2/picon"):
			command +="mount -t tmpfs tmpfs /tmp/root/usr/share/enigma2/picon\n"
		target ="%s/%s.tar" % (config.plugins.dbackup.backuplocation.value, backupname)
		# tar.gz is now default
		if config.plugins.dbackup.backuptool.value == "tar.gz":
			if os.path.exists("%s/bin/pigz" % dbackup_plugindir):
				if config.plugins.dbackup.verbose.value:
					command +="%s/tar -cvf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				else:
					command +="%s/tar -cf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				command +="%s/bin/pigz %s\n" % (dbackup_plugindir, target)
			else:
				if config.plugins.dbackup.verbose.value:
					command +="%s/tar -cvzf %s.gz %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				else:
					command +="%s/tar -czf %s.gz %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
		elif config.plugins.dbackup.backuptool.value == "tar.xz":
			if os.path.exists("%s/bin/xz" % dbackup_plugindir):
				if config.plugins.dbackup.verbose.value:
					command +="%s/tar -cvf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				else:
					command +="%s/tar -cf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				command +="%s/bin/xz < %s > %s.xz\n" % (dbackup_plugindir,target,target)
				command +="rm %s\n" % (target)
			else:
				if config.plugins.dbackup.verbose.value:
					command +="%s/tar -cvJf %s.xz %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
				else:
					command +="%s/tar -cJf %s.xz %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
		elif config.plugins.dbackup.backuptool.value == "tar.bz2":
			if config.plugins.dbackup.verbose.value:
				command +="%s/tar -cvjf %s.bz2 %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
			else:
				command +="%s/tar -cjf %s.bz2 %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
		else:
			if config.plugins.dbackup.verbose.value:
				command +="%s/tar -cvf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
			else:
				command +="%s/tar -cf %s %s -C /tmp/root .\n" % (dbackup_bin, target, exclude)
		if config.plugins.dbackup.picons.value:
			command +="umount /tmp/root/usr/share/enigma2/picon\n"
		command +="umount /tmp/root\n"
		command +="rmdir /tmp/root\n"

		if os.path.exists("/etc/init.d/openvpn"):
			command +="/etc/init.d/openvpn start\n"

		command +="chmod 777 %s.*\n" % (target)
		command +="ls -alh %s.*\n" % (target)
		command +="du -h %s.* > %s\n" % (target,dbackup_backup)
		command +="df -h\n"
		command +="rm %s\n" % dbackup_busy
		command +="exit 0\n"
		print command
		b=open(dbackup_backupscript,"w")
		b.write(command)
		b.close()
		os.chmod(dbackup_backupscript, 0777)
                self.container = eConsoleAppContainer()                                                        
		start_cmd="/sbin/start-stop-daemon -K -n dbackup.sh -s 9; /sbin/start-stop-daemon -S -b -n dbackup.sh -x %s" % (dbackup_backupscript)
		if config.plugins.dbackup.exectool.value == "daemon":
			print "[dBackup] daemon %s" % dbackup_backupscript
	               	self.container.execute(dbackup_backupscript)                                                           
		elif config.plugins.dbackup.exectool.value == "system":
			print "[dBackup] system %s" % start_cmd
			os.system(start_cmd)
		if config.plugins.dbackup.exectool.value == "container":
			print "[dBackup] container %s" % start_cmd
	               	self.container.execute(start_cmd)                                                           

###############################################################################
# dBackup Check by gutemine
###############################################################################

class dBackupChecking(Screen):
    skin = """
        <screen position="center,80" size="680,440" title="choose NAND Flash Check" >
        <widget name="menu" position="10,60" size="660,370" scrollbarMode="showOnDemand" />
	<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
	<widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
	<widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        </screen>"""
        
    def __init__(self, session, args = 0):
        self.skin = dBackupChecking.skin
        self.session = session
        Screen.__init__(self, session)
        self.menu = args
        self.onShown.append(self.setWindowTitle)
        flashchecklist = []
	self["buttonred"] = Label(_("Cancel"))
	self["buttonyellow"] = Label(info_header)
	self["buttongreen"] = Label(_("OK"))
	self["buttonblue"] = Label(_("About"))
	self["logo"] = Pixmap()
        if not os.path.exists("/data"):
		os.mkdir("/data")
       	flashchecklist.append((_("check root"), "/sbin/fsck.ext4 -n  -f -v /dev/mmcblk0p1"))
       	flashchecklist.append((_("check & repair recovery"), "/sbin/fsck.ext4 -p -f -v /dev/mmcblk0p2")) 
	if os.path.exists("/sbin/badblocks"):
        	flashchecklist.append((_("badblocks recovery > 1min"), "/sbin/fsck.ext4 -p -f -c -v /dev/mmcblk0p2")) 
	else:
        	flashchecklist.append((_("no badblocks binary - get e2fsprogs"), "none")) 
       	flashchecklist.append((_("clean apt cache"), "apt-get -v; apt-get clean")) 
       	flashchecklist.append((_("check defragmentation root"), "ln -sfn /dev/mmcblk0p1 /dev/root; %s/bin/e4defrag -c /dev/root" % dbackup_plugindir)) 
       	flashchecklist.append((_("defragment root"), "ln -sfn /dev/mmcblk0p1 /dev/root; %s/bin/e4defrag /dev/root" % dbackup_plugindir)) 
       	flashchecklist.append((_("check defragmentation recovery"), "mount /dev/mmcblk0p2 /data; %s/bin/e4defrag -c /dev/mmcblk0p2; umount /data" % dbackup_plugindir)) 
       	flashchecklist.append((_("defragment recovery"), "mount /dev/mmcblk0p2 /data; %s/bin/e4defrag /dev/mmcblk0p2; umount /data" % dbackup_plugindir)) 
	m=open("/proc/mounts")
	mounts=m.read()
	m.close()
	if mounts.find("/media/hdd ext4") is not -1:
	       	flashchecklist.append((_("check defragmentation Harddisk"), "%s/bin/e4defrag -c /media/hdd" % dbackup_plugindir)) 
	       	flashchecklist.append((_("defragment Harddisk"), "%s/bin/e4defrag -v /media>/hdd" % dbackup_plugindir)) 
	        
        self["menu"] = MenuList(flashchecklist)
	self["setupActions"] = ActionMap([ "ColorActions", "SetupActions" ],
		{
		"ok": self.go,
		"green": self.go,
		"red": self.close,
		"yellow": self.legend,
		"blue": self.about,
		"cancel": self.close,
		})
        
    def go(self):
        checking = self["menu"].l.getCurrentSelection()[0]
        command = self["menu"].l.getCurrentSelection()[1]
	print checking, command
        if command is not None and command != "none":
       		self.session.open(Console, checking,[ (command) ])

    def setWindowTitle(self):
	self["logo"].instance.setPixmapFromFile("%s/dbackup.png" % dbackup_plugindir)
	self.setTitle(backup_string+" & "+flashing_string+" V%s " % dbackup_version + checking_string)

    def legend(self):
        title=_("If you install e2fsprogs the badblocks binary will allow to check and mark also bad blocks")
        self.session.open(MessageBox, title,  MessageBox.TYPE_INFO)

    def about(self):
       	self.session.open(dBackupAbout)

class dBackupConfiguration(Screen, ConfigListScreen):
    skin = """
        <screen position="center,80" size="680,540" title="dBackup Configuration" >
	<widget name="logo" position="10,10" size="100,40" transparent="1" alphatest="on" />
        <widget name="config" position="10,60" size="660,450" scrollbarMode="showOnDemand" />
        <widget name="buttonred" position="120,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttongreen" position="260,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonyellow" position="400,10" size="130,40" backgroundColor="yellow" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttonblue" position="540,10" size="130,40" backgroundColor="blue" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        </screen>"""

    def __init__(self, session, args = 0):
	Screen.__init__(self, session)

        self.onShown.append(self.setWindowTitle)
        # explizit check on every entry
	self.onChangedEntry = []
	
        self.list = []                                                  
       	ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
       	self.createSetup()       

	self["logo"] = Pixmap()
       	self["buttonred"] = Label(_("Cancel"))
       	self["buttongreen"] = Label(_("OK"))
       	self["buttonyellow"] = Label(checking_string)
	self["buttonblue"] = Label(info_header)
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
       	{
       		"green": self.save,
        	"red": self.cancel,
	       	"yellow": self.checking,
        	"blue": self.disclaimer,
            	"save": self.save,
            	"cancel": self.cancel,
            	"ok": self.save,
       	})
       	
    def createSetup(self):                                                  
       	self.list = []
	self.list.append(getConfigListEntry(_("Flashtool"), config.plugins.dbackup.flashtool))
      	self.list.append(getConfigListEntry(_("Backuptool"), config.plugins.dbackup.backuptool))
#	self.list.append(getConfigListEntry(_("Create signature file"), config.plugins.dbackup.sig))
#	self.list.append(getConfigListEntry(_("Extract loader from Flash"), config.plugins.dbackup.loaderextract))
#	self.list.append(getConfigListEntry(_("Extract kernel from Flash"), config.plugins.dbackup.kernelextract))
	self.list.append(getConfigListEntry(_("Flash kernel from image"), config.plugins.dbackup.kernelflash))
        self.list.append(getConfigListEntry(_("Flashing reboot delay [0-60 sec]"), config.plugins.dbackup.delay))
	self.list.append(getConfigListEntry(_("Imagetype in backupname"), config.plugins.dbackup.backupimagetype))
	self.list.append(getConfigListEntry(_("Boxtype in backupname"), config.plugins.dbackup.backupboxtype))
	self.list.append(getConfigListEntry(_("deb in backupname"), config.plugins.dbackup.backupdeb))
	self.list.append(getConfigListEntry(_("Date in backupname"), config.plugins.dbackup.backupdate))
	self.list.append(getConfigListEntry(_("Time in backupname"), config.plugins.dbackup.backuptime))
	if not os.path.exists("/var/lib/opkg/status"):
	        self.list.append(getConfigListEntry(_("Clean apt cache before backup"), config.plugins.dbackup.aptclean))
	        self.list.append(getConfigListEntry(_("Exclude epg.db"), config.plugins.dbackup.epgdb))
        self.list.append(getConfigListEntry(_("Exclude timers"), config.plugins.dbackup.timers))
        self.list.append(getConfigListEntry(_("Exclude settings"), config.plugins.dbackup.settings))
	if os.path.exists("/usr/share/enigma2/picon"):
        	self.list.append(getConfigListEntry(_("Exclude picons"), config.plugins.dbackup.picons))
        self.list.append(getConfigListEntry(_("Minimal Fading Transparency"), config.plugins.dbackup.transparency))
        self.list.append(getConfigListEntry(_("Verbose"), config.plugins.dbackup.verbose))
        self.list.append(getConfigListEntry(_("Sort Imagelist alphabetic"), config.plugins.dbackup.sort))
      	self.list.append(getConfigListEntry(_("Show plugin"), config.plugins.dbackup.showing)) 
	if not os.path.exists("/var/lib/opkg/status"):
	        self.list.append(getConfigListEntry(_("Webinterface"), config.plugins.dbackup.webinterface))

        self["config"].list = self.list                                 
        self["config"].l.setList(self.list)         
       	
    def changedEntry(self):                                                 
       	self.createSetup()       
		
    def setWindowTitle(self):
	self["logo"].instance.setPixmapFromFile("%s/dbackup.png" % dbackup_plugindir)
	self.setTitle(backup_string+" & "+flashing_string+" V%s " % dbackup_version + setup_string)

    def save(self):
	if config.plugins.dbackup.transparency.value > config.av.osd_alpha.value:
		# current transparency is maximum for faded transparency = no fading
		config.plugins.dbackup.transparency.value = config.av.osd_alpha.value
		config.plugins.dbackup.transparency.save()
	if config.plugins.dbackup.flashtool.value == "rescue":
		config.plugins.dbackup.backuplocation.value = "/data/.recovery"
		config.plugins.dbackup.backuptool.value = "tar.gz"
	else:
		# back to normal ...
		if config.plugins.dbackup.backuplocation.value == "/data/.recovery":
			config.plugins.dbackup.backuplocation.value = "/media/hdd/backup"
			config.plugins.dbackup.backuptool.value = "tar.gz"
	config.plugins.dbackup.backuplocation.save()
	config.plugins.dbackup.backuptool.save()
        for x in self["config"].list:
           x[1].save()
        self.close(True)

    def cancel(self):
        for x in self["config"].list:
           x[1].cancel()
        self.close(False)

    def checking(self):      
	self.session.open(dBackupChecking)

    def disclaimer(self):
	self.session.openWithCallback(self.about,MessageBox, disclaimer_string, MessageBox.TYPE_WARNING)

    def about(self,answer):
       	self.session.open(dBackupAbout)

class dBackupAbout(Screen):
    skin = """
        <screen position="center,80" size="680,460" title="About dBackup" >
        <ePixmap position="290,10" size="100,100" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/dBackup/g3icon_dbackup.png" transparent="1" alphatest="on" />
        <widget name="buttonred" position="10,10" size="130,40" backgroundColor="red" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="buttongreen" position="540,10" size="130,40" backgroundColor="green" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;18"/>
        <widget name="aboutdbackup" position="10,120" size="660,100" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        <widget name="freefilesystem" position="100,240" size="220,220" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        <widget name="freememory" position="370,240" size="200,220" valign="center" halign="center" zPosition="2"  foregroundColor="white" font="Regular;24"/>
        </screen>"""

    def __init__(self, session, args = 0):
	Screen.__init__(self, session)
        self.onShown.append(self.setWindowTitle)
        st = os.statvfs("/")                                                                           
        free = st.f_bavail * st.f_frsize/1024/1024                                                               
        total = st.f_blocks * st.f_frsize/1024/1024                                                
        used = (st.f_blocks - st.f_bfree) * st.f_frsize/1024/1024 
	freefilesystem=_("Root Filesystem\n\ntotal: %s MB\nused:  %s MB\nfree:  %s MB") % (total,used,free)		

      	memfree=0
      	memtotal=0
      	memused=0
	fm=open("/proc/meminfo")
      	line = fm.readline()
      	sp=line.split()
      	memtotal=int(sp[1])/1024
      	line = fm.readline()
      	sp=line.split()
      	memfree=int(sp[1])/1024
	fm.close()
	memused=memtotal-memfree
	freememory=_("Memory\n\ntotal: %i MB\nused: %i MB\nfree: %i MB") % (memtotal,memused,memfree)		

       	self["buttonred"] = Label(_("Cancel"))
       	self["buttongreen"] = Label(_("OK"))
       	self["aboutdbackup"] = Label(plugin_string)
       	self["freefilesystem"] = Label(freefilesystem)
       	self["freememory"] = Label(freememory)
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
       	{
       		"green": self.cancel,
        	"red": self.cancel,
	       	"yellow": self.cancel,
        	"blue": self.cancel,
            	"save": self.cancel,
            	"cancel": self.cancel,
            	"ok": self.cancel,
       	})

    def setWindowTitle(self):
        self.setTitle( _("About")+" dBackup")

    def cancel(self):
        self.close(False)

