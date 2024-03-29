from __future__ import print_function
import cv2
import numpy as np
import pcl
import numpy as np
import os.path
import os
from data import VOCDetection, VOC_ROOT, VOCAnnotationTransform, KITTIDetection, KITTI_ROOT, KITTIAnnotationTransform

#/home/dllab/kitti_object/data_object_velodyne/data_object_calib/training/calib
def readCalibration(calib_dir,img_idx):

  label_filename = "{}/{}.txt".format(calib_dir,img_idx)
  lines = [line.rstrip() for line in open(label_filename)]

  for line in lines:
      data = line.split(' ')
      data[1:] = [float(x) for x in data[1:]]
      if(data[0] == 'Tr_velo_to_cam:'):
        #rot [0][0]data [1]
        Tr_velo_to_cam = np.matrix([[data[1],data[2],data[3],data[4]],[data[5],data[6], data[7], data[8]],[data[9],data[10],data[11], data[12]],[0.0,0.0,0.0,1.0]])
      if(data[0] == 'R0_rect:'):
        R0_rect = np.matrix([[data[1],data[2],data[3],0.0],[data[4],data[5], data[6],0.0],[data[7],data[8],data[9],0.0],[0.0,0.0,0.0,1.0]])
      if(data[0] == 'P2:'):
        P2 = np.matrix([[data[1],data[2],data[3],data[4]],[data[5],data[6],data[7],data[8]],[data[9],data[10],data[11], data[12]]])


  return Tr_velo_to_cam, R0_rect, P2

def readDetections(label_dir,img_idx):
  label_filename = "{}/{}.txt".format(label_dir,img_idx)
  lines = [line.rstrip() for line in open(label_filename)]
  objects = [Object3d(line) for line in lines]
  return objects

class Object3d(object):
  ''' 3d object label '''
  def __init__(self, label_file_line, data=None):
    data = label_file_line.split(' ')
    data[1:] = [float(x) for x in data[1:]]

    # extract label, truncation, occlusion
    self.type = data[0] # 'Car', 'Pedestrian', ...
    #self.truncation = data[1] # truncated pixel ratio [0..1]
    #self.occlusion = int(data[2]) # 0=visible, 1=partly occluded, 2=fully occluded, 3=unknown
    #self.alpha = data[3] # object observation angle [-pi..pi]

    # extract 2d bounding box in 0-based coordinates
    self.xmin = int(data[1]) # left
    self.ymin = int(data[2]) # top
    self.xmax = int(data[3]) # right
    self.ymax = int(data[4]) # bottom
    self.box2d = np.array([self.xmin,self.ymin,self.xmax,self.ymax])

    # extract 3d bounding box information
   # self.h = data[8] # box height
    #self.w = data[9] # box width
    #self.l = data[10]  # box length (in meters)
   # self.t = (data[11],data[12],data[13]) # location (x,y,z) in camera coord.
    #self.ry = data[14] # yaw angle (around Y-axis in camera coordinates) [-pi..pi]

if __name__ == "__main__":
    # Load the Dataset
    testset = KITTIDetection(KITTI_ROOT,['train'], None, KITTIAnnotationTransform)

    # Necessary Directories
    root_dir="/home/dllab/kitti_object/data_object_image_2"
    pcd_dir="/home/dllab/kitti_object/data_object_velodyne/pcl"
    data_set = "training"
    images_dir = os.path.join(root_dir,data_set, "image_{0}".format(2))
    detection_dir = '/home/emeka/Schreibtisch/AIS/ais3d/Detections'
    calib_dir = '/home/dllab/kitti_object/data_object_velodyne/data_object_calib/training/calib'

    # Assign 1 to visualize the images and PCD
    show_images=0

    # Iterate for every image
    for img_idx in range(1,len(testset)):
        # Get the real image index (used in file names etc.)
        img_real_id=testset.img_id_return(img_idx)

        #Delete the 0s before the number
        if img_real_id == '000000':
            pcd_id = '0'
        else:
            pcd_id = img_real_id.lstrip('0') # without 0

        #Read Cloud & Convert it to array
        cloud = pcl.load_XYZI(os.path.join(pcd_dir,'{0}.pcd'.format(pcd_id)))
        points_array = np.asarray(cloud)

        #Read Calibration Matrices & Detected objects
        Tr_velo_to_cam, R0_rect, P2 = readCalibration(calib_dir,img_real_id)
        objects = readDetections(detection_dir,img_real_id)

        filtered_points_array = []

        # Show the boxes on the test image
        if show_images == 1:
            image = testset.pull_image(img_idx)
            for index in range(0,len(objects)):
                obj=objects[index]
                cv2.rectangle(image,(obj.xmin,obj.ymin),(obj.xmax,obj.ymax),(0,255,0),2)
            cv2.imshow("test image", image)
            cv2.waitKey(1)& 0xFF

        filename = '/home/emeka/Schreibtisch/AIS/ais3d/PCD_Files1/DetectionLocations/'+'{}.txt'.format(testset.img_id_return(img_idx))
        f = open(filename,'w')

        # Check if the Point is inside of the Box
        for ind in range(0,points_array.shape[0]):
            y = np.matrix([[points_array[ind][0]],[points_array[ind][1]],[points_array[ind][2]],[1.0]]);
            Tr_y = Tr_velo_to_cam*y
            if Tr_y[2] > 0:
                X = P2 * R0_rect * Tr_y
                #FOR LOOP FOR ALL  OBJECTS
                for index in range(0,len(objects)):
                    obj=objects[index]
                    if ( ( obj.xmin < X[0]/X[2] < obj.xmax ) and ( obj.ymin < X[1]/X[2] < obj.ymax ) ):
                        filtered_points_array.append(points_array[ind])
                        f.write('{} \n'.format(points_array[ind]))
        f.close()
        # Save the Points to a PCD file if the points exist
        if(len(filtered_points_array) > 0):
            outcloud = pcl.PointCloud_PointXYZI(np.array(filtered_points_array, dtype=np.float32))
            #DONT CHANGE NAMES BECAUSE OF CPP CODE
            pcl.save(outcloud, "/home/emeka/Schreibtisch/AIS/ais3d/PCD_Files1/segmented_{}.pcd".format(pcd_id))
            print('Cloud saved')
            if show_images == 1:
                os.system("/home/emeka/Schreibtisch/AIS/deleteme/build/test_pcl {}".format(pcd_id))
        if show_images == 1:
            cv2.destroyAllWindows()





