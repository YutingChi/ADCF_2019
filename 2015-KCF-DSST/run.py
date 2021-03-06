# test version: 8.31
import cv2
import numpy as np
from scipy import io
from tracker import KCFTracker # use hog or gray


env = 'MAC' #'WIN'
test = 'BenchMark' # 'Cam'


if env == 'MAC':
	path_seq = '/Users/apple/Downloads/cnnKCF_proj_code/KCF_8.12/Sequence/'
	path_save = '/Users/apple/Downloads/cnnKCF_proj_code/tracker_benchmark_v1.0/results/results_py/'
elif env == 'WIN':
	path_seq = 'Sequence\\'
	path_save = 'E:\\cnnKCF_proj_code\\tracker_benchmark_v1.0\\results\\results_py\\'


# load seq_txt generated by xx_CSK.mat to get test_seq
def load_seq_txt_to_test(path_save, seqs):
	seq_txt = []
	for s in seqs:
		if env == 'MAC':
			seq_txt.append(s+'/'+s+'.txt')
		elif env == 'WIN':
			seq_txt.append(s+'\\'+s+'.txt')
	seq_test = []
	for txt in seq_txt:
		file = open(path_save + txt, 'r')
		print('load file:',txt)
		# read lines and save as list(dict)
		list_read = file.readlines()
		seq_list = []
		for l in list_read:
			d = eval(l)
			seq_list.append(d)
		seq_test.append(seq_list)
	return seq_test

# get IoU of track_bbox and truth_bbox
def IoU(box1, box2): # 2D bounding box [top, left, bottom, right]
	t1,l1,b1,r1 = box1[0],box1[1],box1[2],box1[3]
	t2,l2,b2,r2 = box2[0],box2[1],box2[2],box2[3]
	if ((t1<=b2 and l1<r2) and (t2<=b1 and l2<=r1)) or ((t1>=b2 and l1>=r2) and (t2>=b1 and l2>=r1)):
		in_h = min(box1[2], box2[2]) - max(box1[0], box2[0])
		in_w = min(box1[3], box2[3]) - max(box1[1], box2[1])
		inter = 0 if in_h<0 or in_w<0 else in_h*in_w
		union = (box1[2] - box1[0]) * (box1[3] - box1[1]) + (box2[2] - box2[0]) * (box2[3] - box2[1])
		union -= inter
		iou = inter / union
		return iou
	else:
		return 0.

# read groundtruth_rect.txt from seq_file to get bbox
def read_groundtruth(seq_path):
	truth_bbox = []
	print('load groundthuth',seq_path+'groundtruth_rect.txt')
	with open(seq_path+'groundtruth_rect.txt', 'r') as file_to_read:
		while True:
			lines = file_to_read.readline() # 整行读取数据
			if not lines:
				break
			p_tmp = [int(i) for i in lines.split(',')]
			p_tmp = tuple(p_tmp)
			truth_bbox.append(p_tmp)
	return truth_bbox


def run_tracker(frame, truth_bbox, path_img, hog=False, _IoU=0.5,seq_val=True, startframe=1, length=100):
	# KCF tracker use (hog, fixed_Window, multi_scale)
	tracker = KCFTracker(hog, True, False)
	
	count = startframe
	fps_mean = 0.
	res = []
	if seq_val == False:
		cam = cv2.VideoCapture(0)
		tracker.init(truth_bbox, frame)
	elif seq_val == True:
		# start from startframe
		tracker.init(truth_bbox[startframe-1], frame)
		res.append(np.array(truth_bbox[startframe-1])) # get init_bbox
		# test seq length
		frame_num = startframe + length - 1
		print('##################################################################')
		print('start running with startframe:',startframe,'length:',length)
	#tracker.init(truth_bbox[0], frame)
	#frame_num = len(truth_bbox)
	
	while True:
		if seq_val == False: # use CAMERA
			ok, frame = cam.read()
			if ok == False: break
		elif seq_val == True: # BenchMark
			count += 1
			if count > frame_num: break
			# read img from seq_file
			if count < 10:
				img_path = path_img + '000'+str(count)+'.jpg'
			elif count < 100:
				img_path = path_img + '00' +str(count)+'.jpg'
			elif count < 1000:
				img_path = path_img + '0'  +str(count)+'.jpg'
			else:
				img_path = path_img + str(count) + '.jpg'
			#print('\nuse name:', init_f)
			print('read frame num',count)
			frame = cv2.imread(img_path)

		timer = cv2.getTickCount()
		bbox = tracker.update(frame)
		res.append(bbox) # save res_bbox

		bbox = list(map(int, bbox))
		fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer)
		fps_mean += fps # get mean fps for test KCF

		# Tracking success
		p1 = (int(bbox[0]), int(bbox[1])) # top,left
		p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])) # top+x,left+y = bottom,right
		# draw tracking result
		cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
		if seq_val == True:
			# get truth_bbox
			t1 = (int(truth_bbox[count-1][0]), int(truth_bbox[count-1][1]))
			t2 = (int(truth_bbox[count-1][0] + truth_bbox[count-1][2]), int(truth_bbox[count-1][1] + truth_bbox[count-1][3]))
			# draw ground_truth bbox
			cv2.rectangle(frame, t1, t2, (0, 255, 0), 2, 1)
			
			# using re_init when tracking failed, IoU<=0.5
			box1,box2 = [p1[0],p1[1],p2[0],p2[1]], [t1[0],t1[1],t2[0],t2[1]]
			#print('IoU:',IoU(box1,box2))
			if IoU(box1,box2) <= _IoU: #0.75:
				tracker.init(truth_bbox[count-1], frame)
				print('#############\nTrack Fail in frame',count,'\nRe_init KCF\n#############!')
		
		# Put FPS
		cv2.putText(frame, "FPS : " + str(int(fps)), (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 170, 50), 2)
		cv2.imshow("Tracking", frame)
		
		# Exit if ESC pressed
		k = cv2.waitKey(1) & 0xff
		if k == 27: break

	if seq_val == False:
		cam.release()
	else:
		fps_mean = fps_mean / length
	cv2.destroyAllWindows()
	print('finished run, res:', len(res))

	return res,fps_mean


