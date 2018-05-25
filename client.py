# Authors: Tushar Pahuja, Pragam Manoj Gandhi

# importing all the dependencies

from multiprocessing import Lock
from collections import namedtuple
import sys
import collections
import pickle
import signal
import time
import socket
import threading

########################################################
# Retransmit timeout
RTT = 0.1 

# acknowledgement
TYPE_ACK = "1010101010101010"
# end of file indication
TYPE_EOF = "1111111111111111"
# data
TYPE_DATA = "0101010101010101"

########################################################
ACK_PORT = 65000 

ACK_HOST = '0.0.0.0'

#print ACK_HOST


sliding_wnd = set()
c_buff = collections.OrderedDict()

data_pkt = namedtuple('data_pkt', 'sequence_no checksum type data')
ack_pkt = namedtuple('ack_pkt', 'sequence_no padding type')

last_ack_pkt = -1 
max_seq_num=0 
last_send_pkt = -1



thrd_lock = Lock()

c_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# flag to find if sending is finished
send_Finish=False

t_start=0
t_end=0
###################################################################

# Constants needed for the code are declared
# command line values
#host address
SEND_HOST = sys.argv[1]
#port number
SEND_PORT = int(sys.argv[2])
# file name
F_NAME = sys.argv[3]
#N_VALUE
N = int(sys.argv[4])
# MSS VALUE
MSS = int(sys.argv[5])

####################################################################

# function to send packet
def send_pkt(pkt, host, port, socket, sequence_no):
	c_sock.sendto(pkt,(SEND_HOST,SEND_PORT))

####################################################################

def carry_add(a, b): 
	c = a+b
	return (c & 0xFFFF) + (c >> 16)

####################################################################

# rdt_send method
def rdt_send(file_content, c_sock, host, port):
	global last_send_pkt,last_ack_pkt,sliding_wnd,c_buff,t_start
	t_start=time.time()
	while len(sliding_wnd)<min(len(c_buff),N):
		if last_ack_pkt==-1:
			send_pkt(c_buff[1+last_send_pkt], host, port, c_sock, 1+last_send_pkt)
			signal.alarm(0)
 			signal.setitimer(signal.ITIMER_REAL, RTT)
 			last_send_pkt += 1
			sliding_wnd.add(last_send_pkt)
			y=0
			while y<100000:
				y=y+1

###########################################################################

# method for checksum computation
def chksum_compute(blob):
	chksum=0
	blob = str(blob)
	b_length=len(blob)
	byte=0
	while byte<b_length:
		# Converting into unicode representation
		byte1=ord(blob[byte])
		
		byte1_shift=byte1<<8
		
		if 1+byte != b_length:
			byte2=ord(blob[byte+1])

		else:
			byte2=0xffff
			
		bytes_merged=byte1_shift+byte2
		chksum_add=chksum+bytes_merged
		main_part=chksum_add&0xffff
		cry=chksum_add>>16
		chksum=cry + main_part 
		byte+=2
	
	# returning 1's complement
	return chksum^0xffff

###############################################################################


def chksum(data):
	if (len(data)%2) != 0:
		data+="0"
	s=0
	for i in range(0,len(data),2):
		w = ord(data[i])+(ord(data[i+1]) << 8)
		s = carry_add(s, w)
	return ~s & 0xFFFF



###############################################################################

#will monitor the incoming ack's and sent the remaining pkts

def ack_process():
	global last_ack_pkt,last_send_pkt,c_buff,sliding_wnd,c_sock,SEND_PORT,SEND_HOST,send_Finish,t_end,t_start,t_total
	
	ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ack_sock.bind((ACK_HOST, ACK_PORT))

	while True:
		
		reply = pickle.loads(ack_sock.recv(65535))
		
		if reply[2] == TYPE_ACK:
			
			curr_ack_seq_num=reply[0]-1
			if last_ack_pkt + 1 >= 0 :
				

				thrd_lock.acquire()
				
			if  max_seq_num == curr_ack_seq_num:
				eof_pkt = pickle.dumps(["0", "0", TYPE_EOF, "0"])
				


				c_sock.sendto(eof_pkt, (SEND_HOST, SEND_PORT))
				
				thrd_lock.release()

				send_Finish=True
				
				t_end=time.time()
				
				t_total=t_end-t_start
				
				break

			elif curr_ack_seq_num>last_ack_pkt:
				
				while curr_ack_seq_num>last_ack_pkt:
    				
	    				signal.alarm(0)
	    				
	    				signal.setitimer(signal.ITIMER_REAL, RTT)
	    				
	    				last_ack_pkt += 1
	    				
	    				sliding_wnd.remove(last_ack_pkt)
	    				c_buff.pop(last_ack_pkt)
	    				
	    				while min(len(c_buff),N)>len(sliding_wnd):
	        				
	        				if max_seq_num>last_send_pkt:
	        					send_pkt(c_buff[1+last_send_pkt],SEND_HOST,SEND_PORT,c_sock,1+last_send_pkt)
	        					sliding_wnd.add(1+last_send_pkt)
	        					last_send_pkt+=1
	        		

        		thrd_lock.release()
    		else:
    			
    				thrd_lock.release()

#########################################################################
# method for timeout of thread, locking and unlocking threads
def timeout_thread(timeout_th, frame):

 	global last_ack_pkt   		
 	if last_send_pkt == last_ack_pkt + len(sliding_wnd):
 		print "Timeout, sequence num = "+str(last_ack_pkt+1)
 		

 		thrd_lock.acquire()

 		for i in range(1+last_ack_pkt,1+last_ack_pkt+len(sliding_wnd),1):
 			signal.alarm(0)
 		
 			signal.setitimer(signal.ITIMER_REAL, RTT)
			send_pkt(c_buff[i], SEND_HOST, SEND_PORT, c_sock, i)
	

		thrd_lock.release()


#########################################################################
# main function
def main():
	
	global c_buff ,max_seq_num,c_sock,N,SEND_PORT,SEND_HOST,MSS

	#################################
	N = int(N)
	mss = int(MSS)
	#################################
	port = SEND_PORT
	host = SEND_HOST
	#################################
	seq_num = 0
	# start timer
	################# new addition
	# start_time = time.time()
	# try-except block
	try:
		with open(F_NAME, 'rb') as x:
			while True:
				blob = x.read(int(mss))  
				if blob:
					max_seq_num=seq_num
					blob_chksum=chksum_compute(blob)
					c_buff[seq_num] = pickle.dumps([seq_num,blob_chksum,TYPE_DATA,blob])
					seq_num+=1
				else:
					break
	except:
		sys.exit("Could not open the file " + sys.argv[3])

	signal.signal(signal.SIGALRM, timeout_thread)
	# creating thread
	ack_thrd = threading.Thread(target=ack_process)
	
	ack_thrd.start() 	
	
	rdt_send(c_buff, c_sock, host, port)
	
	while True:
		if send_Finish:
			break
	
	ack_thrd.join()
	# # stop timer
	# stop_time = time.time()
	# print stop_time-start_time
	# closing the client socket
	c_sock.close()

if __name__ == "__main__":
    main()