#! /usr/local/bin/python

#  Copyright (C) 2013 Registro.br. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 1. Redistribution of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY REGISTRO.BR ``AS IS AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIE OF FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL REGISTRO.BR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

# $Id: avail_client.py 64 2009-11-05 13:10:15Z eduardo $

import sys
import socket
import StringIO
import random
import getopt

# File where the cookie is stored
COOKIE_FILE = '/tmp/isavail-cookie.txt'

# Default Server Address and port
SERVER_ADDR = '200.160.2.3'
SERVER_PORT = 43

MAX_UDP_SIZE = 512
DEFAULT_COOKIE = '00000000000000000000'

# Maximum retries and interval
MAX_RETRIES = 3
RETRY_TIMEOUT = 5

#############################################################
##                                                         ##
##  Class responsible for parsing a Domain Check response  ##
##                                                         ##
#############################################################
class AvailResponseParser:
    def __init__(self):
        self._status = -1
        self._query_id = ''
        self._fqdn = ''
        self._fqdn_ace = ''
        self._expiration_date = ''
        self._publication_status = ''
        self._nameservers = []
        self._tickets = []
        self._release_process_dates = []
        self._msg = ''
        self._cookie = ''
        self._response = ''
        self._suggestions = []

    def __str__(self):
        msg = "Query ID: " + self._query_id + "\n"
        msg += "Domain name: " + self._fqdn + "\n"
        msg += "Response Status: " + str(self._status) + " ("
        if (self._status == 0):
            msg += "Available)\n"

        elif (self._status == 1):
            msg += "Available with active tickets)\n"
            msg += "Tickets: \n"
            for t in self._tickets:
                msg += "  " + str(t) + "\n"
                        
        elif (self._status == 2):
            msg += "Registered)\n"
            msg += "Expiration Date: "
            if (self._expiration_date == '0'):
                msg += "Exempt from payment\n"
            else:
                 msg += self._expiration_date + "\n"
            msg += "Publication Status: " + self._publication_status + "\n"
            msg += "Nameservers: \n"
            for ns in self._nameservers:
                msg += "  " + ns + "\n"
            if (len(self._suggestions) > 0):
                msg += "Suggestions:"
                for s in self._suggestions:
                    msg += " " + s
                msg += "\n"
            
        elif (self._status == 3):
            msg += "Unavailable)\n"
            msg += "Additional Message: " + self._msg + "\n"
            if (len(self._suggestions) > 0):
                msg += "Suggestions:"
                for s in self._suggestions:
                    msg += " " + s
                msg += "\n"

        elif (self._status == 4):
            msg += "Invalid query)\n"
            msg += "Additional Message: " + self._msg + "\n"
            
        elif (self._status == 5):
            msg += "Release process waiting)\n"

        elif (self._status == 6):
            msg += "Release process in progress)\n"
            msg += "Release Process:\n"
            msg += "  Start date: " + self._release_process_dates[0] + "\n"
            msg += "  End date:   " + self._release_process_dates[1] + "\n"
            
        elif (self._status == 7):
            msg += "Release process in progress with active tickets)\n"
            msg += "Release Process:\n"
            msg += "  Start date: " + self._release_process_dates[0] + "\n"
            msg += "  End date:   " + self._release_process_dates[1] + "\n"
            msg += "Tickets: \n"
            for t in self._tickets:
                msg += "  " + str(t) + "\n"

        elif (self._status == 8):
            msg += "Error)\n"
            msg += "Additional Message: " + self._msg + "\n"
            
        elif (self._response != ''):
            msg = self._response
            
        else:
            msg = 'No response'
            
        return msg

    # Parse a string response
    def parse_response(self, response):
        self._response = response
        buffer = StringIO.StringIO(response)

        line = ''
        while (True):
            line = buffer.readline().strip()

            # Ignore blank lines at the beginning
            if (line == ''):
                continue

            # Ignore comments
            if (line.startswith('%')):
                continue

            # Get the status of the response, or cookie
            if (line.startswith('CK ') or line.startswith('ST ')):
                items = line.split()

                # New cookie
                if (items[0] == 'CK'):
                    self._cookie = items[1][:20]
                    self._query_id = items[2]
                    return 0

                # Get the response status
                try:
                    self._status = int(items[1])
                except:
                    return -1
                
                # Status 8: Error
                if (self._status == 8):
                    line = buffer.readline().strip()
                    self._msg = line
                    return 0
                
                self._query_id = items[2]

            # Get the fqdn and fqdn_ace
            line = buffer.readline().strip()
            words = line.split('|')
            if (len(words) == 1):
                self._fqdn = words[0]
            elif (len(words) == 2):
                self._fqdn_ace = words[1]
                self._fqdn = words[0]
            else:
                return -1
                
            if (self._status == 0 or self._status == 5):
                # Domain available or waiting release process
                return 0

            # Read a new line from the buffer
            line = buffer.readline().strip()

            # Domain available with ticket: Get the list of active tickets
            if (self._status == 1):
                tickets = line.split('|')
                for t in tickets:
                    self._tickets.append(int(t))

                return 0
                        
            # Domain already registered
            elif (self._status == 2):
                words = line.split('|')
                if (len(words) < 2):
                    return -1

                self._expiration_date = words[0]
                self._publication_status = words[1]
                for i in range(2, len(words)):
                    self._nameservers.append(words[i])
                
                # Check if there's any suggestion
                line = buffer.readline().strip()
                if (line == ''):
                    return 0

                suggestions = line.split('|')
                for s in suggestions:
                    self._suggestions.append(s + '.br')

                return 0
            
            # Domain unavailable or invalid
            elif (self._status == 3 or self._status == 4):
                # Just get the message
                self._msg = line
            
                if (self._status == 3):
                    # Check if there's any suggestion
                    line = buffer.readline().strip()
                    if (line == ''):
                        return 0

                    suggestions = line.split('|')
                    for s in suggestions:
                        self._suggestions.append(s + '.br')

                return 0

            # Release process
            elif (self._status == 6 or self._status == 7):
                # Get the release process dates
                self._release_process_dates = line.split('|')
                if (len(self._release_process_dates) < 2):
                    return -1

                # Get the tickets (status 7)
                if (self._status == 7):
                    line = buffer.readline().strip()
                    tickets = line.split('|')
                    for t in tickets:
                        self._tickets.append(int(t))
                        
                return 0

            # Error
            return -1

