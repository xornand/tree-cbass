'''

This program interfaces with the dynamic execution trace(generated from platform-dependent instrumentation or emulation environment) and 
provide concrete values of memory and registers for concrte/symbolic execution. 
Inputs:
    -- Dynamic Trace File with fine-grained instruction level state information
 Output:
   -- Instruction address and relevant program state 
   
 * @author Nathan Li
 * 
 */

'''
import os
import struct
import logging

log = logging.getLogger('CIDATA')
from ctypes import *
from ctypes.util import *
import ctypes

from x86Decoder import x86Decoder, instDecode, IMMEDIATE, REGISTER,MEMORY, WINDOWS, LINUX
from x86Thread import X86Thread

Invalid, LoadImage,UnloadImage,Input,ReadMemory,WriteMemory,Execution, Snapshot, eXception = range(9)

class InstructionEncoding(object):
    def __init__(self):
        self.address = None
        self.size = None
        self.encoding = None
        self.menica = None
        
class TraceRecord(object):
    def __init__(self):
        self.recordType= Invalid
        
    def getRecordType(self):
        return self.recordType
    
class InstructionTraceRecord(TraceRecord):
    def __init__(self):
        self.recordType = Execution
        self.currentLine = None
        self.currentInstruction = None
        self.currentInstSize = None
        self.sEncoding = None
        self.currentThreadId = None
        self.currentInstSeq = 0
        self.currentReadAddr = None
        self.currentReadSize = None
        self.currentReadValue = None
        self.currentWriteAddr = None
        self.currentWriteSize = None
        self.currentWriteValue = None
        self.reg_value={}

class ExceptionTraceRecord(TraceRecord):    
    def __init__(self):
        self.recordType =  eXception
        self.currentExceptionCode = None
        self.currentExceptionAddress = None

class InputTraceRecord(TraceRecord):    
    def __init__(self):
        self.recordType = Input
        self.currentInputAddr = None
        self.currentInputSize = None
        self.inputBytes = None
        self.inputFunction = None
        self.functionCaller = None
        self.callingThread = None
        self.sequence = None
        self.inputHandle = None

class LoadImageTraceRecord(TraceRecord):    
    def __init__(self):
        self.recordType = LoadImage
        self.ImageName = None
        self.ImageSize = None
        self.LoadAddress = None
        
        
class TraceReader(object):
    def __init__(self, trace_file):
        self.exe_trace = trace_file
        self.x86_thread = X86Thread()
            
    def loadImage(self, imageName, loadOffset, lowAddress, highAddress):
#        self.images[imageName] = BinImage(loadOffset, lowAddress,highAddress)
        self.currentImage = imageName

    def getCurrentImage(self):
        return self.currentImage
              
    def unloadImage(self, mod_id, mod_path):
        pass
 
    def getNext(self):
        pass
    
    def parseInput(self, line):
        pass

    def parseInstruction(self, line):
        pass
 
    def parseImageLine(self, line):
        pass
   
    def parseException(self,line):
        pass
        
        
