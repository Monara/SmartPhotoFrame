#Smart Picture Frame. Read-only access to dropbox

from tkinter import * #Tkinter for python2, tkinter for python3
from PIL import ImageTk, Image
from datetime import datetime, timedelta
from dateutil import tz #to ensure correct timezone
import dropbox
from dropbox.files import * #ThumbnailFormat, ThumbnailSize, ThumbnailMode, etc
import json
import reverse_geocode #git clone git://github.com/richardpenman/reverse_geocode/
import os #delete files locally

uploadImagesFolder = "/Nuotraukos_rodymui"
fontName = "Josefin Sans"
fontSize = 22
defaultScreenWidth = 1024
defaultScreenHeight = 600
defaultImage = "default.jpg"
imagesToCycle = 3

def quit(event): #quit program with esc, no other means
	root.destroy()

def update_clock():
	timeZone = tz.gettz("Europe/Vilnius")
	dateAndTime = datetime.now(tz=timeZone) #year, month, day, hour, minute, microsecond, timezone
	dateAndTimeStr = dateAndTime.strftime("%H:%M")
	currentTime.configure(text=" " + dateAndTimeStr) #gap from icon
	root.after(1000, update_clock)

def read_file_contents(fileName):
	file = open(fileName, "r")
	contents = file.read().strip()
	file.close()
	return contents
	
def access_dropbox():
	try:
		access_key = read_file_contents("dropbox_key.txt")
		dbx = dropbox.Dropbox(access_key)
		return dbx
	except:
		print ("Cannot access Dropbox.")
		return None		
				
def get_next_image_entry(imageEntryList, oldImageName):
	
	if len(imageEntryList) == 0: #empty list
		return None
	
	oldImageIndex = -1
	newImageIndex = -1
	
	#find index of old image
	for i in range(len(imageEntryList)):
		if imageEntryList[i].name == oldImageName:
			oldImageIndex = i
			break
			
	#if found and not newest, get newer image
	if oldImageIndex > 0:
		newImageIndex = oldImageIndex - 1
	# else (not found, deleted) take oldest image
	else:
		newImageIndex = len(imageEntryList) - 1
	
	return imageEntryList[newImageIndex]		
		
def get_dropbox_image(dbx, imageEntry):
	imgName = imageEntry.name
	imgPath = imageEntry.path_lower
	
	try:	
		#Get thumbnail.Tuple returned
		(dbxImgMeta, dbxImg) = dbx.files_get_thumbnail(path=imgPath, format=ThumbnailFormat("jpeg", None), size=ThumbnailSize("w1024h768", None), mode=ThumbnailMode("strict", None))
		
		#Save file
		img = open(imgName, "wb")
		img.write(dbxImg.content)
		img.close()
	
		return dbxImgMeta
	except:
		return None			

