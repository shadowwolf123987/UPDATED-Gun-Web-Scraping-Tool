#Module Imports
from datetime import datetime

import mariadb
import sys

import os
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup

from openai import OpenAI

#Get Date Time function, formatted for logs
def CurrDateTime():
    return datetime.today().strftime("%d %b %Y %H:%M:%S")

#Environment Variables
try:
    load_dotenv()
    
    #Change these to your own details if you wish to use this tool
    dbUser = os.environ["DB_USER"]
    dbPass = os.environ["DB_PASS"]
    dbHost = os.environ["DB_HOST"]
    dbPort = int(os.environ["DB_PORT"])
    database = os.environ["DATABASE"]
    
    #wifiSsid = os.environ["WIFI_SSID"]
    #wifiPass = os.environ["WIFI_PASS"]

    openAiApiKey = os.environ["OPENAI_API_KEY"]

except:
    #if ENV keys not found, alert user
    print("No Environment Variables detected \n\nEither Add a .env file containing the required details or manually edit the code with your details.")
    sys.exit(1)

#Variable Definitions
logs = open("GSLogs.txt", "a")

#Connecting to DB with Error logging
try:
    conn = mariadb.connect(
        user = dbUser,
        password = dbPass,
        host = dbHost,
        port = dbPort,
        database = database
        )
    
except mariadb.Error as error:
    #If failed, log error in logs file
    logs.write(f"{CurrDateTime()} - DB Connection Failed - {error}\n")
    logs.close()
    sys.exit(1)
    
else:
    logs.write(f"{CurrDateTime()} - DB Connection Successful\n")
    logs.close()

cur = conn.cursor()
client = OpenAI()

#Scraping Wiki pages Function
def ScrapeGunPage(gunType):
    #Format Inputted term to be url friendly
    gunHeader = gunType.replace(" ","_").lower()
    url = "https://en.wikipedia.org/wiki/List_of_"+gunHeader
    
    #Define gun lists
    namesList = []
    imagesList = []
    
    #Get page from URL
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    
    #Find table of guns
    table = soup.find("table", class_="wikitable")
    
    #Get Tables headers to find col number containing name and image
    header = table.find_all("th")
    #Get number of columns in table
    headerCount = len(header)
    
    x=0
    while x < len(header):
        #Get index of name column
        if "name" in header[x].get_text().lower():
            namesCol = x
        
        #Get index of image column
        if "image" in header[x].get_text().lower():
            imagesCol = x

        x+=1
        
    #Get all names and images for page
    body = table.find_all("td")
    
    while namesCol <= len(body) and imagesCol <= len(body): 
        try:
            #Get all names and imgs for row (For checking if theres multiple guns in one row)
            names = body[namesCol].find_all("a")
            imgs = body[imagesCol].find_all("img")
                
        except:
            #If errored, skip gun
            namesCol += headerCount
            imagesCol += headerCount
            
        else:
            #Loops through list of names and imgs per row for cases of multiple names/imgs in a row
            for name,img in zip(names,imgs):
                
                #Skips any gun family label text
                if "family" in name.get_text():
                    namesCol += headerCount
                    imagesCol += headerCount
                
                namesList.append(name.get_text())
                imagesList.append(img.get("src"))
            
            #Go to next gun
            namesCol += headerCount
            imagesCol += headerCount
        
    return namesList,imagesList
    
arNames = []
arImgs = []

arNames,arImgs = ScrapeGunPage("Assault Rifles")

def FilterGunData(names,imgs):
    
    x=0
    while x < len(names):
        
        name = names[x].replace("\n"," ")
        name = name.strip()
        
        img = imgs[x].replace("/thumb/","")
        img = img.split("/")
        del img[-1]
        img = "/".join(img)
        img = img.replace("commons","commons/")
        img = "https:"+img
        
        names[x] = name
        imgs[x] = img
        
        x+=1
        
    return names,imgs

arNames,arImgs = FilterGunData(arNames,arImgs)