class IDATextTraceReader(TraceReader):

    def __init__(self, trace_file):
        super(IDATextTraceReader,self).__init__(trace_file)
        self.trace_fd = open(self.exe_trace, 'r') 
        
    def getNext(self):
        if(self.trace_fd is None):
            print("Invalid trace file\n")
            return None
        
        line = self.trace_fd.readline()        
        sDbg = "TextTraceReader: %sline:%s" %("\n\n",line)
        log.debug(sDbg)
        
        if line==None:
            print ("No more line. Quit!\n")
            return None

        line = line.strip()
        split = line.split(" ")
        skip = 0

        while line is not None:
            log.debug(line)
            tRecord = None
            if split[0] == "L":
                tRecord = self.parseImageLine(line)
                skip = 0				
                return tRecord
            elif split[0] == "I":
                tRecord = self.parseInputLine(line)
                skip = 0				
                sDbg = "TextTraceReader: After input %s, return tRecord" %(line)
                log.debug(sDbg)
                return tRecord
            elif split[0] == "E":
                sDbg = "TextTraceReader: ELine %s, return tRecord" %(line)
                log.debug(sDbg)
                tRecord = self.parseInstructionLine(line) 
                skip = 0
                return tRecord
            elif split[0] == "X":
                tRecord = self.parseExceptionLine(line)
                skip = 0
                return tRecord       
            elif split[0] == "T":
                tRecord = self.parseExceptionLine(line)
                skip = 0
                return tRecord       
            else:
                if( line=="EOF"):
                    sDbg= "EOF reached %s" %line
                    log.debug(sDbg)
                    break;
                elif skip <5:
                    skip = skip+1
                else:
                    sDbg= "Skip too many lines: STOP! %s" %line
                    log.debug(sDbg)
                    break            
            line = self.trace_fd.readline()
            line = line.strip()
            split = line.split(" ")

    def parseInputLine(self,line):
        split = line.split(" ")
        iRecord = InputTraceRecord()
        
        iRecord.currentInputAddr = int(split[1], 16)
        iRecord.currentInputSize = int(split[2], 10)
        sDbg= "Text Trace Input received at 0x%x for %d bytes" %(iRecord.currentInputAddr,iRecord.currentInputSize)
        #I 103e138 12 414141414141414141414141 0x63c4 0x0 wsock32_recv 0x11d110e 0x78
        # or I 103e138 12 414141414141414141414141 "old format"
        iRecord.inputBytes = split[3]
        if len(split)> 4:
            iRecord.callingThread = int(split[4],16)            
            iRecord.sequence = int(split[5],16)            
            iRecord.inputFunction = split[6]
            iRecord.functionCaller = int(split[7],16)
            iRecord.inputHandle = int(split[8],16)
        else:
            iRecord.callingThread = 0            
            iRecord.sequence = 0
            iRecord.inputFunction = "Unknown"
            iRecord.functionCaller = 0
            iRecord.inputHandle = 0
        log.debug(sDbg)
        
        return iRecord

    def parseImageLine(self, line):
        sDbg= "parsing image line: %s" % (line)
        log.debug(sDbg)

        iRecord = LoadImageTraceRecord()
        
        split = line[2:] #remoe the L identifier, then split with comma
        #csplit = split.split(",") # default is space, which may have problem with Windows Path
        csplit = split.split() # default is space, which may have problem with Windows Path
        # Image load, extrac the name from the fullpath
        if len(csplit)>2:               
            sImageName = csplit[0].rsplit("\\",1)
            if len(sImageName)>1:
                iRecord.ImageName = (csplit[0].rsplit("\\",1))[1]
            else:
                iRecord.ImageName = sImageName
            sDbg= "parsing image: %s" % (iRecord.ImageName)
            log.debug(sDbg)
                    
            iRecord.LoadAddress = int(csplit[1], 16)
            iRecord.ImageSize = int(csplit[2], 16)
       
        return iRecord

    def parseExceptionLine(self,line):
        split = line.split(" ")
        iRecord = ExceptionTraceRecord()

        iRecord.currentExceptionAddress = int(split[1], 16)        
        iRecord.currentExceptionCode = int(split[2], 16)

        sDbg= "Text Tracer: Exception happened at 0x%x with exception code %x" %(iRecord.currentExceptionAddress,iRecord.currentExceptionCode)
        log.debug(sDbg)
        print("%s" %sDbg)
        
        return iRecord
                            
        
    def parseInstructionLine(self,line):
        
        iRecord = InstructionTraceRecord()
        
        line = line.strip()
        split = line.split(" ")
        nParts = len(split)
        if split[0] == "E":
            #"Located Instruction header:"
            iRecord.currentInstruction = int(split[1],16)
            iRecord.currentInstSize = int(split[2],16)
            iRecord.sEncoding = split[3]
            iRecord.currentThreadId = int(split[4],16)
            iRecord.currentInstSeq = int(split[5],16)
            sDbg= "Addr=0x%x, Thread=%x, Seq=%d" %(iRecord.currentInstruction,iRecord.currentThreadId,iRecord.currentInstSeq)
            log.debug(sDbg)
            #print("%s" %sDbg)
            
            if(nParts<=6):
                return iRecord
            i=6                       
            if(split[i] == "Reg("):
                #read register name and value pair
                i=i+1
                while (split[i] != ")"):
                    #read concrete values from trace
                    reg_value_pair=(split[i]).split("=")
                    regname = reg_value_pair[0].lower()
                    regvalue = int(reg_value_pair[1],16)
                    iRecord.reg_value[regname] = regvalue
                    sDbg = "regname=%s, regvalue=0x%x" %(regname,iRecord.reg_value[regname])
                    log.debug(sDbg)
                    i= i+1
                i=i+1
            if(nParts-i>=3):
                #print("R: nParts=%d, i=%d split[i+1]=%s " %(nParts, i, split[i+1]))
                if(split[i] == "R"):
                    sSize = split[i+1].lstrip()
                    iRecord.currentReadSize = int(sSize.lstrip(), 10) # in byte                
                    iRecord.currentReadAddr = int(split[i+2], 16)

                    memBytes = (split[i+3]).split("_")
                    sDbg= "Read %d bytes at 0x%x: " %(iRecord.currentReadSize,iRecord.currentReadAddr)
                    log.debug(sDbg)
                    
                    if(memBytes[0]!='X'):
                        j =0;
                        iRecord.currentReadValue = c_byte*iRecord.currentReadSize
                        readBytes = iRecord.currentReadValue()
                        while j<iRecord.currentReadSize:
                            readBytes[j] = int(memBytes[j],16)
                            sDbg= "Offset:%d,Value=0x%x" %(j,readBytes[j])
                            log.debug(sDbg)
                        #TODO: validate if this matches exec simulation
                            j=j+1               
                        i=i+3
                    else:
                        i = i+2
                    
            if(nParts-i>=3):                    
                head = split[i+1].lstrip()
                if(head== "W"):
                    sSize = split[i+2].lstrip()    
                    iRecord.currentWriteSize = int(sSize, 10) # in byte                
                    iRecord.currentWriteAddr = int(split[i+3], 16)
                    sDbg = "Write %d bytes at 0x%x: " %(iRecord.currentWriteSize,iRecord.currentWriteAddr)
                    log.debug(sDbg)
                    #print("%s" %sDbg)

        return iRecord

