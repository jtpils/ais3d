from __future__ import print_function
import sys
import os
import argparse
import torch
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
from torch.autograd import Variable
from data import KITTI_ROOT, VOC_ROOT, VOC_CLASSES, KITTI_CLASSES as labelmap
from PIL import Image
from data import VOCAnnotationTransform, KITTIAnnotationTransform, VOCDetection, KITTIDetection, BaseTransform, VOC_CLASSES, KITTI_CLASSES
import torch.utils.data as data
from ssd import build_ssd
import matplotlib.pyplot as plt
import time
parser = argparse.ArgumentParser(description='Single Shot MultiBox Detection')
#parser.add_argument('--trained_model', default='weights/ssd_300_VOC0712.pth',
#                    type=str, help='Trained state_dict file path to open')
parser.add_argument('--trained_model', default='/home/emeka/Schreibtisch/AIS/ais3d/ssd.pytorch-master/weights/ssd300_Resz_KITTI_80000.pth',
                    type=str, help='Trained state_dict file path to open')
parser.add_argument('--save_folder', default='eval/', type=str,
                    help='Dir to save results')
parser.add_argument('--visual_threshold', default=0.5, type=float,
                    help='Final confidence threshold')
parser.add_argument('--cuda', default=True, type=bool,
                    help='Use cuda to train model')
parser.add_argument('--kitti_root', default=KITTI_ROOT, help='Location of root directory')
parser.add_argument('-f', default=None, type=str, help="Dummy arg so we can load in Jupyter Notebooks")
args = parser.parse_args()

if args.cuda and torch.cuda.is_available():
    torch.set_default_tensor_type('torch.cuda.FloatTensor')
else:
    torch.set_default_tensor_type('torch.FloatTensor')

if not os.path.exists(args.save_folder):
    os.mkdir(args.save_folder)


def bb_intersection_over_union(boxA, boxB):
    # determine the (x, y)-coordinates of the intersection rectangle

    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    # compute the area of intersection rectangle
    interArea = (xB - xA) * (yB - yA)

    # compute the area of both the prediction and ground-truth
    # rectangles
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = interArea / float(boxAArea + boxBArea - interArea)
    if iou < 0:
        iou = 0;
    # return the intersection over union value
    return iou


