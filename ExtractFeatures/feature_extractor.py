import cv2
import numpy as np
import lmdb
import sys
import glob
import errno
import os
import csv
import random
import h5py
import caffe
import argparse

class ReIDDataLayer():
	def __init__(self, orginal_dir, posebox_dir, feature_dir, testOrTrain):
		orginal_dir = orginal_dir
		posebox_dir = posebox_dir
		feature_dir = feature_dir
		self.testOrTrain = testOrTrain
		
		file_list = glob.glob(posebox_dir + '/*.jpg')
	 	orginal_file_list = glob.glob(orginal_dir + '/*.jpg')
	 	assert(len(file_list) == len(orginal_file_list))

		# initalize fileID 2 personID mapping
		fileID2labelID = {}
		filedIDCounter = {}
		with open(feature_dir) as csvfile:
	 		reader = csv.DictReader(csvfile)
		 	for row in reader:
		 		file_name = row['file_name']
		 		if filedIDCounter.get(file_name[0:4]) == None:
					filedIDCounter[file_name[0:4]] = 1.0
				else:
					filedIDCounter[file_name[0:4]] = filedIDCounter[file_name[0:4]] + 1.0

		for key in filedIDCounter:
			#print(filedIDCounter[key])
			filedIDCounter[key] = filedIDCounter[key] * 1.0



		# build datalist
		file_counter = 0
		self.train_data_list = list()
		self.test_data_list = list()
		all_data_list = list()

	 	counter = 0
		with open(feature_dir) as csvfile:
	 		reader = csv.DictReader(csvfile)
		 	for row in reader:
		 		file_name = row['file_name']

		 		data_entry = list()
		 		data_entry.append( posebox_dir+'/'+file_name )

		 		data_entry.append( orginal_dir+'/'+file_name )

		 		conf = np.zeros((12,))

		 		#symmtric configureation
				conf[0] = row['Rshoulder_confidence']
				conf[1] = row['Rhip_confidence']
				conf[2] = row['Rknee_confidence']
				conf[3] = row['Rankle_confidence']
				conf[4] = row['Relbow_confidence']
				conf[5] = row['Rwrist_confidence']

				conf[6] = row['Lwrist_confidence']
				conf[7] = row['Lelbow_confidence']
				conf[8] = row['Lankle_confidence']
				conf[9] = row['Lknee_confidence']
				conf[10] = row['Lhip_confidence']
				conf[11] = row['Lshoulder_confidence']
				data_entry.append(conf.reshape((1,12)))

		 		if fileID2labelID.get(file_name[0:4]) == None:
					fileID2labelID[file_name[0:4]] = len(fileID2labelID)+1

		 		# label = np.zeros((751,))
		 		# label[fileID2labelID[file_name[0:4]] -1 ] = 1
		 		label = np.zeros((1,)).astype(int)
		 		label[0] = fileID2labelID[file_name[0:4]] -1
		 		data_entry.append(label.reshape(1,1))
		 		
		 		data_entry.append(file_name)

		 		all_data_list.append(data_entry)

		 		counter = counter + 1

		# random val & train data

		# random.shuffle(all_data_list)
		for entry in all_data_list:
		 	file_name = entry[-1]
		 	if filedIDCounter[file_name[0:4]] > 0:
		 		self.train_data_list.append(entry)
		 		filedIDCounter[file_name[0:4]] = filedIDCounter[file_name[0:4]] - 1
		 	else:
		 		self.test_data_list.append(entry)

		print('Test Data List Size: '+ str(len(self.test_data_list)))
		print('Train Data List Size: '+ str(len(self.train_data_list)))
		

	def size(self):
		if self.testOrTrain == 'train':
			return len(self.train_data_list)
		else:
			return len(self.test_data_list)


def get_feature(img, pose, conf):
	net.blobs['pose_data'].data[...] = pose
	net.blobs['orig_data'].data[...] = img
	print(pose.shape)
	print(img.shape)
	print(conf)
	net.blobs['conf_scores'].data[...] = conf.reshape((1,12,1,1))

	net.forward()
	poseBox_fc751 = net.blobs['poseBox_fc8_'].data[0]
	origImg_fc751 = net.blobs['origImg_fc8_'].data[0]
	overall_fc751 = net.blobs['overall_fc751'].data[0]

	concat = net.blobs['concat'].data[0]
   # print type(scores)
	print poseBox_fc751.shape
	print origImg_fc751.shape
	print overall_fc751.shape
	print concat.shape

	return origImg_fc751, poseBox_fc751, overall_fc751, concat

if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument('--caffemodel', help='the path of caffemodel')
        parser.add_argument('--orig_data', help='the path of original data')
        parser.add_argument('--pose_data', help='the path of posebox data')
        parser.add_argument('--csv_list', help='the csv file that stores the confidence scores of posebox')
        
        args = parser.parse_args()
        assert args.orig_data and args.pose_data and args.csv_list and args.caffemodel
        print args.orig_data
        print args.pose_data
        print args.csv_list
        print args.caffemodel

	a = ReIDDataLayer(args.orig_data,
	 		  args.pose_data,
	 		  args.csv_list,
	 		  'train')
	counter = 0
	print(len(a.train_data_list))
	print(len(a.test_data_list))


	##################Load network
	caffe.set_mode_gpu()
	counter = 0

	net = caffe.Classifier('./res50_tripleLoss_deploy.prototxt',
			       args.caffemodel, caffe.TEST)######

	blob = caffe.proto.caffe_pb2.BlobProto()
	mean_data = open( '../DataMaker/ResNet_mean.binaryproto' , 'rb' ).read()
	blob.ParseFromString(mean_data)
	arr = np.array( caffe.io.blobproto_to_array(blob) )[0]

	pose_data_transformer = caffe.io.Transformer({'pose_data': net.blobs['orig_data'].data.shape})
	pose_data_transformer.set_transpose('pose_data', (2,0,1))
	pose_data_transformer.set_mean('pose_data', arr.mean(1).mean(1)) # mean pixel
	pose_data_transformer.set_raw_scale('pose_data', 255) # the reference model operates on images in [0,255] range instead of [0,1]
	pose_data_transformer.set_channel_swap('pose_data', (2,1,0)) # the reference model has channels in BGR order instead of RGB

        os.mkdir('./features')
        os.mkdir('./features/poseBox_fc751')
        os.mkdir('./features/origImg_fc751')
        os.mkdir('./features/overall_fc751')
        os.mkdir('./features/concat')

	for k in a.train_data_list:
		pose = pose_data_transformer.preprocess('pose_data', caffe.io.load_image(k[0]))
		orig = pose_data_transformer.preprocess('pose_data', caffe.io.load_image(k[1]))

		conf = k[2]
		label = k[3]
		name = k[4]
		# print(label.shape)
		origImg_fc751, poseBox_fc751, overall_fc751, concat = get_feature(orig, pose, conf)
		output_name = name[0:-4]
		
		f = open('./features/poseBox_fc751/' + output_name ,'wb')#######
		f.write(poseBox_fc751)
		f.close()

		f = open('./features/origImg_fc751/' + output_name ,'wb')#######
		f.write(origImg_fc751)
		f.close()

		f = open('./features/overall_fc751/' + output_name ,'wb')#######
		f.write(overall_fc751)
		f.close()
		
		f = open('./features/concat/' + output_name ,'wb')#######
		f.write(concat)
		f.close()

		counter = counter + 1	
		print('*****	'+ str(counter) + '  ******')

	print counter
	print len(a.train_data_list)
