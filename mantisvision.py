from picamera import PiCamera
from picamera.array import PiRGBArray
from fractions import Fraction
import numpy as np
import time, math, cv2, serial, struct, argparse


sirl = serial.Serial('/dev/ttyAMA0', 9600)
print "Starting Mantis Vision 0.3a, input: PiCamera, output: ",sirl.portstr

#mouse callback
def on_mouse(event, x, y, flags, param):
  if event==cv2.EVENT_RBUTTONDOWN:
    print "clicked (", x, ", ", y,"): ", \
          frame.array[y][x], "BGR -> HSV", \
          im[y][x] #, "=>", th[y][x]
  elif event == cv2.EVENT_LBUTTONDOWN:
    print "new center:", x, ", ", y
    global center
    center = (x, y)
  elif event == cv2.EVENT_LBUTTONUP:
    global radius
    radius = int(math.hypot(center[0]-x, center[1]-y))
    print "new radius:", radius
    

#null callback
def nothing(x):
  pass


#initialize
cam = PiCamera()
cam.resolution = (200, 200) # (400, 300)
center = (cam.resolution[0]/2, cam.resolution[1]/2)
radius = cam.resolution[1]/4
#center = (110, 72) #(210,135)
#radius = 48 #90
cam.zoom = (0.2, 0.165, 0.67, 0.6)
cam.framerate = 10

#warmup and let the gains settle
time.sleep(2) 

#configure
#cam.shutter_speed = cam.exposure_speed
##cam.exposure_mode = 'off'
cam.meter_mode = 'backlit'
cam.iso = 100
##cam.saturation = 1
##cam.contrast = 1

cam.awb_mode = 'fluorescent'
#awb = cam.awb_gains
#cam.awb_mode = 'off'
#cam.awb_gains = awb

#grab reference to raw camera capture
cap = PiRGBArray(cam, size = cam.resolution)

# define upper and lower bounds of what counts as food
#foodLo = np.array([ 0, 10, 10])
#foodHi = np.array([180, 255, 255])
foodLo = np.array([ 0, 50, 150])
foodHi = np.array([15, 255, 255])


#build a clickable window with 6 trackbars for color limits
#cv2.namedWindow("FRAME")
#cv2.setMouseCallback("FRAME", on_mouse)
#cv2.createTrackbar('HL', "FRAME", foodLo[0], 180, nothing)
#cv2.createTrackbar('HH', "FRAME", foodHi[0], 180, nothing)
#cv2.createTrackbar('SL', "FRAME", foodLo[1], 255, nothing)
#cv2.createTrackbar('SH', "FRAME", foodHi[1], 255, nothing)
#cv2.createTrackbar('VL', "FRAME", foodLo[2], 255, nothing)
#cv2.createTrackbar('VH', "FRAME", foodHi[2], 255, nothing)
##cv2.createTrackbar('R',  "FRAME", 128, 256, nothing)
##cv2.createTrackbar('B',  "FRAME", 128, 256, nothing)


counter = 0;
#capture frames
for frame in cam.capture_continuous(cap,format="bgr", use_video_port=True):
  counter += 1
##  if (counter % 100 == 1):
##    print " ISO: ", cam.iso
##    print " DRC: ", cam.drc_strength
##    print " AWB: ", cam.awb_mode
##    print "rd-bl:", cam.awb_gains
##    print "brite:", cam.brightness
##    print "contt:", cam.contrast
##    print "sharp:", cam.sharpness
##    print "satch:", cam.saturation
##    print "meter:", cam.meter_mode
##    print "speed:", cam.exposure_speed
##    print "xmode:", cam.exposure_mode
##    print "xcomp:", cam.exposure_compensation
##    print "dgain:", cam.digital_gain
##    print "again:", cam.analog_gain

  ## adjust segmentation threshold based on UI elements
  #HL = cv2.getTrackbarPos('HL', "FRAME")
  #HH = cv2.getTrackbarPos('HH', "FRAME")
  #SL = cv2.getTrackbarPos('SL', "FRAME")
  #SH = cv2.getTrackbarPos('SH', "FRAME")
  #VL = cv2.getTrackbarPos('VL', "FRAME")
  #VH = cv2.getTrackbarPos('VH', "FRAME")
  #foodLo = np.array([HL, SL, VL])
  #foodHi = np.array([HH, SH, VH])

  ## manually set white balance with fractional adjustment to red- and blue-gain
  #R = cv2.getTrackbarPos('R', "FRAME")
  #B = cv2.getTrackbarPos('B', "FRAME")
  #cam.awb_gains = (Fraction(R, 128), Fraction(B, 128))

  ## convert image to HSV and create thresholded frame mask
  im = cv2.cvtColor(frame.array, cv2.COLOR_BGR2HSV)
  th = cv2.inRange(im, foodLo, foodHi)
  #h,s,v = cv2.split(im)
  #r,t = cv2.threshold(h,20,255,cv2.THRESH_BINARY_INV)

  ## despeckle result 
  e = cv2.erode(th, None)
  d = cv2.dilate(e, None)

  # mask off the original image with the detected segments
  f = cv2.bitwise_and(im, im, mask=d)
  o = cv2.cvtColor(f, cv2.COLOR_HSV2BGR)
  
  ## find blobs, keep track of the biggest one
  contours,_ = cv2.findContours(d, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
  biggest = 0
  for c in contours:
    area = cv2.contourArea(c)
    if area > biggest and area < 2550:
      biggest = area
      best = c

  cx, cy = 0, 0
  if biggest > 0:
    # if there is a biggest blob, find its center
    m = cv2.moments(best)
    cx, cy = int(m['m10']/m['m00']), int(m['m01']/m['m00'])
    #cv2.circle(o, (cx,cy), 9, (250,220,0))
    
    #convert to polar representation, flip, and rotate by 90 degrees
    ang = (((math.atan2(cy-center[1], cx-center[0])*180.0/math.pi + 90.0) % 360 ) - 180) * -1
    #print "food (",cx,", ",cy,", ",biggest,", ", ang,"deg)"
    
    # generate a serial packet (HEADER ID SIZE BEARING)
    serial_size = int(math.ceil(biggest/10))
    serial_dir = int(round(ang/2))
    #print(chr(0)+chr(1)+chr(serial_size)+chr(serial_dir))    
    print "food!", serial_size, serial_dir
    sirl.write(struct.pack('cbBb', '\xfa', 0, serial_size, serial_dir))
  else:
    print "No food"
    sirl.write(struct.pack('cbBb', '\xfa', 0, 0, 111))
    

  #cv2.circle(o, center, 5, (0,250,0))
  #cv2.circle(o, center, radius, (0,250,0))
  #cv2.circle(o, center, radius*2, (0,250,0))

  #cv2.imshow("FRAME", o)
  key = cv2.waitKey(1) & 0xff
  cap.truncate(0)
  # 'q' quits
  if key == ord('q'):
    cv2.destroyAllWindows()
    break