def test_net(save_folder, net, cuda, testset, transform, thresh):
    # dump predictions and assoc. ground truth to text file for now
    #filename = save_folder+'test1.txt'
    lower_limit = 0.0;
    pre_car = []
    pre_ped = []
    pre_cyc = []
    rec_car = []
    rec_ped = []
    rec_cyc = []
    thrS = [0.5,0.7,0.5]
    for ind in range(40):
        print('Lower Limit: {:.3f}'.format(lower_limit))
        num_images = len(testset)
        #we zero tp,fp, fn
        tp_car = 0
        tp_ped = 0
        tp_cyc = 0
        fp_car = 0
        fp_ped = 0
        fp_cyc = 0
        fn_car = 0
        fn_ped = 0
        fn_cyc = 0

        for i in range(num_images):
            if (i+1) % 10 == 0:
                print('Testing image {:d}/{:d}....'.format(i+1, num_images))
            img = testset.pull_image(i)
            img_id, annotation = testset.pull_anno(i)
            x = torch.from_numpy(transform(img)[0]).permute(2, 0, 1)
            x = Variable(x.unsqueeze(0))

            #with open(filename, mode='a') as f:
                #f.write('\nGROUND TRUTH FOR: '+img_id+'\n')
                #for box in annotation:
                    #f.write('label: '+' || '.join(str(b) for b in box)+'\n')
                    #the line below is the actual class from the original image
                    #print(box[4])
            if cuda:
                x = x.cuda()
            t = time.time()
            y = net(x)      # forward pass
            elapsed = time.time() - t
            print ('Forward pass time: {}'.format(elapsed))
            detections = y.data
            # scale each detection back up to the image
            scale = torch.Tensor([img.shape[1], img.shape[0],
                                 img.shape[1], img.shape[0]])
            pred_num = 0
            for i in range(detections.size(1)):
                j = 0
                cycDum=0
                carDum=0
                pedDum=0
                #this line under is looping all the dections
                while detections[0, i, j, 0] > lower_limit:
                    if (i-1) == 0: #cyc
                        cycDum=1
                        carDum=0
                        pedDum=0
                    if (i-1) == 1: #car
                        cycDum=0
                        carDum=1
                        pedDum=0
                    if (i-1) == 2: #ped
                        cycDum=0
                        carDum=0
                        pedDum=1
                    #if pred_num == 0:
                        #with open(filename, mode='a') as f:
                            #f.write('PREDICTIONS: '+'\n')
                    score = detections[0, i, j, 0]
                    label_name = labelmap[i-1]
                    pt = (detections[0, i, j, 1:]*scale).cpu().numpy()
                    coords = (pt[0], pt[1], pt[2], pt[3])
                    #print('prediction box is pt[0]={}, pt[1]={},, pt[2]={},, pt[3]={}, '.format(pt[0], pt[1], pt[2], pt[3]))
                    #this line under is
                    for box in annotation:
                        #the line below is the actual class from the original image
                     #   print('class number is ' + str(box[4]))
                     #   print([box[0], box[1],box[2], box[3]],[pt[0], pt[1], pt[2], pt[3]])
                        if (i-1) == box[4]:
                            intres = bb_intersection_over_union([box[0], box[1],box[2], box[3]],[pt[0], pt[1], pt[2], pt[3]])
                            if intres > thrS[i-1]:
                    #            print(intres)
                                if (i-1) == 0: #cyc
                                    cycDum=0
                                if (i-1) == 1: #car
                                    carDum=0
                                if (i-1) == 2: #ped
                                    pedDum=0
                    fp_car += carDum
                    fp_ped += pedDum
                    fp_cyc += cycDum
                    pred_num += 1
                    #with open(filename, mode='a') as f:
                    #    f.write(str(pred_num)+' label: '+label_name+' score: ' +
                    #            str(score) + ' '+' || '.join(str(c) for c in coords) + '\n')
                    #    #the line below is the prediction
                    #    print(label_name)
                    j += 1
            #print(fp_car)
            #print(fp_ped)
            #print(fp_cyc)

            for box in annotation:
                cycDum=0
                carDum=0
                pedDum=0
                if box[4] == 0: #cyc
                    cycDum=1
                    carDum=0
                    pedDum=0
                if box[4] == 1: #car
                    cycDum=0
                    carDum=1
                    pedDum=0
                if box[4] == 2: #ped
                    cycDum=0
                    carDum=0
                    pedDum=1
                for i in range(detections.size(1)):
                    j = 0
                    #this line under is looping all the dections
                    while detections[0, i, j, 0] > lower_limit:

                        score = detections[0, i, j, 0]
                        label_name = labelmap[i-1]
                        pt = (detections[0, i, j, 1:]*scale).cpu().numpy()
                        coords = (pt[0], pt[1], pt[2], pt[3])
                        if (i-1) == box[4]:
                            intres = bb_intersection_over_union([box[0], box[1],box[2], box[3]],[pt[0], pt[1], pt[2], pt[3]])
                            #print([box[0], box[1],box[2], box[3]],[pt[0], pt[1], pt[2], pt[3]])
                            #print(intres)
                            if intres > thrS[i-1]:
                                if (i-1) == 0: #cyc
                                    tp_cyc+=1
                                    cycDum=0
                                    #break
                                if (i-1) == 1: #car
                                    tp_car+=1
                                    carDum=0
                                    #break
                                if (i-1) == 2: #ped
                                    tp_ped+=1
                                    pedDum=0
                                    #break

                        j += 1
                fn_car += carDum
                fn_ped += pedDum
                fn_cyc += cycDum
            elapsed = time.time() - t
            print ('Total time: {}'.format(elapsed))
            #print('FN')
            #print(fn_car)
            #print(fn_ped)
            #print(fn_cyc)

        #here we have to compute the 3 vectors.. by using append in the end
        lower_limit = lower_limit+0.025
        pre_car.append(tp_car/(tp_car+fp_car))
        if (tp_ped+fp_ped)>0:
            pre_ped.append(tp_ped/(tp_ped+fp_ped))
        else:
            pre_ped.append(0)
        if (tp_cyc+fp_cyc)>0:
            pre_cyc.append(tp_cyc/(tp_cyc+fp_cyc))
        else:
            pre_cyc.append(0)
        rec_car.append(tp_car/(tp_car+fn_car))
        rec_ped.append(tp_ped/(tp_ped+fn_ped))
        rec_cyc.append(tp_cyc/(tp_cyc+fn_cyc))

    plt.plot(rec_car, pre_car,color='green', label='car')
    plt.plot(rec_ped, pre_ped,color='blue', label='pedestrian')
    plt.plot(rec_cyc, pre_cyc,color='red', label='cyclist')
    plt.ylabel('Precision')
    plt.xlabel('recall')
    plt.legend( loc=1)
    plt.savefig('pr.png')
    plt.show()
    plt.hold(True)


def test_kitti():
    # load net
    num_classes = len(KITTI_CLASSES) + 1 # +1 background
    net = build_ssd('test', 300, num_classes) # initialize SSD
    net.load_state_dict(torch.load(args.trained_model))
    net.eval()
    print('Finished loading model!')
    # load data
    testset = KITTIDetection(KITTI_ROOT,['val'], None, KITTIAnnotationTransform())
    if args.cuda:
        net = net.cuda()
        print('test')
        cudnn.benchmark = True
    # evaluation
    test_net(args.save_folder, net, args.cuda, testset, BaseTransform(net.size, (104, 117, 123)),thresh=args.visual_threshold)

if __name__ == '__main__':
    test_kitti()
    #print(bb_intersection_over_union([0,0,10,10],[0,0,0,0]))
