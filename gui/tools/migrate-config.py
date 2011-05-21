#!/usr/local/bin/python
#- 
# Copyright (c) 2011 iXsystems, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

import os
import sys
import sqlite3

from xml.dom import minidom

FREENAS_ETC_BASE = "/conf/base/etc"
FREENAS_RCCONF = os.path.join(FREENAS_ETC_BASE, "rc.conf")
FREENAS_SYSCTLCONF = os.path.join(FREENAS_ETC_BASE, "sysctl.conf")
FREENAS_HOSTSALLOW = os.path.join(FREENAS_ETC_BASE, "hosts.allow")

#FREENAS_DBPATH = "/data/freenas-v1.db"
FREENAS_DBPATH = "/home/john/freenas-v1.db"
FREENAS_DEBUG = 1


def usage():
    print >> sys.stderr, "%s <config.xml>" % sys.argv[0]
    sys.exit(1)


class FreeNASSQL:
    def __init__(self, database, debug = 0):
        self.__handle = sqlite3.connect(database)
        self.__cursor = self.__handle.cursor()
        self.__debug = debug

    def sqldebug(self, fmt, *args):
        if self.__debug:
            __str = "DEBUG: " + fmt
            __str = __str % args
            print >> sys.stderr, __str

    def getmaxID(self, table, idname = "id"):
        self.__cursor.execute("select max(%s) from %s" % (idname, table))
        __id = self.__cursor.fetchone()
        if __id:  
            __id = __id[0] 
        else:
            __id = -1

        return __id

    def getCount(self, table):
        __count = self.__cursor.execute("select count(*) from %s" % table)
        if __count:
            __count = __count[0]
        else:
            __count = 0

        return __count

    def insert(self, table, pairs):
        __sql = "insert into %s (" % table
        for p in pairs:
            __sql += "%s, " % p
        __sql = __sql[:-2] + ") values ("
        for p in pairs:
            __sql += "'%s', " % pairs[p]
        __sql = __sql[:-2] + ');'

        self.sqldebug(__sql)

    def update(self, table, id, pairs):
        __sql = "update %s set " % table
        for p in pairs:
            __sql += "%s = '%s', " % (p, pairs[p])
        __sql = __sql[:-2] + ' '
        __sql += "where id = '%d';" % id
           
        self.sqldebug(__sql)

    def do(self, table, pairs):
        __id = self.getmaxID(table)
       
        if __id > 0:
            self.update(table, __id, pairs)

        else:
            self.insert(table, pairs)


    def close(self):
        pass


