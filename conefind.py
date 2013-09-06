#!/usr/bin/python

import cv

centerX = 160
centerY = 120
#hsvcopy = None
cropped = None

def on_mouse(event, x, y, flags, param):
  if event==cv.CV_EVENT_LBUTTONDOWN:
    print "clicked ", x, ", ", y, ": ", cropped[y,x]
    #global centerX
    #global centerY
    #centerX = x
    #centerY = y

if __name__ == '__main__':
  capture = cv.CaptureFromCAM(0)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
  polar = cv.CreateImage((360, 360), 8, 3)
  cropped = cv.CreateImage((360, 40), 8, 3)
  #hsvcopy = cv.CreateImage((360, 40), 8, 3)
  img = cv.CreateImage((320, 240), 8, 3)
  
  cones = cv.CreateImage((360, 40), 8, 1)

  #arr = cv.CreateImage((360, 40), 8, 1)
  #gee = cv.CreateImage((360, 40), 8, 1)
  #bee = cv.CreateImage((360, 40), 8, 1)

  #hue = cv.CreateImage((360, 40), 8, 1)
  #sat = cv.CreateImage((360, 40), 8, 1)
  #val = cv.CreateImage((360, 40), 8, 1)

  cv.NamedWindow('cam')
  cv.ResizeWindow('cam', 320,240)

  cv.NamedWindow('unwrapped')
  cv.ResizeWindow('unwrapped', 360,40)
  #cv.NamedWindow('hsvcopy')
  #cv.ResizeWindow('hsvcopy', 360,40)

  #cv.NamedWindow('polar')
  cv.NamedWindow('cones')
  
  #cv.NamedWindow('hue')
  #cv.NamedWindow('sat')
  #cv.NamedWindow('val')
  
  #cv.NamedWindow('arr')
  #cv.NamedWindow('gee')
  #cv.NamedWindow('bee')

  cv.SetMouseCallback('unwrapped', on_mouse)
  #on_mouse(cv.CV_EVENT_LBUTTONDOWN, img.width/2, img.height/2, None, None)

  #lower = cv.Scalar(200, 100, 50) #apparently scalars are RGB even when the image is BGR?
  lower = cv.Scalar(50, 100, 200) 
  upper = cv.Scalar(100, 200, 255)

  M = 69

  while True:
    img = cv.QueryFrame(capture)
    cv.LogPolar(img, polar, (centerX, centerY), M+1, cv.CV_INTER_NN) #possible speedup - get subrect src
    #cropped = cv.GetSubRect(polar,(280,0,40,360))
    #cv.Transpose(cropped, cropped)
    cv.Transpose(cv.GetSubRect(polar,(280,0,40,360)), cropped)
    cv.Flip(cropped) #just for viewing

    cv.InRangeS(cropped, lower, upper, cones)
    cv.Erode(cones, cones) # just once might be too much

    k = cv.CreateStructuringElementEx(3, 47, 1, 23, cv.CV_SHAPE_RECT)
    cv.Dilate(cones, cones, k) 
    
    #cv.Split(cropped, bee, gee, arr, None)
    #cv.CvtColor(cropped, hsvcopy, cv.CV_BGR2HSV)
    #cv.Split(hsvcopy, hue, sat, val, None)

    cv.ShowImage('cam', img)
    #cv.ShowImage('polar', polar)
    cv.ShowImage('cones', cones)
    #cv.ShowImage('hsvcopy', hsvcopy)
    cv.ShowImage('unwrapped', cropped)

    #cv.ShowImage('hue', hue)
    #cv.ShowImage('sat', sat)
    #cv.ShowImage('val', val)

    #cv.ShowImage('arr', arr)
    #cv.ShowImage('gee', gee)
    #cv.ShowImage('bee', bee)


    #print "(2,2) = ", arr[2,2], ", ", gee[2,2], ", ", bee[2,2]
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