############################################################
##                                                        ##
## Class responsible for sending a query thru the network ##
##                                                        ##
############################################################
class AvailClient:
    _lang = 0
    _ip = ''
    _cookie = DEFAULT_COOKIE
    _cookie_file = COOKIE_FILE
    _version = 1
    _server = SERVER_ADDR
    _port = SERVER_PORT
    _suggest = 1
    
    def __init__(self,
                 lang = 0,
                 ip = '',
                 cookie_file = COOKIE_FILE,
                 version = 1,
                 server = SERVER_ADDR,
                 port = SERVER_PORT,
                 suggest = 1):

        self._lang = lang
        self._ip = ip
        self._cookie = DEFAULT_COOKIE
        self._cookie_file = cookie_file
        self._version = version
        self._server = server
        self._port = port
        self._suggest = suggest
        
        # Try to get cookie from file
        # If can't open file, send an invalid-cookie query
        try:
            f = open(self._cookie_file, 'r')
        except IOError:
            # Send a query with an invalid cookie
            self.send_query(fqdn = 'registro.br')
        else:
            self._cookie = f.readline()
            f.close()
            if (self._cookie.endswith("\n")):
                self._cookie = self._cookie[:-1]

    def send_query(self, fqdn):
        query = ''
        if (self._ip != ''):
            query += '[' + self._ip + '] '

        # Create a random 10 digit query ID (2^32)
        query_id = str(random.randint(0, 4294967296))

        # Form the query
        query += str(self._version)  + ' ' + self._cookie + ' ' + \
                 str(self._lang) + ' ' + query_id + ' ' + fqdn.strip()

        if (self._version > 0):
            query += ' ' + str(self._suggest)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        addr = (self._server, self._port)

        # Send the query and wait for a response
        timeout = 0
        retries = 0
        resend = True

        # Response parser
        parser = AvailResponseParser()
        while (True):
            # Check the need to (re)send the query
            if (resend == True):
                resend = False
                retries += 1
                if (retries > MAX_RETRIES):
                    break
                
                # Send the query
                sock.sendto(query, addr)
                
            # Set the timeout
            timeout += RETRY_TIMEOUT
            sock.settimeout(timeout)
            try:
                response = sock.recv(MAX_UDP_SIZE)                
            except socket.timeout:                
                # Timeout: Resend the query and wait a little longer
                resend = True
                continue
                
            # Response received. Call the parser
            parser.parse_response(response)

            # Check the query ID
            if (parser._query_id != query_id and
                parser._status != 8):
                # Wrong query ID. Just wait for another response
                resend = False
                continue
            
            # Check if the cookie was invalid
            if (parser._cookie != ''):
                # Save the new cookie
                cookie = self._cookie
                self._cookie = parser._cookie

                try:
                    f = open(self._cookie_file, 'w')
                    f.write(self._cookie)
                    f.close()
                except IOError:
                    pass

                if (cookie == DEFAULT_COOKIE):
                    # Nothing else to do
                    break
                else:
                    # Resend query. Now we should have the right cookie
                    parser = self.send_query(fqdn)
                    break

            break
        
        # Return the filled ResponseParser object
        return parser

