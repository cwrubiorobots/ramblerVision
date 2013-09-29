#!/usr/bin/python

import cv, serial, struct, argparse
from datetime import datetime


# center and depth of the polar coordinate transform
centerX = 160
centerY = 120
M = 69

# define "orange" in a simple way
lower = cv.Scalar( 40, 100, 180) 
upper = cv.Scalar(100, 180, 255)


# mouse event callback
def on_mouse(event, x, y, flags, param): 
  if event==cv.CV_EVENT_LBUTTONDOWN:
    print "clicked ", x, ", ", y, ": ", unwrapped[y,x] # get the color of the pixel (B,G,R)


# main program 
if __name__ == '__main__': 
  # First check to see if the program was invoked with any options  
  parser = argparse.ArgumentParser(description='Measure bearings to orange landmarks.')
  parser.add_argument("-g", "--gui", action="store_true", help="Show video output") 
  parser.add_argument("-d", "--debug", action="store_true", help="Enable debugging") 
  args = parser.parse_args()
  
  # open first serial port and give it a good name
  cyril = serial.Serial('/dev/ttyAMA0', 9600) 
  #print "Opened "+cyril.portstr+" for serial access"
  
  # open the first video4linux device with openCV, and ask it to be 320x240
  capture = cv.CaptureFromCAM(0)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
  
  # Define some pixel canvases in memory
  img = cv.CreateImage((320, 240), 8, 3)
  polar = cv.CreateImage((360, 360), 8, 3)
  unwrapped = cv.CreateImage((360, 40), 8, 3)
  cones = cv.CreateImage((360, 40), 8, 1)

  if args.gui:
    #if args.debug: 
      #cv.NamedWindow('cam')
    cv.NamedWindow('unwrapped')
    cv.NamedWindow('cones')
    cv.SetMouseCallback('unwrapped', on_mouse)
    #on_mouse(cv.CV_EVENT_LBUTTONDOWN, img.width/2, img.height/2, None, None)

  while True:
    # wait for next frame from camera
    img = cv.QueryFrame(capture)
    # using calibrated center, do a log-polar to cartesian transform using nearest-neighbors
    cv.LogPolar(img, polar, (centerX, centerY), M+1, cv.CV_INTER_NN) #possible speedup - get subrect asap 
    # transpose the section we want from the polar result into the unwrapped image
    cv.Transpose(cv.GetSubRect(polar,(280,0,40,360)), unwrapped)
    #flip just for viewing - optional. TODO: make sure nothing is backwards
    cv.Flip(unwrapped)

    # generate 'cones' image using pixels from 'unwrapped' image which fall into range [lower, upper]
    cv.InRangeS(unwrapped, lower, upper, cones)
    # de-noise the 1-bit per pixel output
    cv.Erode(cones, cones) # just once might be too much
    
    # Use a tall thin structure to dilate the remaining 'on' pixels,
    # eliminating beacon range information, and making it easy to see which bearings have 'beacon' in them.
    k = cv.CreateStructuringElementEx(3, 99, 1, 39, cv.CV_SHAPE_RECT)
    cv.Dilate(cones, cones, k) 
    
    # Display the images from the three major steps of acquisition, transformation, and segmentation
    if args.gui:
      #if args.debug:
        #cv.ShowImage('cam', img)
      cv.ShowImage('unwrapped', unwrapped)
      cv.ShowImage('cones', cones)

    size = 0
    segments = 0
    if args.debug:
      print "found %d" % (segments),
    bearings = []
    for i in xrange(360-2):
      # examine the current and next bearing's measurements
      cur = cones[0, i]
      nex = cones[0, i+1]
      if (cur == 0 and nex == 255) or (cur == 255 and nex == 255):
        # a segment of the image is detected as a beacon
        size = size + 1
      elif (cur == 255 and nex == 0):
        # a segment of beacon has ended
        segments = segments + 1
        if args.debug:
          print segments,
        bearings.append([int(i-(size/2)), size])
        size = 0
      if (i == 360-2-1 and size != 0): # handle wraparound
        if (cones[0,0] == 255): # if the first pixel is 'on', there is wraparound.
          if (bearings[0][1] > size): # will the new bearing fall on the 0 side (not the 360 side)?
            bearings[0] = [(((size+bearings[0][1])/2)-size), size+bearings[0][1]]
          else:
            bearings.append([(360-(((size+bearings[0][1])/2)-bearings[0][1])), size+bearings[0][1]])
            bearings.pop(0)
        else: # there is no wraparound, just end the segment
          segments = segments + 1
          if args.debug:
            print segments,
          bearings.append([int(i-(size/2)), size])
    if args.debug:
      print "segments: %s" % bearings

    # now that the measurements have been made, arrange them for logging
    bearingstring = ""
    for b in bearings:
      bearingstring = bearingstring + "%03d," % b[0]

    # tell the cockroach what it wants to hear
    cyril.write(struct.pack('cbbb', '\xfa', 0, 111, 0))

    # Data Logging with POSIX stdio!
    if (cyril.inWaiting() > 0):
      logdata = cyril.read(cyril.inWaiting())
      a = 0
      b = 0
      for c in logdata:
        if c == '\n':
          now = datetime.now().time()
          print "%02d,%02d,%02d,%03d,%d,%s,%s,%s" % \
            (now.hour, now.minute, now.second, now.microsecond/1000, \
            (now.hour*3600000 + now.minute*60000 + now.second*1000 + now.microsecond/1000), \
            logdata[a:b-1], segments, bearingstring)
          a = b + 1 # leapfrog the other counter every line
        b = b + 1 # increment the counter every character
 
    key = cv.WaitKey(30)
    #print "key ",key
    if key == 27:
        break
    elif key == 65362:
        print "M=",M+1
        M = (M + 5)%100
    elif key == 65364:
        print "M=",M+1
        M = (M - 5)%100

  cv.DestroyAllWindows()

