#################################### train single image ######################################
# import json
# import utils
# from GazeDirectionPathway import GazeDirectionNet 
# import cv2
# import torch
# import torch.nn as nn
# from torchvision import transforms
# import os
# import torch.optim as optim
# os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

# MIT_DATA_PATH = 'example_data/MIT_annotation.txt'
# MIT_ORIGINAL_PATH = 'example_data/MIT_original.jpg'


# def GDLoss(direction, gt_direction):
# 	cosine_similarity = nn.CosineSimilarity()
# 	gt_direction = gt_direction.unsqueeze(0)
# 	# print(direction, gt_direction)
# 	loss = torch.mean(1 - cosine_similarity(direction, gt_direction))
# 	return loss

# with open(MIT_DATA_PATH,'r') as ann:
#     data_mit = ann.read()
# # print("MIT:",data_mit)
# # image_transforms = transforms.Compose([transforms.Resize((224, 224)),
# # 									  transforms.ToTensor(),
# # 									  transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

# # head_transforms = transforms.Compose([transforms.Resize((224, 224)),
# # 									  transforms.ToTensor(),
# # 									  transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

# ann = utils.MIT_extract_annotation_as_dict(data_mit)
# # print(ann)
# hx, hy = ann['eye_x'], ann['eye_y']
# # print(hx,hy)
# # image = cv2.imread(MIT_ORIGINAL_PATH, cv2.IMREAD_COLOR)
# # print(image)
# head_img = utils.get_head_img(MIT_ORIGINAL_PATH,ann,0)
# head_img = head_img.resize((224,224))
# head_img = transforms.ToTensor()(head_img)
# head_img = head_img.unsqueeze(0)

# head_pos =  torch.Tensor([hx,hy])
# head_pos = head_pos.unsqueeze(0)

# direction_gt = utils.get_gaze_direction_GT(hx,hy,ann['gaze_x'],ann['gaze_y'])
# direction_gt = torch.from_numpy(direction_gt)
# print(direction_gt)


# net = GazeDirectionNet() 
# print("train")
# learning_rate = 0.8
# optimizer = optim.Adam([{'params': net.head_feature_net.parameters(), 
# 							'initial_lr': learning_rate},
# 							{'params': net.head_feature_process.parameters(), 
# 							'initial_lr': learning_rate},
# 							{'params': net.head_pos_net.parameters(), 
# 							'initial_lr': learning_rate},
# 							{'params': net.concatenate_net.parameters(), 
# 							'initial_lr': learning_rate}],
# 							lr=learning_rate, weight_decay=0.0001)
# epoch = 500
# outputlist = []
# for i in range(epoch):
# 	print(i)
# 	optimizer.zero_grad()
# 	output = net([head_img,head_pos])
# 	loss = GDLoss(output,direction_gt)
# 	print(loss.data)
# 	loss.backward()	
# 	optimizer.step()


# print(output,direction_gt)
#################################### train single image ######################################

