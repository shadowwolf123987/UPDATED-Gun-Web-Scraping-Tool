#Module Imports
from datetime import datetime

import mariadb

import os
import sys
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup

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
    sys.exit(1)
    
else:
    logs.write(f"{CurrDateTime()} - DB Connection Successful\n")

cur = conn.cursor()

#Scraping Wiki pages Function
def ScrapeGunPage(gunType):
    #Format Inputted term to be url friendly
    gunHeader = gunType.replace(" ","_").lower()
    url = "https://en.wikipedia.org/wiki/List_of_"+gunHeader
    
    #Define gun lists
    namesList = []
    imagesList = []
    blockedOrigins = ["north korea","south korea","brazil","china","czechoslovakia","indonesia","poland","serbia","singapore","yugoslavia"]
    
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
            
        if "origin" in header[x].get_text().lower() or "country" in header[x].get_text().lower():
            countryCol = x

        x+=1
        
    #Get all names and images for page
    body = table.find_all("td")
    
    #Loops through Wiki Row
    while namesCol <= len(body) and imagesCol <= len(body): 
        try:
            #Get all names and imgs in single row (For checking if theres multiple guns in one row)
            names = body[namesCol].find_all("a")
            imgs = body[imagesCol].find_all("img")
            countries = body[countryCol].find_all("a")
                
        except:
            #If errored, skip gun
            namesCol += headerCount
            imagesCol += headerCount
            countryCol += headerCount
            
        else:
            #Loops through list of names and imgs per row for cases of multiple names and imgs in row
            for name,img,country in zip(names,imgs,countries):
                
                #Filters Names
                name = name.get_text()
                name = name.strip()
                
                #Convert Image Links to Full Resolution Usable Links
                img = img.get("src")
                img = img.replace("/thumb/","")
                img = img.split("/")
                del img[-1]
                img = "/".join(img)
                img = img.replace("commons","commons/")
                img = "https:"+img
                
                #Excludes guns from blocked countries and gun names with the word family in them
                if country.get_text().lower() not in blockedOrigins and "family" not in name:
                    namesList.append(name)
                    imagesList.append(img)
                
            #Goes to next gun
            namesCol += headerCount
            imagesCol += headerCount
            countryCol += headerCount
                    
        
    return namesList,imagesList
    
def pushToDB(table, names, imgs):
    try:
        cur.execute(f"SELECT name,image from {table};") #Tried proper method but its tedious and didnt work
    
    except mariadb.ProgrammingError:
        cur.execute(f"CREATE TABLE {table} (id int NOT NULL AUTO_INCREMENT, name VARCHAR(255) NOT NULL, image MEDIUMTEXT NOT NULL, PRIMARY KEY(id));")
        if pushToDB(table,names,imgs) == False:
            logs.write(f"{CurrDateTime()} - {table} - Data Commit Failed after Creating\n")
        return False
    
    except Exception as error:
        logs.write(f"{CurrDateTime()} - {table} - Data Commit Failed for Unknown Reason - {error}\n")
        return False
    
    else:
        
        try:
            cur.execute(f"TRUNCATE TABLE {table};")
            query = ""
            
            for name,img in zip(names,imgs):
                name = name.replace('"','')
                name = name.replace("'",'')
                img = img.replace('"','')
                img = img.replace("'",'')
                
                query = query + ("('" + name + "','" + img + "'),")
                
            query = query.rstrip(",")
            
            print(f"INSERT INTO {table}(name,image) values {query}")
            cur.execute(f"INSERT INTO {table}(name,image) values {query}")
            conn.commit()
        
        except Exception as error:
            conn.rollback()
            logs.write(f"{CurrDateTime()} - {table} - Data Commit Failed - {error}\n")
            return False
        
        else:
            logs.write(f"{CurrDateTime()} - {table} - Data Committed Successfully\n")
            return True
    
names = []
imgs = []

#Scrape Gun names and Img links for Assault Rifles from Wikipedia
names,imgs = ScrapeGunPage("Assault Rifles")

#Pushes scraped Assault Rifle to appropriate DB table
pushToDB("AssaultRifles",names,imgs)



#Scrape Gun names and Img links for Pistols from Wikipedia
names,imgs = ScrapeGunPage("Pistols")

#Pushes scraped Pistols to appropriate DB table
pushToDB("Pistols",names,imgs)



#Scrape Gun names and Img links for Sniper Rifles from Wikipedia
names,imgs = ScrapeGunPage("Sniper Rifles")

#Pushes scraped Sniper Rifles to appropriate DB table
pushToDB("SniperRifles",names,imgs)



#Scrape Gun names and Img links for Machine Guns from Wikipedia
names,imgs = ScrapeGunPage("MachineGuns")

#Pushes scraped Machine Guns to appropriate DB table
pushToDB("MachineGuns",names,imgs)



#Scrape Gun names and Img links for Shotguns from Wikipedia
names,imgs = ScrapeGunPage("Shotguns")

#Pushes scraped Shotguns to appropriate DB table
pushToDB("Shotguns",names,imgs)

conn.close()
logs.close()