class PinTraceReader(TraceReader):
    def __init__(self, trace_file):
        super(PinTraceReader,self).__init__(trace_file)        
        self.trace_fd = open(self.exe_trace, 'rb')
        self.xDecoder32 = x86Decoder(32,32, WINDOWS)

    def getNext(self):

        if(self.trace_fd is None):
            print("Invalid trace file\n")
            return None

        try: 
            tag = self.trace_fd.read(1) 
            sDbg= "First tag=%s" % (tag)
            log.debug(sDbg)
#            print ("%s" %sDbg)
                    
            while tag:
                tRecord = None
                sDbg= "tag=%s" % (tag)
                log.debug(sDbg)
#                print ("%s" %sDbg)
                
                if tag == 'L': #load image
                    tRecord = self.parseImageLine(self.trace_fd.readline()) 
                    return tRecord
                elif tag == 'I': #input
                    tRecord = self.parseInputLine()
                    return tRecord
                elif tag =='E':
                    tRecord = self.parseInstructionLine() 
                    return tRecord
                elif tag == 'X':
                    tRecord = self.parseExceptionLine(self.trace_fd.readline())      
                    return tRecord
                else:
                    sDbg= "Unknown tag"
                    log.debug(sDbg)
                    
                tag = self.trace_fd.read(1)     
        finally:
            pass
			
    def parseInputLine(self):
        line = self.trace_fd.readline()
        split = line.split(" ")
        iRecord = InputTraceRecord()
        
        iRecord.currentInputAddr = int(split[1], 16)
        iRecord.currentInputSize = int(split[2], 16)
        iRecord.inputBytes = split[3]
        sDbg= "Input received at 0x%x for %d bytes:" %(iRecord.currentInputAddr,iRecord.currentInputSize)
        log.debug(sDbg)
        print("%s" %(sDbg))
        
        #TODO: Enhance PIN Tracer to provide following information
        iRecord.callingThread = 0            
        iRecord.sequence = 0            
        iRecord.inputFunction = "ReadFile"
        iRecord.functionCaller = 0xffff
        iRecord.inputHandle = 0

        return iRecord

    def parseImageLine(self, line):
        sDbg= "parsing image line: %s" % (line)
        print("%s" %(sDbg))
        log.debug(sDbg)

        iRecord = LoadImageTraceRecord()
        
        split = line #remoe the L identifier, then split with comma
        csplit = split.split(",")
        # Image load, extrac the name from the fullpath               
        iRecord.ImageName = (csplit[0].rsplit("\\",1))[1]
        sDbg= "parsing image: %s" % (iRecord.ImageName)
        log.debug(sDbg)
        print("%s" %(sDbg))
        
        iRecord.LoadAddress = int(csplit[1], 16)
        iRecord.ImageSize = int(csplit[3], 16) - int(csplit[2], 16)
       
        return iRecord

    def parseExceptionLine(self,line):
        split = line.split(" ")
        iRecord = ExceptionTraceRecord()
        
        iRecord.currentExceptionAddress = int(split[2], 16)
        iRecord.currentExceptionCode = int(split[1], 16)
        sDbg= "Exception happened at 0x%x with code %x" %(iRecord.currentExceptionAddress,iRecord.currentExceptionCode)
        log.debug(sDbg)
        print("%s" %sDbg)
        
        return iRecord
                            
        
    def parseInstructionLine(self):
        
        iRecord = InstructionTraceRecord()        
        iRecord.currentInstSeq +=1;
        
        iRecord.currentInstruction = struct.unpack("<I", self.trace_fd.read(4))[0]
        print("Instruction address 0x%x\n" %iRecord.currentInstruction)

        iRecord.currentInstSize = struct.unpack("<B", self.trace_fd.read(1))[0]
        print("Instruction currentInstSize 0x%x\n" %iRecord.currentInstSize)

        iRecord.sEncoding = bytearray(self.trace_fd.read(iRecord.currentInstSize))