#################################### train on dataset   ######################################
# running train
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from scipy import signal
import numpy as np
from PIL import Image
import cv2
from tqdm import tqdm
# preprocess
import json
import torch.nn as nn
import torch.optim as optim
from GazeDirectionPathway import GazeDirectionNet
import matplotlib.pyplot as plt
import utils
import os
image_transforms = transforms.Compose([transforms.Resize((224, 224)),
									   transforms.ToTensor(),
									   transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

head_transforms = transforms.Compose([transforms.Resize((224, 224)),
									  transforms.ToTensor(),
									  transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

class SVIPDataset(Dataset):
	def __init__(self, root_dir, ann_file):
		self.root_dir = root_dir
		with open(root_dir + ann_file) as f:
			self.anns = json.load(f)
		self.image_num = len(self.anns)
	def __len__(self):
		# return 2
		length = self.image_num
		#length = 1
		return length

	def __getitem__(self,idx):
		ann = self.anns[idx]

		img = cv2.imread(self.root_dir + ann['path'], cv2.IMREAD_COLOR)
		#image
		# image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
		# image = Image.fromarray(image)
		# image = image_transforms(image)
		#head image
		head_image = self.get_head_img(img,ann)
		#head position
		head_pos = ann['head_position']
		#gaze direction
		

		d = np.array([ann['gaze_point'][0] - head_pos[0], ann['gaze_point'][1] - head_pos[1]])
		gaze_dir = d/np.linalg.norm(d)
		# gaze_dir = ann['gaze_direction']
		#gaze_direction_field
		# gdf = self.get_direction_field(head_pos[0],head_pos[1],gaze_dir)
		# gdf = torch.from_numpy(gdf).unsqueeze(0)
		# gdf_2 = torch.pow(gdf,2)
		# gdf_5 = torch.pow(gdf,5)
		#gaze point
		# gaze = ann['gaze_point']
		#heatmap
		# heatmap = self.get_heatmap_GT(gaze[0],gaze[1])

		sample = {
				  'head_image':head_image,
				  'head_position':torch.FloatTensor(head_pos),
				  'gaze_direction':torch.from_numpy(gaze_dir),
		}
		# print(sample["gaze_positon"])
		return sample

	def get_head_img(self,image,annotation):
		h,w,_ = image.shape
		x_0 = int(w*annotation['x_init'])
		x_1 = int(w*(annotation['x_init']+annotation['w']))
		y_0 = int(h*annotation['y_init'])
		y_1 = int(h*(annotation['y_init']+annotation['h']))
		face_image = image[y_0:y_1, x_0:x_1,:]
		face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
		face_image = Image.fromarray(face_image)
		# face_image.show()
		face_image = head_transforms(face_image)
		return face_image

	def get_direction_field(self,head_x,head_y,gaze_direction,gamma=1):
		head_x = int(224 * head_x)
		head_y = int(224 * head_y)
		field = np.zeros((224,224))
		for idx_y,row in enumerate(field):
			for idx_x,pix in enumerate(row):
				d = np.array([idx_x - head_x, idx_y - head_y])
				G = d/np.linalg.norm(d)
				field[idx_y,idx_x] = max(G[0] * gaze_direction[0] + G[1] * gaze_direction[1],0)
		return field

	def get_heatmap_GT(self,gaze_x,gaze_y,kernlen=21, std=3):
		'''Get ground truth heatmap or (51,9)
		'''
		gkern1d = signal.gaussian(kernlen, std=std).reshape(kernlen, 1)
		kernel_map = np.outer(gkern1d, gkern1d)

		gaze_x = int(224*gaze_x)
		gaze_y = int(224*gaze_y)
		
		k_size = kernlen // 2

		x1, y1 = gaze_x - k_size, gaze_y - k_size
		x2, y2 = gaze_x + k_size, gaze_y + k_size

		h, w = 224,224
		if x2 >= w:
			w = x2 + 1
		if y2 >= h:
			h = y2 + 1
		heatmap = np.zeros((h, w))
		left, top, k_left, k_top = x1, y1, 0, 0
		if x1 < 0:
			left = 0
			k_left = -x1
		if y1 < 0:
			top = 0
			k_top = -y1

		heatmap[top:y2+1, left:x2+1] = kernel_map[k_top:, k_left:]
		return heatmap[:224, :224]

def GDLoss(direction, gt_direction):
	cosine_similarity = nn.CosineSimilarity()
	#gt_direction = gt_direction.unsqueeze(0)
	#print("gdloss",direction, gt_direction)
	loss = torch.mean(1 - cosine_similarity(direction, gt_direction))
	return loss
def LossPlot(lst,plotname,folder):
	x = np.linspace(1,len(lst),len(lst))
	plt.figure()
	plt.plot(x,lst)
	if not os.path.exists(folder):    
		print("notexist")         
		os.makedirs(folder)
	plt.savefig(folder + '/' + plotname + '.jpg')

def writeLoss(lst,path):
	with open(path,'w') as f:
		json.dump(lst,f)
def main():
	net = GazeDirectionNet()
	print("train")
	learning_rate = 0.0001
	optimizer = optim.Adam([{'params': net.head_feature_net.parameters(),
							 'initial_lr': learning_rate},
							{'params': net.head_feature_process.parameters(),
							 'initial_lr': learning_rate},
							{'params': net.head_pos_net.parameters(),
							 'initial_lr': learning_rate},
							{'params': net.concatenate_net.parameters(),
							 'initial_lr': learning_rate}],
						   lr=learning_rate, weight_decay=0.0001)

	train_set = SVIPDataset(root_dir='data/SVIP/',
                           ann_file='SVIP_annotation.json')
	bs = 5
	train_data_loader = DataLoader(train_set, batch_size=bs,
                                   shuffle=False, num_workers=1)
	TotalLossList = []
	MeanLossList = []
	epoch = 5
	scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1, last_epoch=-1)
	#scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10, verbose=False, threshold=0.001, threshold_mode='rel', cooldown=0, min_lr=0, eps=1e-08)
	#verbose=true: print the lr
	#adjust lr: https://blog.csdn.net/m0_37531129/article/details/107794136
	pretrained = 'pretrained'
	train_param = 'batchsize_' + str(bs) + '_lr_' + str(learning_rate) + '_' + str(epoch) + '_epoch_' + pretrained
	if not os.path.exists(train_param):    
		print("notexist")         
		os.makedirs(train_param)
	for j in range(epoch):
		LossList = []
		epochName = str(j) + 'th_epoch'
		scheduler.step()
		for i, data in tqdm(enumerate(train_data_loader)):
			head_image = data['head_image']
			head_position = data['head_position']
			gaze_direction = data['gaze_direction']
			#print(gaze_direction)
			#print("!!!!!!!!:",gaze_direction)
			optimizer.zero_grad()
			output = net([head_image, head_position])
			#print("!!!!!!!!:",output)
			#print("!!!",output.size, gaze_direction.size)
			loss = GDLoss(output, gaze_direction)
			loss.backward()
			#optimizer.step()
			optimizer.step()
			print("output:",output.data,"groundtruth:",gaze_direction.data)
			print("lr:",learning_rate,"loss:",loss.data)
			
			LossList.append(float(loss.data.numpy()))
			#print("???????????",loss.data.numpy())
		#netpath = train_param + '/' + epochName +'.pth'
		
		#LossPlot(LossList,epochName,netpath + '/loss')
		TotalLossList.append(LossList)
		#print(LossList)
	#print(TotalLossList)
	MeanLossList = [np.mean(epochList) for epochList in TotalLossList]
	writeLoss(MeanLossList,train_param + '/' + 'meanloss.json')
	writeLoss(TotalLossList,train_param + '/' + 'loss.json')
	netpath = train_param + '/' + str(epoch) +'epoch.pth'
	torch.save(net.state_dict(),netpath)
	
	#LossPlot(MeanLossList,'meanloss_'+ str(epoch) + 'epoches',train_param)
if __name__ == '__main__':
    main()
#################################### train on dataset   ######################################