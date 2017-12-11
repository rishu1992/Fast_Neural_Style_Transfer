import torch 
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
from torch import optim

import torchvision
from torchvision import transforms, models
from torch.utils.data import Dataset

from PIL import Image
import copy

class ResidualBlock(nn.Module):
	def __init__(self, in_channels, out_channels, stride=1):
		super(ResidualBlock, self).__init__()
		self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, 
					 stride=stride, padding=1, bias=False)
		self.bn1 = nn.InstanceNorm2d(out_channels)
		self.relu = nn.ReLU(inplace=True)
		self.conv2 = nn.Conv2d(in_channels, out_channels, kernel_size=3, 
					 stride=stride, padding=1, bias=False)
		self.bn2 = nn.InstanceNorm2d(out_channels)
		
	def forward(self, x):
		residual = x
		out = self.conv1(x)
		out = self.bn1(out)
		out = self.relu(out)
		out = self.conv2(out)
		out = self.bn2(out)
		out += residual
		# out = self.relu(out)
		return out

class ImageTransformationNetwork(nn.Module):
	def __init__(self, img_size):
		super(ImageTransformationNetwork, self).__init__()
		self.img_size = img_size
		self.conv1 = nn.Conv2d(3, 32, kernel_size=9, stride=1, padding=4)
		self.bn1 = nn.InstanceNorm2d(32)
		self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)
		self.bn2 = nn.InstanceNorm2d(64)
		self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1)
		self.bn3 = nn.InstanceNorm2d(128)
		self.res1 = ResidualBlock(128,128)
		self.res2 = ResidualBlock(128,128)
		self.res3 = ResidualBlock(128,128)        
		self.res4 = ResidualBlock(128,128)
		self.res5 = ResidualBlock(128,128)		
		self.conv4 = nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1)
		self.bn4 = nn.InstanceNorm2d(64)
		self.conv5 = nn.ConvTranspose2d(64, 32, kernel_size=3, stride=2, padding=1)
		self.bn5 = nn.InstanceNorm2d(32)
		self.conv6 = nn.Conv2d(32, 3, kernel_size=9, stride=1, padding=4)
		self.bn6 = nn.InstanceNorm2d(3)
		self.tanh = nn.Tanh()
		self.relu = nn.ReLU(inplace=True)

	def forward(self,x):
		out = self.relu(self.bn1(self.conv1(x)))
		out = self.relu(self.bn2(self.conv2(out)))
		out = self.relu(self.bn3(self.conv3(out)))
		out = self.res1(out)
		out = self.res2(out)
		out = self.res3(out)
		out = self.res4(out)
		out = self.res5(out)
		out = self.relu(self.bn4(self.conv4(out, output_size=(self.img_size//2,self.img_size//2))))
		out = self.relu(self.bn5(self.conv5(out, output_size=(self.img_size,self.img_size))))
		out = self.tanh(self.bn6(self.conv6(out)))
		# out.data[:,0,:,:].add_(1).div_(2).mul_(255)
		# out.data[:,1,:,:].add_(1).div_(2).mul_(255)
		# out.data[:,2,:,:].add_(1).div_(2).mul_(255) 
		out = torch.add(out,1)
		out = torch.div(out,2)
		out = torch.mul(out,255)
		
		return out


class TrainDataset(Dataset):
	"""Dataset wrapping data and target tensors.

	Each sample will be retrieved by indexing both tensors along the first
	dimension.

	Arguments:
		data_tensor (Tensor): contains sample data.
		target_tensor (Tensor): contains sample targets (labels).
	"""

	def __init__(self, data_tensor):
		self.data_tensor = data_tensor

	def __getitem__(self, index):

		return self.data_tensor[index]

	def __len__(self):
		return len(self.data_tensor)



class VGG16(nn.Module):
	def __init__(self):
		super(VGG16, self).__init__()

		original_model = models.vgg16(pretrained=True).features
		
		self.layer1 = nn.Sequential(*list(original_model.children())[:4])
		self.layer2 = nn.Sequential(*list(original_model.children())[5:9])
		self.layer3 = nn.Sequential(*list(original_model.children())[10:16])
		self.layer4 = nn.Sequential(*list(original_model.children())[17:23])
		self.pool1 = nn.AvgPool2d(kernel_size=2, stride=2)
		self.pool2 = nn.AvgPool2d(kernel_size=2, stride=2)
		self.pool3 = nn.AvgPool2d(kernel_size=2, stride=2)			
				   
	def forward(self, x):
		l1 = self.layer1(x)
		l2 = self.layer2(self.pool1(l1))
		l3 = self.layer3(self.pool2(l2))
		l4 = self.layer4(self.pool3(l3))
		return [l1,l2,l3,l4]
