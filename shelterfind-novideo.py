#!/usr/bin/python

import cv, serial, struct
from datetime import datetime

cyril = serial.Serial('/dev/ttyAMA0', 9600) #open first serial port and give it a good name
print "Opened "+cyril.portstr+" for serial access"

# the center of the reflector in the camera frame should be set here
centerX = 150 #175 #160
centerY = 125 #110 #120

# These values determine the range of colors to detect as "shelter".
#Calibration A: finding cones in room 817
#lower = cv.Scalar(35,  90, 140) # (B, G, R)
#upper = cv.Scalar(70, 140, 255)
#Calibration B: finding green paper in 817
#lower = cv.Scalar(10,  90, 10)
#upper = cv.Scalar(99, 255, 90)
#Calibration C: finding orange paper in 817
lower = cv.Scalar(50, 120, 190)
upper = cv.Scalar(90, 160, 255)

cropped = None
img = None

# decrease angular resolution for 8-bit serial transport, result in [-90,90]
def derez(x):
  if( x < 90 ):
    return (-90-x)/2
  else:
    return (270-x)/2

# allow user to click on image from camera to set the center for transformation
def on_mouse(event, x, y, flags, param):
  if event==cv.CV_EVENT_LBUTTONDOWN:
    #print x, ", ", y, ": ", img[y,x]
    print "Set center ", x, ", ", y, ": ", img[y,x]
    global centerX
    global centerY
    centerX = x
    centerY = y


if __name__ == '__main__':
  #This is the setup
  datalog = open("data.log", "w+")
  datalog.write("\n~~~=== Rambler Data Log Opened, " + str(datetime.now()) + " ===~~~\n")

  capture = cv.CaptureFromCAM(0)
  #capture = cv.CaptureFromFile("../out2.mpg")
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

  polar = cv.CreateImage((360, 360), 8, 3)
  cropped = cv.CreateImage((360, 40), 8, 3)
  img = cv.CreateImage((320, 240), 8, 3)
  
  cones = cv.CreateImage((360, 40), 8, 1)

  #cv.NamedWindow('cam')
  #cv.NamedWindow('unwrapped')
  #cv.NamedWindow('target')
  
  #cv.SetMouseCallback('cam', on_mouse)
  #on_mouse(cv.CV_EVENT_LBUTTONDOWN, centerX, centerY, None, None)

  # The magic number M determines how deep the polar transformation goes.
  M = 69

  #This is the main loop
  while True:
    img = cv.QueryFrame(capture)
    cv.LogPolar(img, polar, (centerX, centerY), M+1, cv.CV_INTER_NN) #possible speedup - get subrect src
    #cropped = cv.GetSubRect(polar,(280,0,40,360))
    #cv.Transpose(cropped, cropped)
    cv.Transpose(cv.GetSubRect(polar,(280,0,40,360)), cropped)
    cv.Flip(cropped) #just for viewing (possible speedup)

    cv.InRangeS(cropped, lower, upper, cones)
    
    cv.Erode(cones, cones) # just once might be too much

    k = cv.CreateStructuringElementEx(3, 43, 1, 1, cv.CV_SHAPE_RECT) # create a 3x43 rectangular dilation element k
    cv.Dilate(cones, cones, k, 2) 

    #scan top row of thresholded, eroded, dilated image, find the number of contiguous segments and their location
    s = 0 # size of contiguous segment
    ss = 0 #number of contiguous segments
    bearingToLandmarks = []
    for i in xrange(360-2):
        c = cones[0, i] #current
        n = cones[0, i+1] #next
        #print int(c),
        if (c == 0 and n == 255) or \
           (c == 255 and n == 255): # this condition marks beginning or middle of contiguous segment
            s = s + 1
            #print ".",
        elif (c == 255 and n == 0): # end of contiguous segment
            ss = ss + 1
            bearingToLandmarks.append((i-s/2, s))
            s = 0
        #handle wraparound
        if (i == 360-2-1 and s != 0): #TODO: double check this offset
            if (cones[0,0] == 255):
                #print "edge case A"
                bearingToLandmarks[0] = ((bearingToLandmarks[0][0]-s/2)%360, bearingToLandmarks[0][1]+s) #TODO: recalculate center more accurately
            else:
                #print "edge case B"
                bearingToLandmarks.append((c-s/2, s))
    #print ".", ss, "."
    #bearingToLandmarks.append((derez(g), 12))
    #g = (g + 1) % 360
    #print bearingToLandmarks, len(bearingToLandmarks)
    for tuple in bearingToLandmarks:
        print tuple[0], derez(tuple[0]), tuple[1]

    bearingToGoal = 111 # Default is to send a bogus bearing (no in range [-90, 90]
    # Bearing output #TODO: CHECK VS REALITY
    if len(bearingToLandmarks) > 0:
        bearingToGoal = derez(bearingToLandmarks[0][0])
    output = struct.pack('c','\xfa') \
        + struct.pack('B', 0) \
        + struct.pack('b', bearingToGoal) \
        + struct.pack('B', 0) 
    cyril.write(output)

    #Data Logging
    if (cyril.inWaiting() > 0):
      logdata = cyril.read(cyril.inWaiting())
      a = 0
      b = 0
      for c in logdata:
        if c == '\n':
          datalog.write(str(datetime.now().time())+","+logdata[a:b]+"\n")
          a = b + 1
        b = b + 1
    
    #cv.ShowImage('cam', img)
    #cv.ShowImage('unwrapped', cropped)
    #cv.ShowImage('target', cones)

    key = 0 #cv.WaitKey(10) # THIS REQUIRES AT LEAST ONE WINDOW 
    #print "key ",key
    if key > 0:
        break
        
  cv.DestroyAllWindows()
  cyril.close()
  datalog.write("\n~~~=== Rambler Data Log Closed, " + str(datetime.now()) + " ===~~~\n")
  datalog.close()
