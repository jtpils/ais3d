from __future__ import print_function
import argparse
import os
import random
import numpy as np

import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils

import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data

from torch.autograd import Variable
from datasets import PartDataset
from pointnet import PointNetDenseCls
import torch.nn.functional as F



parser = argparse.ArgumentParser()
parser.add_argument('--batchSize', type=int, default=8, help='input batch size')
parser.add_argument('--workers', type=int, help='number of data loading workers', default=4)
parser.add_argument('--nepoch', type=int, default=25, help='number of epochs to train for')
parser.add_argument('--outf', type=str, default='seg',  help='output folder')
parser.add_argument('--model', type=str, default = '',  help='model path')


opt = parser.parse_args()
print (opt)

#opt.manualSeed = random.randint(1, 10000) # fix seed
#print("Random Seed: ", opt.manualSeed)
#random.seed(opt.manualSeed)
#torch.manual_seed(opt.manualSeed)

dataset = PartDataset( classification = False)
dataloader = torch.utils.data.DataLoader(dataset, batch_size=opt.batchSize,
                                          shuffle=True)#, num_workers=int(opt.workers)

test_dataset = PartDataset( classification = False, class_choice = ['Chair'], train = False)
testdataloader = torch.utils.data.DataLoader(test_dataset, batch_size=opt.batchSize,
                                          shuffle=True, num_workers=int(opt.workers))

print(len(dataset), len(test_dataset))
num_classes = dataset.num_seg_classes
print('classes', num_classes)
try:
    os.makedirs(opt.outf)
except OSError:
    pass

blue = lambda x:'\033[94m' + x + '\033[0m'


classifier = PointNetDenseCls(k = num_classes)

if opt.model != '':
    classifier.load_state_dict(torch.load(opt.model))

optimizer = optim.SGD(classifier.parameters(), lr=0.01, momentum=0.9)
classifier.cuda()

num_batch = len(dataset)/opt.batchSize

for epoch in range(opt.nepoch):
    for i, data in enumerate(dataloader):
        #label_filename = "{}/{}.txt".format('/home/emeka/Schreibtisch/AIS/ais3d/PCD_Files/Labeled',dataset.ids[i] )
        #if not os.path.isfile(label_filename):
        #   print('PASS')
            #continue

        points, target = data
        #print(*points, sep='\n')
        #print('1. Points{} , Target={} '.format(points.shape,target.shape))
        points, target = Variable(points), Variable(target)
        #print('2. Points{} , Target={} '.format(points.shape,target.shape))
        points = points.transpose(2,1)
        #print('3. Points{} , Target={} '.format(points.shape,target.shape))
        points, target = points.cuda(), target.cuda()
        #print('4. Points{} , Target={} '.format(points.shape,target.shape))
        optimizer.zero_grad()
        pred, _ = classifier(points)
        pred = pred.view(-1, num_classes)
        target = target.view(-1,1)[:,0] - 1
        #print('4. Points{} , Target={} '.format(points.shape,target.shape))
        #print(pred.size(), target.size())
        #both vectors should be nx4 dimentions. target is one hot encoding with ground truth and prediction is nx4.
        loss = F.nll_loss(pred, target)
        loss.backward()
        optimizer.step()
        pred_choice = pred.data.max(1)[1]
        correct = pred_choice.eq(target.data).cpu().sum()
        print('[%d: %d/%d] train loss: %f accuracy: %f' %(epoch, i, num_batch, loss, correct/float(opt.batchSize * 2500)))
        
        if i % 10 == 0:
            j, data = next(enumerate(testdataloader, 0))
            points, target = data
            points, target = Variable(points), Variable(target)
            points = points.transpose(2,1) 
            points, target = points.cuda(), target.cuda()   
            pred, _ = classifier(points)
            pred = pred.view(-1, num_classes)
            target = target.view(-1,1)[:,0] - 1
            #last layer should be log softmax
            loss = F.nll_loss(pred, target)
            pred_choice = pred.data.max(1)[1]
            correct = pred_choice.eq(target.data).cpu().sum()
            print('[%d: %d/%d] %s loss: %f accuracy: %f' %(epoch, i, num_batch, blue('test'), loss, correct/float(opt.batchSize * 2500)))
    
    torch.save(classifier.state_dict(), '%s/seg_model_%d.pth' % (opt.outf, epoch))