#############################################################
##                                                         ##
##                Command-line client                      ##
##                                                         ##
#############################################################

def usage():
    print
    print "Usage:"
    print "\t./avail_client.py [-h] [-d] [-l language] [-s server_IP]"
    print "\t                  [-p server_port] [-c cookie_file] "
    print "\t                  [-a proxied_IP] [-S] fqdn\n"
    print "\t-h Print this help"
    print "\t-d Turn ON debug mode"
    print "\t-l language: EN or PT (Default: PT)"
    print "\t-s server_IP: Server's IP address (Default: " + SERVER_ADDR + ")"
    print "\t-p server_port: Server's port number (Default: " + str(SERVER_PORT) + ")"
    print "\t-c cookie_file: File where the cookie is stored"
    print "\t   (Default: " + COOKIE_FILE + ")"
    print "\t-a proxied_IP: Client IP address being proxied"
    print "\t-S Enable suggestion in server answer" 
    print "\tfqdn: fully qualified domain name being queried"
    print 
    
if __name__ == "__main__":
    # Get the command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hdl:s:p:c:a:S' )
    except getopt.GetoptError:
        usage()
        sys.exit()

    # Default parameters
    debug = False
    language = 1
    server_addr = SERVER_ADDR
    server_port = SERVER_PORT
    cookie_f = COOKIE_FILE
    proxied = ''
    sug = 0
    
    # There must be at least one argument (FQDN)
    if (len(args) == 0):
        usage()
        sys.exit()

    # Get the option values
    fqdn = args[0]
    for opt, value in opts:
        if (opt == '-d'):
            debug = True
        elif (opt == '-h'):
            usage()
            sys.exit()
        elif (opt == '-l'):
            if (value.upper() == 'EN'):
                language = 0
            elif (value.upper() == 'PT'):
                language = 1
            else:
                pass
        elif (opt == '-a'):
            proxied = value
        elif (opt == '-s'):
            server_addr = value
        elif (opt == '-c'):
            cookie_f = value
        elif (opt == '-p'):
            server_port = int(value)
        elif (opt == '-S'):
            sug = 1

    # Initialize client object and send query
    ac = AvailClient(version = 1,
                     lang = language,
                     ip = proxied,
                     cookie_file = cookie_f,
                     server = server_addr,
                     port = server_port,
                     suggest = sug)
    arp = ac.send_query(fqdn)
    
    print arp
    if (debug == True):
        print "*****Response received*****"
        print arp._response

