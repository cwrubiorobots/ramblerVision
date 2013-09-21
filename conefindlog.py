#!/usr/bin/python

import serial, struct
from datetime import datetime
from time import sleep
import cv

# the center of the reflector in the camera frame should be set here
centerX = 160 #150 #175 #160
centerY = 120 #125 #110 #120

# These (B,G,R) values determine the range of colors to detect as "cones".
#Calibration A: finding cones in room 817
#lower = cv.Scalar(35,  90, 140) # (B, G, R)
#upper = cv.Scalar(70, 140, 255)
#Calibration B: finding green paper in 817
#lower = cv.Scalar(10,  90, 10)
#upper = cv.Scalar(99, 255, 90)
#Calibration C: finding orange paper in 817
#lower = cv.Scalar(50, 120, 190)
#upper = cv.Scalar(90, 160, 255)
#Calibration D: Cones in room 817
#lower = cv.Scalar(45,  90, 160) 
#upper = cv.Scalar(90, 180, 255)
#Calibration E: Arena in room 814
lower = cv.Scalar(55, 100, 160) 
upper = cv.Scalar(90, 180, 255)

unwrapped = None
cam = None
polar = None
cones = None

cyril = serial.Serial('/dev/ttyAMA0', 9600) #open first serial port and give it a good name
print "Opened "+cyril.portstr+" for serial access"

def on_mouse(event, x, y, flags, param):
  if event==cv.CV_EVENT_LBUTTONDOWN:
    #print "clicked ", x, ", ", y  #, ": ", cam[y,x]
    print "clicked ", x, ", ", y, ": ", unwrapped[y,x]
    #global centerX
    #global centerY
    #centerX = x
    #centerY = y

if __name__ == '__main__':
  #This is the setup
  datalog = open("data.log", "w+")
  datalog.write("\n~~~=== Rambler Data Log Opened, " + str(datetime.now()) + " ===~~~\n")

  capture = cv.CaptureFromCAM(0)
  #capture = cv.CaptureFromFile("../out2.mpg")
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

  polar = cv.CreateImage((360, 360), 8, 3)
  unwrapped = cv.CreateImage((360, 40), 8, 3)
  cam = cv.CreateImage((320, 240), 8, 3)
  cones = cv.CreateImage((360, 40), 8, 1)

  cv.NamedWindow('cam')
  cv.ResizeWindow('cam', 320,240)
  cv.NamedWindow('unwrapped')
  cv.ResizeWindow('unwrapped', 360,40)
  cv.NamedWindow('cones')
  cv.ResizeWindow('cones', 360,40)

  sleep(3)
  cam = cv.QueryFrame(capture)
  sleep(3)
  cam = cv.QueryFrame(capture)
  sleep(3)
  cv.ShowImage('cam', cam)

  ##GUI #Enable these lines to allow mouse interaction with the polar transform
  ##GUI cv.SetMouseCallback('cam', on_mouse)
  cv.SetMouseCallback('unwrapped', on_mouse)
  #on_mouse(cv.CV_EVENT_LBUTTONDOWN, centerX, centerY, None, None)
  
  # The magic number M determines how deep the polar transformation goes.
  M = 69

  #This is the main loop
  while True:
    cam = cv.QueryFrame(capture)
    cv.LogPolar(cam, polar, (centerX, centerY), M+1, cv.CV_INTER_NN) #possible speedup - get subrect src
    #unwrapped = cv.GetSubRect(polar,(280,0,40,360))
    #cv.Transpose(unwrapped, unwrapped)
    cv.Transpose(cv.GetSubRect(polar,(280,0,40,360)), unwrapped)
    cv.Flip(unwrapped) #just for viewing (possible speedup)

    cv.InRangeS(unwrapped, lower, upper, cones)
    cv.Erode(cones, cones) # just once might be too much, but unavoidable

    k = cv.CreateStructuringElementEx(3, 43, 1, 1, cv.CV_SHAPE_RECT) # create a 3x43 rectangular dilation element k
    cv.Dilate(cones, cones, k) 

    #Display (should probably be disabled with a usage flag)
    cv.ShowImage('cam', cam)
    cv.ShowImage('unwrapped', unwrapped)
    cv.ShowImage('cones', cones)
    #cv.ShowImage('polar', polar)
    #cv.ShowImage('hsvcopy', hsvcopy)

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
            #print "! ss", ss, "@", i-s/2,
            s = 0
        #handle wraparound
        if (i == 360-2-1 and s != 0): #TODO: double check this offset
            if (cones[0,0] == 255):
                #print "edge case A"
                bearingToLandmarks[0] = ((bearingToLandmarks[0][0]-s/2)%360, bearingToLandmarks[0][1]+s) #TODO: recalculate center more accurately
            else:
                #print "edge case B"
                bearingToLandmarks.append((c-s/2, s))

    # Bearing output #TODO: CHECK VS REALITY
    bearingToGoal = 111 # Default is to send a bogus bearing (not in range [-90, 90])
    #if len(bearingToLandmarks) > 0:
    #    bearingToGoal = derez(bearingToLandmarks[0][0])
    output =  struct.pack('c','\xfa') \
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
          s = (str(datetime.now().time())+","+logdata[a:b]+","+ \
               str(len(bearingToLandmarks))+","+str(bearingToLandmarks)+"\n")
          datalog.write(s)
          #print s
          a = b + 1  # a only gets incremented on EOL
        b = b + 1
        #print "!",

    #hacky data logging with stdio
    #print str(datetime.now().time()), bearingToLandmarks, len(bearingToLandmarks)
    print str(len(bearingToLandmarks)), ",", str(bearingToLandmarks)
    
    key = 0 
    #key = cv.WaitKey(10) # THIS REQUIRES AT LEAST ONE WINDOW 
    #print "key ",key
    if key == 27:
        break
    elif key == 65362:
        print "M=",M+1
        M = (M + 5)%100
    elif key == 65364:
        print "M=",M+1
        M = (M - 5)%100
  #cv.DestroyAllWindows()
