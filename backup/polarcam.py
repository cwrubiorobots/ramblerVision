#!/usr/bin/python

import cv2.cv as cv

centerX = 160
centerY = 120

def on_mouse(event, x, y, flags, param):
  if event==cv.CV_EVENT_LBUTTONDOWN:
    #print "clicked ", x, ", ", y
    global centerX
    global centerY
    centerX = x
    centerY = y

if __name__ == '__main__':
  capture = cv.CaptureFromCAM(0)
  #capture = cv.CaptureFromFile("out.mpg") # not working, for unknown reasons

  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_WIDTH, 320)
  cv.SetCaptureProperty(capture, cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

  polar = cv.CreateImage((360, 360), 8, 3)
  img = cv.CreateImage((320, 240), 8, 3)
  im = cv.CreateImage((320, 240), 8, 1)
  rt = cv.CreateImage((320, 240), 8, 1)
  lt = cv.CreateImage((320, 240), 8, 1)
  lm = cv.LoadImageM("leftmask-K-2013-02-27.bmp", cv.CV_LOAD_IMAGE_GRAYSCALE)
  rm = cv.LoadImageM("rightmask-K-2013-02-27.bmp", cv.CV_LOAD_IMAGE_GRAYSCALE)
  
  cv.NamedWindow('cam')
  cv.NamedWindow('left')
  cv.NamedWindow('right')

  cv.SetMouseCallback("cam", on_mouse)
  on_mouse(cv.CV_EVENT_LBUTTONDOWN, centerX, centerY, None, None)

  font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN, 1.0, 1.0) 

  M = 60

  while True:
    img = cv.QueryFrame(capture)
    cv.CvtColor(img, im, cv.CV_RGB2GRAY)
    #cv.LogPolar(img, polar, (centerX, centerY), M+1, cv.CV_INTER_NN + cv.CV_WARP_FILL_OUTLIERS )

    cv.And(im, lm, lt)
    leftBrightness = cv.Avg(im, mask=lm)
    cv.Rectangle(lt, (0, 0), (32, 32), leftBrightness, thickness=-1)
    cv.PutText(lt, "%3.0f" % leftBrightness[0], (3,20), font, cv.RealScalar(0))

    cv.And(im, rm, rt)
    rightBrightness = cv.Avg(im, mask=rm)
    cv.Rectangle(rt, (0, 0), (32, 32), rightBrightness, thickness=-1)
    cv.PutText(rt, "%3.0f" % rightBrightness[0], (3,20), font, cv.RealScalar(0))

    cv.ShowImage('cam', im)
    cv.ShowImage('left', lt)
    cv.ShowImage('right', rt)

    key = cv.WaitKey(10)
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
