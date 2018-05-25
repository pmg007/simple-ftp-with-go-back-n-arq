# Authors: Tushar Pahuja, Pragam Manoj Gandhi


# importing all the dependencies

import socket
import os
import sys
import pickle
import random

############################################################

# Constants needed for the code are declared
# command line values
#port number
S_PORT_NUMBER = int (sys.argv[1])
# file name
F_NAME = sys.argv[2]
# probability for packet loss
PKT_LOSS_PROB = float(sys.argv[3])
# acknowledgement
TYPE_ACK = "1010101010101010"
# padding or data
DATA_PADDING = "0000000000000000"
# end of file indication
TYPE_EOF = "1111111111111111"
#data
TYPE_DATA = "0101010101010101"

################################################################

ACK_PORT = 65000

s_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ACK_HOST_NAME = ''

HOST_NAME = '0.0.0.0'

s_sock.bind((HOST_NAME, S_PORT_NUMBER))

last_recv_pkt=-1

# Removing file if already present

if os.path.isfile(F_NAME):
	os.remove(F_NAME)

####################################################################
# writing data to file

def writing_File(pkt_data):
	with open(F_NAME, 'ab') as x:
		x.write(pkt_data)

#########################################################################
# sending acknowledgement
def ack_send(ack_num):
	
	ack_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
	ack_pkt = pickle.dumps([ack_num, DATA_PADDING, TYPE_ACK])
	
	ack_sock.sendto(ack_pkt,(ACK_HOST_NAME, ACK_PORT))
	
	ack_sock.close()
#####################################################################
def randNum():
	return random.random()

#####################################################################
def carry_add(a, b): 
	c = a+b
	return (c & 0xFFFF) + (c >> 16)

#########################################################################
# checking if the packet needs to be dropped according to the probability

def pkt_drop_chk(PKT_LOSS_PROB,pkt_seq_num):
	
	if random.random() > PKT_LOSS_PROB:
		return False

	return True
##########################################################################

def chksum(data):
	if (len(data)%2) != 0:
		data+="0"
	s=0
	for i in range(0,len(data),2):
		w = ord(data[i])+(ord(data[i+1]) << 8)
		s = carry_add(s, w)
	return ~s & 0xFFFF


##########################################################################
# validating checksum
def validate_chksum(blob,chksum):
	
	if chksum_compute(blob,chksum) == 0:
		return True

	return False

###########################################################################

# Method for checksum computation
def chksum_compute(blob,chksum):
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

##############################################################################
# main function
def main():
	
	global last_recv_pkt, ACK_HOST_NAME
	
	complete_flag=True
	
	while complete_flag:
		recv_data_temp, addr = s_sock.recvfrom(65535)
		
		ACK_HOST_NAME = addr[0]
		
		recv_data = pickle.loads(recv_data_temp)
		
		pkt_seq_num, pkt_chksum, pkt_type, pkt_data = recv_data[0], recv_data[1], recv_data[2], recv_data[3]
		
		if pkt_type == TYPE_EOF:
			complete_flag=False
			s_sock.close()
		elif pkt_type == TYPE_DATA:
			
			drop_pkt=pkt_drop_chk(PKT_LOSS_PROB,pkt_seq_num)
			
			if drop_pkt==False:
				
				if validate_chksum(pkt_data,pkt_chksum):
					
					if pkt_seq_num == 1 + last_recv_pkt:
						ack_send(pkt_seq_num+1)
						last_recv_pkt+=1
						writing_File(pkt_data)
					
					else:
						ack_send(1 + last_recv_pkt)
				
				else:
					print "Packet "+str(pkt_seq_num)+" dropped " + " reason " + " wrong checksum "

			
			else:
				print "Packet loss, sequence number = "+ str(pkt_seq_num)
				
				



if __name__ == "__main__":
    main()