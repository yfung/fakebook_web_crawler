#!/usr/bin/env python
import argparse
import socket
import string

# Filter the initial data from the login page format into a readable array
def filter_init(data, parsearr):
    # Remove tabs, new lines
    data = data.replace("\t", "")
    data = data.replace("\r", "")
    data = data.replace("    ", "")
    temparr = data.split('\n')
    for x in temparr:
        parsearr.append(x)

# Get the profile links and check for flags
def get_profiles(data, to_visit, visited, flags):
    temparr = data.split("\"")
    for x in temparr:
        if "fakebook" in x and x not in visited and x not in to_visit:
            to_visit.append(x)
        if ">FLAG:" in x:
            temp1 = x.split(" ")
            temp2 = temp1[1].split("<")
            key = temp2[0]
            if key not in flags:
                # Print the secret flag
                print key 
                flags.append(key) 

# Get the cookies from the filtered ata
def get_cookies(parsearr, cookies):
    for x in parsearr:
         if "sessionid" in x:
            cooki = x.split("=")
            tempcookie = cooki[1].split(";")
            cookies.append(tempcookie[0])
         if "csrftoken" in x:
            cscooki = x.split("=")
            tempccookie = cscooki[1].split(";")
            cookies.append(tempccookie[0])

# Login to the website by getting the initial page and getting the cookies, then sending in our POST request. Return the cookies for future requests
def connect(s):
    # Connect to the site
    # Get the site credentials for our visit
    init_message = "GET " + loginlink + " HTTP/1.1\r\nHost: fring.ccs.neu.edu\r\nConnection: Keep-Alive\r\n\r\n"
    s.send(init_message)
    data = s.recv(4096)
    filter_init(data, parsearr)
    # Get the cookies for our session retrieving this page
    get_cookies(parsearr, cookies)
    csrfcookie = cookies[0]
    seshcookie = cookies[1]
    del parsearr[:]
    # Login to the site
    message = "POST /accounts/login/ HTTP/1.1\r\nHost: fring.ccs.neu.edu\r\nUser-Agent: HTTPTool/1.1\r\nContent-Length: 89\r\nContent-Type: application/x-www-form-urlencoded\r\nCookie: sessionid=" + seshcookie + "; csrftoken=" + csrfcookie + "\r\nConnection: Keep-Alive\r\n\r\nusername=" + username + "&password=" + password + "&csrfmiddlewaretoken=" + csrfcookie +"\r\n\r\n"
    s.send(message)
    data = s.recv(4096)
    filter_init(data, parsearr)
    # Get the cookies for our session retrieving this page
    get_cookies(parsearr, cookies)
    if len(cookies) == 3:
        seshcookie = cookies[2]
    del parsearr[:]
    # Move to the home page after we have logged in
    return cookies

# Parse the arguments
parser = argparse.ArgumentParser(description='Process arguments.')
# Handle command line arguments
parser.add_argument('username', metavar='user', type=str)
parser.add_argument('password', metavar='pass', type=str)
# Get the command line arguments
args = parser.parse_args()
# Username
username = args.username
# Password
password = args.password
# Fakebook url
home = "http://fring.ccs.neu.edu/fakebook/"
# Fakebook login url
loginlink = "http://fring.ccs.neu.edu/accounts/login/?next=/fakebook/"
# List of visited links
parsearr = []
to_visit = []
visited = []
# Secret flags
flags = []
# Do we have all 5 flags?
finished = False
# Session cookie
cookies = []

# Create the socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("fring.ccs.neu.edu", 80))
# Login and get the cookies for our session
cookies = connect(s)

while (len(cookies) < 3):
    cookies = connect(s)
# Go to the home page following login
homeget = "GET " + home + " HTTP/1.1\r\nHost: fring.ccs.neu.edu\r\nConnection: Keep-Alive\r\nUser-Agent: HTTPTool/1.1\r\nCookie: sessionid=" + cookies[2] + "; csrftoken=" + cookies[0] + "\r\n\r\n"
s.send(homeget)
# Append fakebook, since we start here
visited.append("/fakebook/")
data = s.recv(4096)
# Get the profiles on the home page
get_profiles(data, to_visit, visited, flags)

# Loop for all links in our to_visit list, which adds more links it finds if we have not seen or visited those links before
while (len(to_visit) > 0) and len(flags) < 5:
    for link in to_visit:
        # Do we have all the flags?
        if len(flags) >= 5 :
            # if we have all the flags, stop
            break
        # Get the page
        while len(cookies[2]) < 1:
            s.close()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("fring.ccs.neu.edu", 80))
            cookies = connect(s)
        # Get the desired link in our to_visit list
        crawlmessage = "GET " + link + " HTTP/1.1\r\nHost: fring.ccs.neu.edu\r\nConnection: Keep-Alive\r\nCookie: sessionid=" + cookies[2] + "; csrftoken=" + cookies[0] + "\r\n\r\n"
        s.send(crawlmessage)
        data = s.recv(4096)
        # If we receive nothing, handle it
        if data == "":
            #print crawlmessage
            s.close()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("fring.ccs.neu.edu", 80))
            cookies = connect(s) 
        # If we have a broken link, abandon and move on, do not visit it again
        if "HTTP/1.1 403" in data:
            visited.append(link)
            to_visit.remove(link)
            continue
        # If the link is a redirect, add the new link and remove the current one
        if "HTTP/1.1 301" in data:
            # Add the redirect to links we should visit
            #to_visit.append(new_link)
            to_visit.remove(link)
            visited.append(link)
            continue
        # If we error in reaching the page, leave it in the array and continue, we will loop back around to it eventually
        if "HTTP/1.1 500" in data:
            #print "500 Error"
            s.close()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("fring.ccs.neu.edu", 80))
            cookies = connect(s)
            continue
        # If the data is good, get the links, handle them, and mark this link as visited
        if "HTTP/1.1 200" in data:
            get_profiles(data, to_visit, visited, flags)
            # We just visited this link, append it to visited
            visited.append(link)
            # We just visited this link, remove it from the list
            to_visit.remove(link)

# close the socket when we are done
s.close()