class ConfigParser:
    def __init__(self, config):
        self._handlers = {}
        self.__config = config
        self.__sql = FreeNASSQL(FREENAS_DBPATH, FREENAS_DEBUG)

    def __getChildNodeValue(self, __parent):
        __node = None
        for __node in __parent.childNodes:
            if __node.nodeType == __node.ELEMENT_NODE:
                break 

        __value = None
        if __node:
            __value = __node.nodeValue

        return __value

    def __getChildNode(self, __parent, __name):
        __node = None

        if __parent.hasChildNodes():
            for __node in __parent.childNodes:
                if (__node.nodeType == __node.ELEMENT_NODE) and (__name != __node.localName):
                    __node = self.__getChildNode(__node, __name)

                elif (__node.nodeType == __node.ELEMENT_NODE) and (__name == __node.localName):
                    break

                else:
                    __node = self.__getChildNode(__node, __name)

        return __node

    def __getChildNodes(self, __parent, __name):
        __nodes = []

        for __node in __parent.childNodes:
            if __node.nodeType == __node.ELEMENT_NODE and __node.localName == __name:
                __nodes.append(__node)

        return __nodes

    def _nullmethod(self, __parent, __level):
        pass

    def __getmethod(self, __base, __name):
        __method = self._nullmethod

        try:
            if __base:
                __prefix = '_handle_' + __base + '_'
            else: 
                __prefix = '_handle_'

            __method = getattr(self, __prefix + __name)

        except AttributeError:
            print "oops, missing %s" % __prefix + __name
            __method = self._nullmethod

        return __method

    def __do_probe(self, __parent, __level, __depth):
        for __node in __parent.childNodes:
            if __node.hasChildNodes():
                if __level + 1 > __depth['levels']:
                    __depth['levels'] = __level + 1
                self.__do_probe(__node, __level + 1, __depth)

    def __probe(self, __parent, __depth = 1):
        __d = {}
        __d['levels'] = __depth

        self.__do_probe(__parent, 1, __d)
        return __d['levels']

    #
    # XXX WTF??? XXX
    #
    def _handle_access(self, __parent, __level):
        pass

    def _handle_ad(self, __parent, __level):
        __nodemap = {'domaincontrollername':'ad_dcname', 'domainname_dns':'ad_domainname',
            'domainname_netbios':'ad_netbiosname', 'username':'ad_adminname',
            'password':'ad_adminpw', 'enable':None}

        __pairs = {}
        __table = "services_activedirectory"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX Not sure I got this one right... XXX
    #
    def _handle_afp(self, __parent, __level):
        __nodemap = {'enable':None, 'afpname':'afp_srv_name', 'guest':'afp_srv_guest'}

        __pairs = {}
        __table = "services_afp"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX Not implemented XXX
    #
    def _handle_bittorrent(self, __parent, __level):
        pass

    def _handle_cron(self, __parent, __level):
        __nodemap = {'enable':None, 'desc':None, 'all_mins':None,
            'all_hours':None, 'all_days':None, 'all_months':None,
            'all_weekdays':None, 'minute':'cron_minute', 'hour':'cron_hour',
            'day':'cron_daymonth', 'month':'cron_month', 'weekday':'cron_dayweek',
            'who':'cron_user', 'command':'cron_command'}

        __table = "services_cronjob"
        __job_nodes = self.__getChildNodes(__parent, "job")
        for __job_node in __job_nodes:

            __pairs = {}
            for __key in __nodemap:
                __node = self.__getChildNode(__job_node, __key)
                if not __node:
                    continue 

                __value = self.__getChildNodeValue(__node)
                if not __value:
                    continue 

                if __nodemap[__key]:
                    __pairs[__nodemap[__key]] = __value

            if __pairs:
                self.__sql.do(__table, __pairs)

    #
    # XXX Not implemented XXX
    #
    def _handle_daap(self, __parent, __level):
        pass

    #
    # XXX WTF??? XXX
    #
    def _handle_diag(self, __parent, __level):
        pass

    #
    # XXX this needs more work XXX
    #
    def _handle_disks(self, __parent, __level):
        __nodemap = {'name':'disk_name', 'devicespecialfile':'disk_disks',
            'harddiskstandby':'disk_hddstandby', 'acoustic':'disk_acousticlevel',
            'apm':None, 'transfermode':'disk_transfermode', 'type':None,
            'desc':'disk_description', 'size':None, 'smart':None, 'fstype':None}

        __disk_nodes = self.__getChildNodes(__parent, "disk")
        for __disk_node in __disk_nodes:

            __pairs = {}
            __table = "storage_disk"
            for __key in __nodemap:
                __node = self.__getChildNode(__disk_node, __key)
                if not __node:
                    continue

                __value = self.__getChildNodeValue(__node)
                if not __value:
                    continue

                if __nodemap[__key]:
                    __pairs[__nodemap[__key]] = __value
           
            self.__sql.do(__table, __pairs)

    #
    # XXX This needs to be implemented XXX
    #
    def _handle_dynamicdns(self, __parent, __level):
        __nodemap = {}
        __pairs = {} 
        __table = "services_dynamicdns"

    #
    # XXX Hopefully this is correct XXX
    #
    def _handle_ftpd(self, __parent, __level):
        __nodemap = {'numberclients':'ftp_clients',
            'maxconperip':'ftp_ipconnections',
            'maxloginattempts':'ftp_loginattempt',
            'timeout':'ftp_timeout',
            'port':'ftp_port',
            'pasv_max_port':'ftp_passiveportsmax',
            'pasv_min_port':'ftp_passiveportsmin',
            'pasv_address':'ftp_masqaddress',
            'directorymask':'ftp_dirmask',
            'filemask':'ftp_filemask',
            'chrooteveryone':None,
            'privatekey':None,
            'certificate':None,
            'userbandwidth':None,
            'anonymousbandwidth':None,
            'banner':'ftp_banner',
            'tlsrequired':'ftp_ssltls'}

        __pairs = {}
        __table = "services_ftp"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            if __key == 'userbandwidth' or __key == 'anonymousbandwidth':
                if __key == 'userbandwidth':
                    __subnodemap = {'up':'ftp_localuserbw', 'down':'ftp_localuserdlbw'}
                else:
                    __subnodemap = {'up':'ftp_anonuserbw', 'down':'ftp_anonuserdlbw'}

                for __subkey in __subnodemap:
                    __subnode = self.__getChildNode(__node, __subkey)
                    if not __subnode:
                        continue

                    __subvalue = self.__getChildNodeValue(__subnode)
                    if not __subvalue:
                        continue

                    if __subnodemap[__subkey]:
                        __pairs[__subnodemap[__subkey]] = __subvalue

            else:
                __value = self.__getChildNodeValue(__node)
                if not __value:
                    continue

                if __nodemap[__key]:
                    __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_gconcat(self, __parent, __level):
        pass

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_geli(self, __parent, __level):
        pass

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_gmirror(self, __parent, __level):
        pass

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_graid5(self, __parent, __level):
        pass

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_gstripe(self, __parent, __level):
        pass

    #
    # XXX This needs to be looked at XXX
    #
    def _handle_gvinum(self, __parent, __level):
        pass

    #
    # XXX not sure what to do with gateway on this one, default? static route?  XXX
    #
    def _handle_interfaces(self, __parent, __level):
        __nodemap = {'enable':None, 'if':'int_interface', 'ipaddr':'int_ipv4address',
            'subnet':'int_v4netmaskbit', 'ipv6addr':'int_ipv6address',
            'ipv6subnet':'int_v6netmaskbit', 'media':None, 'mediaopt':'int_options', 'gateway':None}

        __table = "network_interfaces"
        __lan_nodes = self.__getChildNodes(__parent, "lan")
        for __lan_node in __lan_nodes:

            __pairs = {}
            for __key in __nodemap:
                __node = self.__getChildNode(__lan_node, __key)

                __value = None 
                if __node:
                    __value = self.__getChildNodeValue(__node)

                if __key == 'ipaddr' and __value == 'dhcp':
                    __value = None
                    __pairs['int_dhcp'] = 1

                elif __key == 'ipv6addr' and __value == 'auto':
                    __value = None
                    __pairs['int_ipv6auto'] = 1

                if __nodemap[__key]:
                    __pairs[__nodemap[__key]] = __value

            if __pairs:
                self.__sql.insert(__table, __pairs) 


    #
    # XXX these are icky, come back to later XXX
    #
    def _handle_iscsiinit(self, __parent, __level):
        pass

    def _handle_iscsitarget(self, __parent, __level):
        pass

    #
    # XXX don't care about this XXX
    #
    def _handle_lastchange(self, __parent, __level):
        pass

    def _handle_ldap(self, __parent, __level):
        __nodemap = {'hostname':'ldap_hostname', 'base':'ldap_basedn', 'anonymousbind':'ldap_anonbind',
            'binddn':None, 'bindpw':None, 'rootbinddn':'ldap_rootbasedn', 'rootbindpw':'ldap_rootbindpw',
            'pam_password':None, 'user_suffix':'ldap_usersuffix', 'group_suffix':'ldap_groupsuffix',
            'password_suffix':'ldap_passwordsuffix', 'machine_suffix':'ldap_machinesuffix'}

        __pairs = {}
        __table = "services_ldap"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs)

    #
    # XXX WTF??? XXX
    #
    def _handle_mounts(self, __parent, __level):
        pass

    #
    # XXX need data XXX
    #
    def _handle_nfsd(self, __parent, __level):
        pass

    #
    # XXX need data XXX
    #
    def _handle_rc(self, __parent, __level):
        pass

    #
    # XXX this looks like a cron job or something, needs looking into XXX
    #
    def _handle_reboot(self, __parent, __level):
        pass

    #
    # XXX needs to be implemented XXX
    #
    def _handle_rsync(self, __parent, __level):
        pass

    #
    # XXX doesn't migrate? XXX
    #
    def _handle_rsyncd(self, __parent, __level):
        pass

    def _handle_samba(self, __parent, __level):

        __settingsmap = {'netbiosname':'cifs_srv_netbiosname', 'workgroup':'cifs_srv_workgroup',
            'serverdesc':'cifs_srv_description', 'security':'cifs_srv_authmodel',
            'guestaccount':'cifs_srv_guest', 'localmaster':'cifs_srv_localmaster',
            'rcvbuf':None, 'sndbuf':None, 'storedosattributes':'cifs_srv_dosattr',
            'largereadwrite':'cifs_srv_largerw', 'usesendfile':'cifs_srv_sendfile',
            'aiorsize':'cifs_srv_aio_rs', 'aiowsize':'cifs_srv_aio_ws', 'aiowbehind':'',
            'enable':None, 'winssrv':None, 'timesrv':'cifs_srv_timeserver',
            'doscharset':'cifs_srv_doscharset', 'unixcharset':'cifs_srv_unixcharset',
            'loglevel':'cifs_srv_loglevel', 'aio':None}

        __pairs = {}
        __table = "services_cifs"
        for __key in __settingsmap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __settingsmap[__key]:
                __pairs[__settingsmap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs)

        __share_pairs = {}
        __share_table = "sharing_cifs_share"
        __sharemap = {'name':'cifs_name', 'path':None, 'comment':'cifs_comment',
            'browseable':'cifs_browsable', 'inheritpermissions':'cifs_inheritperms',
            'recyclebin':'cifs_recyclebin', 'hidedotfiles':None,
            'hostsallow':'cifs_hostsallow', 'hostsdeny':'cifs_hostsdeny'}

        #__mountpoint_table = "storage_mountpoint"

        #
        # Need to figure out logic here, create a volume, then mountpoint,
        # then share is what it looks like on the surface 
        #
        # FreeNAS 0.7 doesn't associate samba shares with disks.... WTF?
        #

        __share_nodes = self.__getChildNodes(__parent, "share") 
        for __share_node in __share_nodes:
            for __key in __sharemap:
                __node = self.__getChildNode(__share_node, __key)
                if not __node:
                    continue

                __value = self.__getChildNodeValue(__node)
                if not __value:
                    continue

                if __sharemap[__key]:
                    __share_pairs[__sharemap[__key]] = __value

            if __share_pairs:
                self.__sql.do(__share_table, __share_pairs)
            

    #
    # XXX this looks like a cron job or something, needs looking into XXX
    #
    def _handle_shutdown(self, __parent, __level):
        pass

    #
    # XXX Convert to smartd flags for /var/tmp/rc.conf.freenas XXX
    #
    def _handle_smartd(self, __parent, __level):
        pass

    def _handle_snmpd(self, __parent, __level):
        pass

    def _handle_sshd(self, __parent, __level):
        __nodemap = {'port':'ssh_tcpport', 'passwordauthentication':'ssh_passwordauth',
            'pubkeyauthentication':None, 'permitrootlogin':'ssh_rootlogin',
            'enable':None, 'private-key':'ssh_privatekey'}

        __pairs = {}
        __table = "services_ssh"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX need to look at code XXX
    #
    def _handle_staticroutes(self, __parent, __level):
        pass

    #
    # XXX can this be migrated? XXX
    #
    def _handle_statusreport(self, __parent, __level):
        pass

    #
    # XXX need to look at code XXX
    #
    def _handle_syslogd(self, __parent, __level):
        pass

    def _handle_system_hostname(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "network_globalconfiguration"

        __pairs = {}
        __pairs['gc_hostname'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_domain(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "network_globalconfiguration"

        __pairs = {}
        __pairs['gc_domain'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_ipv6dnsserver(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "network_globalconfiguration"

        __pairs = {}
        __pairs['gc_nameserver1'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_username(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "auth_user"

        __pairs = {}
        __pairs['username'] = __value
        __pairs['is_active'] = 1
        __pairs['is_superuser'] = 1
        self.__sql.do(__table, __pairs) 

    def _handle_system_password(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "auth_user"

        __pairs = {}
        __pairs['password'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_timezone(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "system_settings"

        __pairs = {}
        __pairs['stg_timezone'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_language(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "system_settings"

        __pairs = {}
        __pairs['stg_language'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_ntp(self, __parent, __level):
        __node = self.__getChildNode(__parent, "timeservers")
        if not __node:
            return

        __value = self.__getChildNodeValue(__node)
        if not __value:
            return

        __table = "system_settings"

        __pairs = {}
        __pairs['stg_ntpserver1'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_webgui_protocol(self, __parent, __level):
        __node = self.__getChildNode(__parent, "protocol")
        if not __node:
            return

        __value = self.__getChildNodeValue(__node)
        if not __value:
            return

        __table = "system_settings"

        __pairs = {}
        __pairs['stg_guiprotocol'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system_webgui(self, __parent, __level):
        self._handle_system_webgui_protocol(__parent, __level)

        __certificate_node = self.__getChildNode(__parent, "certificate")
        if not __certificate_node:
            return

        __certificate_value = self.__getChildNodeValue(__certificate_node)
        if not __certificate_value:
            return

        __privatekey_node = self.__getChildNode(__parent, "privatekey")
        if not __privatekey_node:
            return

        __privatekey_value = self.__getChildNodeValue(__privatekey_node)
        if not __privatekey_value:
            return

        __table = "system_ssl"

        __value = __privatekey_value + "\n" + __certificate_value + "\n"

        __pairs = {}
        __pairs['ssl_certfile'] = __value
        self.__sql.do(__table, __pairs) 

    #
    # XXX WTF XXX
    #
    def _handle_system_zerconf(self, __parent, __level):
        pass

    def _handle_system_motd(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "system_advanced"

        __pairs = {}
        __pairs['adv_motd'] = __value
        self.__sql.do(__table, __pairs) 

    #
    # XXX how to handle swap ? XXX
    #
    def _handle_system_swap(self, __parent, __level):
        __node = self.__getChildNode(__parent, "type")
        if not __node:
            return

        __value = self.__getChildNodeValue(__node)
        if not __value:
            return

    #
    # XXX no proxy support XXX
    #
    def _handle_system_proxy(self, __parent, __level):
        pass

    def _handle_system_email(self, __parent, __level):
        __nodemap = {'server':'em_outgoingserver', 'port':'em_port', 'security':'em_security',
            'username':'em_user', 'password':'em_pass', 'from':'em_fromemail'}

        __table = "system_email"

        __pairs = {}
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX This needs to be implemented XXX
    #
    def _handle_system_rcconf(self, __parent, __level):
        __params = self.__getChildNodes(__parent, "param")

        #f = open(FREENAS_RCCONF, "a")
        for __param in __params:
            __name_node = self.__getChildNode(__param, "name")
            if not __name_node:
                continue

            __name = self.__getChildNodeValue(__name_node)
            if not __name:
                continue

            __value_node = self.__getChildNode(__param, "value")
            if not __value_node:
                continue

            __value = self.__getChildNodeValue(__value_node)
            if not __value:
                continue

            __comment_node = self.__getChildNode(__param, "comment")
            __comment = None
            if __comment_node:
                __comment = self.__getChildNodeValue(__comment_node)

            __enable_node = self.__getChildNode(__param, "enable")
            __enable = False
            if __enable_node:
                __enable = self.__getChildNodeValue(__enable_node)

        #f.close()

    #
    # XXX Uncomment for real use XXX
    #
    def _handle_system_sysctl(self, __parent, __level):
        __params = self.__getChildNodes(__parent, "param")

        #f = open(FREENAS_SYSCTLCONF, "a")
        for __param in __params:
            __name_node = self.__getChildNode(__param, "name")
            if not __name_node:
                continue

            __name = self.__getChildNodeValue(__name_node)
            if not __name:
                continue

            __value_node = self.__getChildNode(__param, "value")
            if not __value_node:
                continue

            __value = self.__getChildNodeValue(__value_node)
            if not __value:
                continue

            __comment_node = self.__getChildNode(__param, "comment")
            __comment = None
            if __comment_node:
                __comment = self.__getChildNodeValue(__comment_node)

            #f.write("%s = %s    # %s\n" % (__name, __value, __comment))
            os.write(0, "%s = %s    # %s\n" % (__name, __value, __comment))

        #f.close()

    #
    # XXX This needs to be implemented XXX
    #
    def _handle_system_hosts(self, __parent, __level):
        pass

    #
    # XXX This needs to be implemented, just printing out values currently XXX
    #
    def _handle_system_hostsacl(self, __parent, __level):
        __rules = self.__getChildNodes(__parent, "rule")

        #f = open(FREENAS_HOSTSALLOW, "a")
        for __rule in __rules:
            __value = self.__getChildNodeValue(__rule)

        #f.close()

    def _handle_system_usermanagement(self, __parent, __level):
        __group_nodes = self.__getChildNodes(__parent, "group")
        for __node in __group_nodes:
            __id_node = self.__getChildNode(__node, "id")
            if not __id_node:
                continue

            __id = self.__getChildNodeValue(__id_node)
            if not __id:
                continue

            __name_node = self.__getChildNode(__node, "name")
            if not __name_node:
                continue

            __name = self.__getChildNodeValue(__name_node)
            if not __name:
                continue

            __table = "account_bsdgroups"

            __pairs = {}
            __pairs['bsdgrp_group'] = __name
            __pairs['bsdgrp_gid'] = __id

            self.__sql.insert(__table, __pairs) 

        __user_nodes = self.__getChildNodes(__parent, "user")
        for __node in __user_nodes:
            __name_node = self.__getChildNode(__node, "name")
            if not __name_node:
                continue

            __name = self.__getChildNodeValue(__name_node)
            if not __name:
                continue

            __id_node = self.__getChildNode(__node, "id")
            if not __id_node:
                continue
            
            __id = self.__getChildNodeValue(__id_node)
            if not __id:
                continue

            __primarygroup_node = self.__getChildNode(__node, "primarygroup")
            if not __primarygroup_node:
                continue

            __primarygroup = self.__getChildNodeValue(__primarygroup_node)
            if not __primarygroup:
                continue

            __table = "account_bsdusers"

            __pairs = {}
            __pairs['bsdusr_username'] =__name
            __pairs['bsdusr_uid'] = __id
            __pairs['bsdusr_group_id'] = __primarygroup

            self.__sql.insert(__table, __pairs) 

            # 
            # XXX This needs to be implemented XXX
            # 
            #__group_nodes = self.__getChildNodes(__node, "group")
            #for __group_node in __group_nodes:
            #    __group_value = self.__getChildNodeValue(__group_node)

            #
            # XXX What should be done with these??? XXX
            #
            #__extraoptions_node = self.__getChildNode(__node, "extraoptions")
            #__extraoptions = self.__getChildNodeValue(__extraoptions_node)

    #
    # XXX convert to pf rules XXX
    #
    def _handle_system_firewall(self, __parent, __level):
        pass

    #
    # XXX needs to be implemented XXX
    #
    def _handle_system_sysconsaver(self, __parent, __level):
        pass

    def _handle_system_dnsserver(self, __parent, __level):
        __value = self.__getChildNodeValue(__parent)
        if not __value:
            return

        __table = "network_globalconfiguration"

        __pairs = {}
        __pairs['gc_nameserver1'] = __value
        self.__sql.do(__table, __pairs) 

    def _handle_system(self, __parent, __level):
        for __node in __parent.childNodes:
            if __node.nodeType == __node.ELEMENT_NODE:
                __method = self.__getmethod("system", __node.localName)
                __method(__node, 0)

    def _handle_tftpd(self, __parent, __level):
        __nodemap = {'dir':'tftp_directory', 'extraoptions':'tftp_options',
            'port':'tftp_port', 'username':'tftp_username', 'umask':'tftp_umask'}

        __pairs = {}
        __table = "services_tftp"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            __value = self.__getChildNodeValue(__node)
            if not __value:
                continue

            if __nodemap[__key]:
                __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX WTF??? XXX
    #
    def _handle_unison(self, __parent, __level):
        pass

    #
    # XXX WTF??? XXX
    #
    def _handle_upnp(self, __parent, __level):
        pass

    def _handle_ups(self, __parent, __level):
        __nodemap = {'upsname':'ups_identifier', 'shutdownmode':'ups_shutdown',
            'shutdowntimer':'ups_shutdowntimer', 'email':None}

        __pairs = {}
        __table = "services_ups"
        for __key in __nodemap:
            __node = self.__getChildNode(__parent, __key)
            if not __node:
                continue

            if __key == 'email':
                __subnodemap = {'to':'ups_toemail', 'subject':'ups_subject'}
                for __subkey in __subnodemap:
                    __subnode = self.__getChildNode(__node, __subkey)
                    if not __subnode:
                        continue

                    __subvalue = self.__getChildNodeValue(__subnode)
                    if not __subvalue:
                        continue

                    if __subnodemap[__subkey]:
                        __pairs[__subnodemap[__subkey]] = __subvalue.replace('%', '%%')

            else:
                __value = self.__getChildNodeValue(__node)
                if not __value:
                    continue

                if __nodemap[__key]:
                    __pairs[__nodemap[__key]] = __value

        if __pairs:
            self.__sql.do(__table, __pairs) 

    #
    # XXX Do we care about this? XXX
    #
    def _handle_version(self, __parent, __level):
        pass

    #
    # XXX Do we care about this? webgui has settings for the django gui XXX
    #
    def _handle_websrv(self, __parent, __level):
        pass

    #
    # XXX this needs to be implemented XXX
    #
    def _handle_zfs(self, __parent, __level):
        pass

    def __parse(self, __parent, __level):
        for __node in __parent.childNodes:
            if __node.nodeType == __node.ELEMENT_NODE:
                __method = self.__getmethod(None, __node.localName)
                __method(__node, 0)

    def run(self):
        __doc = minidom.parse(self.__config)
        __root = __doc.documentElement

        __level = 0
        self.__parse(__root, __level)


#
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#
# So this needs a lot of work still. Various methods aren't implemented,
# others probably have some of the field mappings wrong, freenas 0.7
# code needs to be looked at for all possible options, and data 
# validation neeeds to be done for every field. FUN, FUN, FUN. 
#
# Other areas that need work are enabling/disabling services, 
# interfaces, daemons and what not. Various files should be parsed and
# checked before new data is written so that duplicates are avoided, 
# and so on and so on. This is just a rough draft ;-)
#
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#

def main():
    config = None

    try:
        config = sys.argv[1]
    except:
        usage()

    cp = ConfigParser(config)
    cp.run()


if __name__ == '__main__':
    main()
