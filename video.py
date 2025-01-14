#video segmentation
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import requests
import cgi
import cgitb
from io import StringIO
import pycurl
import json
from io import BytesIO
import math
import numpy as np
import time
from skimage import measure
import cv2
import boto3
# import classify_image

ssim = measure.compare_ssim

#import s3 configuration credentials
exec(compile(open("./configuration.py").read(), "./configuration.py", 'exec'))

#configure s3 boto3 connection
s3 = boto3.resource(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

#array to store urls
arr1 = []

#mean squared error calculation
def mse(imageA, imageB):
	# the 'Mean Squared Error' between the two images is the
	# sum of the squared difference between the two images;
	# NOTE: the two images must have the same dimension
	err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
	err /= float(imageA.shape[0] * imageA.shape[1])

	# return the MSE, the lower the error, the more "similar"
	# the two images are
	return err


#parse the video into frames then call save to aws on it
def parseVideo(videoFile):
    print("parseVideo", videoFile)
    arr = []
    vidcap = cv2.VideoCapture(videoFile) #set videoFile to 0 to capture from webcam
    success,image = vidcap.read()
    seconds = 1 #check every so many seconds
    counter = 1
    time = 0
    fps = int(round(vidcap.get(cv2.CAP_PROP_FPS))) # Gets the frames per second
    multiplier = fps * seconds

    def imageConvert(image):
        try:
            greyimage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return greyimage
        except:
            return image

    oldimage = imageConvert(image)
    newimage = imageConvert(image)    


    while success:
        frameId = int(round(vidcap.get(1))) #current frame number, rounded b/c sometimes you get frame intervals which aren't integers...this adds a little imprecision but is likely good enough
        success, image = vidcap.read() #grabs the next frame
        #image is a 2d numpy array 'numpy.ndarray', bgr I believe
        #we can perform transformations on this array
        if frameId % multiplier == 0:
            newimage = imageConvert(image)
            if not success:
                success = True
            print ('once everyother second similarity measurement:')
            time = vidcap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            #greyscale image
            
            s = 0
            #m = 0
            try:
                #100 calculations takes: ssim - 4.37s, mse -  0.35s
                s = ssim(oldimage, newimage) #10 times slower but is able to detect more types of changes outside of color   #similarity
                #m = mse(oldimage, newimage) #not used for now but can be to speed performance   #error
            except:
                s = 1
                success, image = vidcap.read()
                newimage = imageConvert(image)
                #m = 1
            #write image locally if oldimage and newimage differ in pixel composition enough
            print('~~~~~~~~sssssssssssssim~~~~~~~~~~:', s)
            oldimage = newimage
            if s<=.95:
                    filenameuploaded = 'pics'+str(counter)+'.jpg'
                    cv2.imwrite(filenameuploaded, image) #writes an image of type 'numpy.ndarray' from nongreyscale image
                    print ('statistically relevant difference, will save image')
                    counter+=1
                    arr.append({
                            'filenameuploaded':filenameuploaded,
                            'time': time
                    })
            #append name of image to array and get ready to process the next frame


    vidcap.release()
    print('about to save the following pics:', arr)
    awsSave(arr) #HERE WE SAVE TO AWS

#save to aws s3 and put urls into arr
def awsSave(arr):
    #maybe configure a bucket or folder for each user, right now all goes into one bucket
    # s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={
    #     'LocationConstraint': 'us-west-1'})
    bucket = 'mybucket-bennettmertz'
    counter = 0
    for val in arr:
        print('save attempt:', val['filenameuploaded'])
        counter += 1
        data = open(str(val['filenameuploaded']), 'rb')
        #still need to implement expiration
        # now = datetime.datetime.now()
        # expires = now + datetime.timedelta(minutes=1)
        #Mar 29, 2017 8:57:13 PM       what they do
        #Wed, 29 Mar 2017 20:53:49 GMT what we did
        # expires = 0.001
        s3.Bucket(bucket).put_object(
            Key='pics'+str(counter)+'.jpg',
            Body=data,
            ACL='public-read'
        )
        url = 'https://s3-us-west-1.amazonaws.com/'+str(bucket)+'/'+str(val['filenameuploaded'])
        arr1.append({"url": url, "time": val['time']})
        # classify_image();
