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

parser = argparse.ArgumentParser(description='Single Shot MultiBox Detection')
#parser.add_argument('--trained_model', default='weights/ssd_300_VOC0712.pth',
#                    type=str, help='Trained state_dict file path to open')
parser.add_argument('--trained_model', default='/home/emeka/Schreibtisch/AIS/ais3d/ssd.pytorch-master/weights/trainval/ssd300_KITTI_110000.pth',
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


def test_net(save_folder, net, cuda, testset, transform, thresh):
    # dump predictions and assoc. ground truth to text file for now
    filename = save_folder+'test1.txt'
    num_images = len(testset)
    for i in range(num_images):
        print('Testing image {:d}/{:d}....'.format(i+1, num_images))
        img = testset.pull_image(i)
        img_id, annotation = testset.pull_anno(i)
        x = torch.from_numpy(transform(img)[0]).permute(2, 0, 1)
        x = Variable(x.unsqueeze(0))

        with open(filename, mode='a') as f:
            f.write('\nGROUND TRUTH FOR: '+img_id+'\n')
            for box in annotation:
                f.write('label: '+' || '.join(str(b) for b in box)+'\n')
                #the line below is the actual class
                print(box[4])
        if cuda:
            x = x.cuda()

        y = net(x)      # forward pass
        detections = y.data
        # scale each detection back up to the image
        scale = torch.Tensor([img.shape[1], img.shape[0],
                             img.shape[1], img.shape[0]])
        pred_num = 0
        for i in range(detections.size(1)):
            j = 0
            while detections[0, i, j, 0] >= 0.6:
                if pred_num == 0:
                    with open(filename, mode='a') as f:
                        f.write('PREDICTIONS: '+'\n')
                score = detections[0, i, j, 0]
                label_name = labelmap[i-1]
                pt = (detections[0, i, j, 1:]*scale).cpu().numpy()
                coords = (pt[0], pt[1], pt[2], pt[3])
                pred_num += 1
                with open(filename, mode='a') as f:
                    f.write(str(pred_num)+' label: '+label_name+' score: ' +
                            str(score) + ' '+' || '.join(str(c) for c in coords) + '\n')
                    #the line below is the prediction
                    print(label_name)
                j += 1


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