def update_image_and_info(dbx, oldImageName):
	
	#Default file and info to display
	imgPath = defaultImage
	uploaderName = "Nėra" #none
	placeStr = "Nenurodyta" #unspecified location
	
	if dbx != None:
		
		try:
			#List files
			listFolder = dbx.files_list_folder(path=uploadImagesFolder)
			listFolderImages = list(filter(lambda x: x.name.endswith(".jpeg") or x.name.endswith(".jpg"), listFolder.entries))
			fileCount = len(listFolderImages)
			print(fileCount)
		except:
			listFolderImages = None
			fileCount = 0

		if fileCount > 0 and listFolderImages != None:
			#Sort list: newest uploaded first
			fileArraySorted = sorted(listFolderImages, key=lambda x: x.server_modified, reverse=True)
			
			#Cycle images uploaded in the last week since newest
			newestUploadedDate = fileArraySorted[0].server_modified
			week = timedelta(days=7)
			showImagesFrom = newestUploadedDate - week
			entriesToShow = [x for x in fileArraySorted if x.server_modified > showImagesFrom]
			
			if len(entriesToShow) < imagesToCycle: #if there isn't enough images to cycle, append older images
				entriesToShow += fileArraySorted[len(entriesToShow):imagesToCycle]
			
			nextImageEntry = get_next_image_entry(entriesToShow, oldImageName)
			print(nextImageEntry.server_modified)
			
			if nextImageEntry != None:
				dbxImgMeta = get_dropbox_image(dbx, nextImageEntry)
					
				if dbxImgMeta != None:
					imgPath = nextImageEntry.name #local
					#Get uploader name from metadata
					uploaderID = dbxImgMeta.sharing_info.modified_by
					uploaderName = dbx.users_get_account(uploaderID).name.given_name

					#Get GPS coordinates from metadata
					mediaMeta = dbxImgMeta.media_info
					#media_info: pending or metadata
					if mediaMeta.is_metadata():
						readyImgMeta = mediaMeta.get_metadata()
						if readyImgMeta.location != None:
							gps = (readyImgMeta.location.latitude, readyImgMeta.location.longitude)
							place = reverse_geocode.get(gps) 
							placeStr = place["city"] + ", " + place["country_code"] #dict data type. country or country_code
			
	
	#Resize image
	localImg = Image.open(imgPath)
	(thumbnailWidth, thumbnailHeight) = localImg.size
	#Width doesn't need resizing, unless height is too large
	if thumbnailHeight > defaultScreenHeight:
		difference = thumbnailHeight - defaultScreenHeight #often 168px
		resizeBy = difference / thumbnailHeight
		resizeWidth = int(thumbnailWidth * (1 - resizeBy))
		localImg = localImg.resize((resizeWidth, defaultScreenHeight), Image.ANTIALIAS)
	
	useImage = ImageTk.PhotoImage(localImg) #same folder as program
	displayImage.configure(image=useImage)
	displayImage.image = useImage
	displayUploader.configure(text=" " + uploaderName)		
	displayLocation.configure(text=placeStr)
	
	#Remove old image locally
	if imgPath != defaultImage and imgPath != None: 
		os.remove(imgPath)
		
	#Run again after delay
	root.after(3600000, update_image_and_info, dbx, imgPath) #1 hour

#Root widget
root = Tk()
root.bind("<Escape>", quit)
root.geometry("1024x600")
root.attributes("-fullscreen", True)
root.configure(bg="black", cursor="none")
root.resizable(False, False) #no maximizing

#Frames for image and info
imageFrame = Frame(root, width=1024, height=600)
imageFrame.grid(row=0, column=0, columnspan=3, sticky=N)
infoFrame = Frame(root, width=1024, height=50, bg="black")
infoFrame.grid(row=0, column=0, columnspan=3, sticky=N) 
infoFrame.columnconfigure(0, weight=2) #all below necessary, otherwise crowded:
infoFrame.columnconfigure(1, weight=0)
infoFrame.columnconfigure(2, weight=1)
infoFrame.grid_propagate(0)

#Time and icon
tIcon = Image.open("clock.png")
tIcon = tIcon.resize((24, 24), Image.ANTIALIAS)
timeIcon = ImageTk.PhotoImage(tIcon)
currentTime = Label(infoFrame, image=timeIcon, font=(fontName, fontSize), bg ="black", fg ="white", borderwidth=0, compound="left") #update_clock() defines text
currentTime.image = timeIcon
currentTime.grid(row=0, column=0, sticky=NW, ipadx=10, ipady=10)

#Uploader name and icon
uIcon = Image.open("user.png")
uIcon = uIcon.resize((24, 24), Image.ANTIALIAS)
userIcon = ImageTk.PhotoImage(uIcon)
displayUploader = Label(infoFrame, image=userIcon, font=(fontName, fontSize), bg="black", fg="white", borderwidth=0, compound="left") #text=" " + uploaderName
displayUploader.image = userIcon
displayUploader.grid(row=0, column=1, ipadx=10, ipady=10)

#GPS coordinates and icon
lIcon = Image.open("location.png")
lIcon = lIcon.resize((32, 32), Image.ANTIALIAS)
locIcon = ImageTk.PhotoImage(lIcon)
displayLocation = Label(infoFrame, image=locIcon, font=(fontName, fontSize), bg="black", fg="white", borderwidth=0, compound="left") #text=placeStr
displayLocation.image = locIcon
displayLocation.grid(row=0, column=2, sticky=NE, ipadx=10, ipady=10)

#Display image
displayImage = Label(imageFrame, borderwidth=0) #label border shown white otherwise
displayImage.pack(side=TOP, fill=X)

update_clock()
dbx = access_dropbox()
update_image_and_info(dbx, None)
root.mainloop()