#        print("Instruction encoding %s\n" %(str(iRecord.sEncoding)))
        '''
        instcode = c_byte*iRecord.currentInstSize
        instBytes = instcode()
        
        i=0
        for byte in iRecord.sEncoding:
            instBytes[i]= byte
            i=i+1
        
        instInfo = instDecode()            
        if iRecord.currentInstSize > 0:
            self.xDecoder32.decode_inst(iRecord.currentInstSize, pointer(instBytes),ctypes.byref((instInfo)))
            print("In Parser")
            instInfo.printInfo()
            print("End Parser")
        '''
        iRecord.currentThreadId = struct.unpack("<B", self.trace_fd.read(1))[0]

        sDbg = "PinTraceReader: parse binary instruction block: addr = 0x%x,threadID=%d, size=%s" %(iRecord.currentInstruction,iRecord.currentThreadId,iRecord.currentInstSize)
        log.debug(sDbg)
        print ("%s" %sDbg)
        reg_mem_count = struct.unpack("<B", self.trace_fd.read(1))[0]
        regCount = reg_mem_count & 0xf
        memRead = (reg_mem_count & 0xc0) >>6
        memWrite = (reg_mem_count & 0x30) >> 4
        sDbg = "BinTraceReader: regcount = %d,memRead=%d, memWrite=%d" %(regCount,memRead,memWrite)
        log.debug(sDbg)
        print("%s" %sDbg)
        
        i=0
        while i<regCount:
            regId = struct.unpack("<B", self.trace_fd.read(1))[0]
            regValue = struct.unpack("<I", self.trace_fd.read(4))[0]
            regName = self.x86_thread.get_reg_name(regId)
            iRecord.reg_value[regName] = regValue
            i=i+1
            sDbg = "BinTraceReader: regID=%d, regName = %s,regValue = 0x%x" %(regId, regName,regValue)
            log.debug(sDbg)
            print("%s" %sDbg)

        i=0
        while i<memRead:                    
            iRecord.currentReadSize = struct.unpack("<B", self.trace_fd.read(1))[0]
            iRecord.currentReadAddr = struct.unpack("<I", self.trace_fd.read(4))[0]            
            i=i+1

            j=0
            while j<iRecord.currentReadSize:
                iRecord.currentReadValue = struct.unpack("<B",self.trace_fd.read(1))[0]
                sDbg = "readValue = %x" %(iRecord.currentReadValue)
                log.debug(sDbg)            
                print("%s" %sDbg)
                j=j+1                
        i=0
        while i<memWrite:
            iRecord.currentWriteSize = struct.unpack("<B", self.trace_fd.read(1))[0]            
            iRecord.currentWriteAddr = struct.unpack("<I", self.trace_fd.read(4))[0]            
            i=i+1
            j=0
            while j<iRecord.currentWriteSize:
                iRecord.currentWriteValue = struct.unpack("<B", self.trace_fd.read(1))[0]
                j=j+1
                sDbg = "writeValue = %x at 0x%x" %(iRecord.currentWriteValue,iRecord.currentWriteAddr+j)
                log.debug(sDbg)
                
        return iRecord
                            
        