Seqs = ['ironman'] # ['matrix', 'deer', 'basketball', 'soccer', 'liquor', 'boy']# ['motorRolling','singer2']


def run_test(hog=True, _IoU=0.5, test='BenchMark'):
	if test == 'CAM': # use camera to show
		video = cv2.VideoCapture(0)
		ok, frame = video.read()
		print(ok, frame.shape)
		# cv2.selectROI to get init bbox on frame(0)
		bbox,_ = cv2.selectROI('Select ROI', frame, False)
		if min(bbox) == 0: exit(0)
		# run with CAM
		res = run_tracker(frame, bbox, False, test_cnn)
	elif test == 'BenchMark': # test tracker with Seqs
		# current test tracker
		if hog:
			tracker_name = 'KCF' # hog
			print('test original KCF')
		else:
			tracker_name = 'Gray' # raw gray
			print('test raw gray KCF')
			
		
		# load test seqs{}
		seq_test = load_seq_txt_to_test(path_save,Seqs)
		seq_num = 0
		# run each seq_test with init_frame, run len(seq_test) times
		for test in seq_test:
			seq = Seqs[seq_num]
			print('\ncurrent test seq:',seq)
			seq_num += 1
			# get groundtruth_file and img
			if env == 'MAC':
				path_cur = path_seq + seq + '/'
				path_img = path_cur + 'img/'
				truth_bbox = read_groundtruth(path_cur)
			elif env == 'WIN':
				path_cur = path_seq + seq + '\\'
				path_img = path_cur + 'img\\'
				truth_bbox = read_groundtruth(path_cur)

			i = 0
			res_dic = {}
			fps_dic = []
			for dic in test: # run 20 times
				stratframe,length = dic['startFrame'],dic['len']
				if stratframe < 10:
					init_f = '000'+str(stratframe)+'.jpg'
				elif stratframe < 100:
					init_f = '00'+str(stratframe)+'.jpg'
				elif stratframe < 1000:
					init_f = '0'+str(stratframe)+'.jpg'
				elif stratframe >= 1000:
					init_f = str(stratframe) + '.jpg'
				frame = cv2.imread(path_img + init_f) # load init_frame to KCF
				print('use init frame:',path_img + init_f)
				print('frame:',frame.shape)

				# run KCF to get res_bbox
				res,fps = run_tracker(frame, truth_bbox, path_img, hog, _IoU,True, stratframe, length)
				print('\n#######################################')
				print('KCF res:',i,len(res),res[0].shape,'fps:',fps)
				print('#######################################\n')
				res_dic.update({str(i+1):np.array(res)}) # save as dict in .mat
				fps_dic.append(fps)
				i += 1
				#break

			res_dic.update({'fps':np.array(fps_dic)}) # save fps as res['fps']
			new_res = seq+'/'+seq+'_'+ tracker_name  +'.mat'
			io.savemat(path_save+new_res, res_dic) # save to result_py as seq_tracker.mat
			print('save results test:', new_res)



if __name__ == '__main__':
	hog = True # use hog
	run_test(hog, 0.1)
	print('\n\n\n\nfinish KCF with Hog Features\n\n\n')
