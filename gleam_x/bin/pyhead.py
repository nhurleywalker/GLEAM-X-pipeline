#!/usr/bin/env python
""" use python/fits to add/print/update/delete header keywords"""
from __future__ import print_function

import copy, os, shutil, glob, sys, string, re, types
import math
from astropy.io import fits

yes=0
no=1

######################################################################
def pyhead(file, extn, cmdlist, arglist, verbose=1, printfile=1, printextn=1, update=0, doparse=1):        
    """ use python/fits to add/print/update/delete header keywords"""

    try:
        if (update):
            inf=fits.open(file,'update')
        else:
            inf=fits.open(file)
    except:
        print("Could not open file {0}\n".format(file))
        return 0

    hdr=inf[extn].header
    for i in range(0,len(cmdlist)):
        cmd=cmdlist[i]
        arg=arglist[i]
        if (cmd.lower() == "u"):
            stuff=arg.split()
            key=stuff[0]
            val=" ".join(stuff[1:len(stuff)])
            if (val.count("$") > 0 and doparse):
                # need to parse the argument
                val2=evalhdr(hdr,val)
            else:
                try:
                    val2=float(val)
                    if (val2 == int(val2)):
                        val2=int(val2)
                except:
                    # it's a string
                    try:
                        val2=eval(val)
                    except:
                        val2=val
            try:                
                hdr[key]=val2
                if verbose:
                    s=""
                    if (printfile):
                        s+="%s" % file
                    if (printextn):
                        s+="[%s]" % extn
                        
                    print("{0}[{1}] = {2} updated".format(s,key,val2))               
            except Exception as e:
                print(e)
                print("Could not update keyword {0}\n".format(key))
        elif (cmd.lower() == "h"):
            val=arg
            if (val.count("$") > 0 and doparse):
                # need to parse the argument
                val2=evalhdr(hdr,val)
            else:
                try:
                    val2=float(val)
                    if (val2 == int(val2)):
                        val2=int(val2)
                except:
                    # it's a string
                    try:
                        val2=eval(val)
                    except:
                        val2=val
            try:                
                hdr.add_history(val2)
                if (verbose):
                    s=""
                    if (printfile):
                        s+="%s" % file
                    if (printextn):
                        s+="[%s]" % extn
                        
                    print("{0}[HISTORY] = {1} updated".format(s,val2))                
            except:
                print("Could not update HISTORY\n")

        elif (cmd.lower() == "d"):
            try:
                del hdr[arg]
                if (verbose):
                    s=""
                    if (printfile):
                        s+="%s" % file
                    if (printextn):
                        s+="[%s]" % extn
                    print("{0}[{1}] deleted".format(s,arg))
            except:
                print("Could not delete keyword {0}\n".format(arg))
        elif (cmd.lower() == "p"):
            if (arg.count("$") == 0 and (arg.count("*") > 0 or arg.count("?") > 0)):
                cards=getcardmatches(hdr,arg)
                if (len(cards)>0):
                    for card in cards:
                        ret=hdr.get(card)
                        s=""
                        if (printfile):
                            s+="%s" % file
                        if (printextn):
                            s+="[%s]" % extn
                        print("{0}[{1}] = {2}".format(s,card,ret))
                else:
                    print("Could not find keyword matching {0}\n".format(arg))

            else:
                if (arg.count("$") > 0):
                    # need to parse the argument
                    ret=evalhdr(hdr,arg)
                else:
                    try:
                        ret=hdr.get(arg)
                    except:
                        print("Could not find keyword {0}\n".format(arg))
                s=""
                if (printfile):
                    s+="%s" % file
                if (printextn):
                    s+="[%s]" % extn
                print("{0}[{1}] = {2}".format(s,arg,ret))
        else:
            print("Unknown command {0}".format(arg))

    if (update):
        inf.verify('fix')
        inf.flush()
    inf.close()
######################################################################
def evalhdr(hdr,arg):
    """evaluates expressions involving header keywords
    """
    
    arg2=arg
    r=re.compile("[^A-Za-z0-9-_]")
    while (arg2.count("$") > 0):
        # replace variables by values
        i1=arg2.find("$")        
        m=r.search(arg2[i1+1:len(arg2)+1])
        if (m):
            i2=m.start()
        else:
            i2=len(arg2)-1
        try:
            y=arg2[i1+1:i1+i2+1]
            card=y            
        except:
            print("Could not find keyword {0}\n".format(arg2[i1+1:i1+i2+1]))
            sys.exit(1)
        x=hdr.get(card)
        if (isinstance(x,bool)):
            if (x == True):
                x=1
            else:
                x=0
        else:
            try:
                x=float(x)
            except:
                x="\"%s\"" % x
        arg2="%s %s %s" % (arg2[0:i1],x,arg2[i1+i2+1:len(arg2)+1])
    try:
        ret=(eval(arg2))
    except:
        print("Could not evaluate expression {0}: {1}".format(arg,arg2))
        sys.exit(1)
    return ret
######################################################################
def getcardmatches(hdr, template):
    """ gets header card matches to wildcard queries
    """
    
    items=hdr.items()
    template2=re.sub("\?",".",template)
    template3=re.sub("\*",".*?",template2)
    template4="^" + template3 + "$"
    matchedcards=[]
    for item in items:
        card=item[0]
        ismatch=re.compile(template4).search(card)
        if (ismatch != None):
            matchedcards.append(card)
    return matchedcards

    
######################################################################
def usage():
    (xdir,xname)=os.path.split(sys.argv[0])

    print("Usage:  {0} [-p keyword/expression] [-d keyword] [-u/-a keyword value/expression]  [-H value/expression] [-f <command_filename>] [-i] <filename(s)>".format(xname))
    print("\t-p will print the value of the keyword")
    print("\t-d will delete the keyword")
    print("\t-u will update the keyword")
    print("\t-a will add a keyword")
    print("\t-H will add to the history")
    print("\t-i will force ignoring of possible variables")
    print("\tcommands can also be included in <command_filename>, without -s")
    print("\tenclose expressions in single quotes")
    print("\tkeywords to print can have wildcards (*,?)")
    print("\tcannot mix expressions and wildcards")
    print("\tfor Booleans, use fits.TRUE or fits.FALSE\n")
    
######################################################################
def main():

    filelist=[]
    cmdlist=[]
    arglist=[]
    argfile=[]

    if (len(sys.argv)==1):
        usage()
        sys.exit(1)
        
    i=1
    update=0
    doparse=1
    while (i<len(sys.argv)):
        arg=sys.argv[i]
        isarg=0
        if (arg.startswith("-h")):
            usage()
            sys.exit(1)
        if (arg.startswith("-f")):
            # file input
            argfile.append(sys.argv[i+1])
            i+=1
            isarg=1
        if (arg.startswith("-p")):
            # print
            cmdlist.append('p')
            arglist.append(sys.argv[i+1])
            i+=1
            isarg=1        
        if (arg.startswith("-d")):
            # delete
            cmdlist.append('d')
            arglist.append(sys.argv[i+1])
            i+=1
            isarg=1
            update+=1
        if (arg.startswith("-i")):
            # ignore parsing
            doparse=0
            isarg=1
        if (arg.startswith("-u") or arg.startswith("-a")):
            # update
            cmdlist.append('u')
            arglist.append("%s %s" % (sys.argv[i+1],sys.argv[i+2]))
            i+=2
            isarg=1    
            update+=1
        if (arg.startswith("-H")):
            # history
            cmdlist.append('H')
            arglist.append(sys.argv[i+1])
            i+=1
            isarg=1
            update+=1
        if (not isarg):
            filelist.append(arg)
        i+=1

    if (len(argfile)>0):
        for file in argfile:
            try:
                fid=open(file)
                lines=fid.readlines()
                fid.close()
                for i in range(0,len(lines)):
                    lines[i]=lines[i].rstrip()
                    if (len(lines[i])>0):
                        lines[i]=lines[i].replace("\'","")
                        x=lines[i].split()
                        if (x[0].find('u')> -1 or x[0].find('a')> -1):
                            cmdlist.append('u')
                            arglist.append("%s %s" % (x[1], ' '.join(x[2:])))
                        if (x[0].find('d')> -1):
                            cmdlist.append('d')
                            arglist.append(x[1])
                            update+=1
                        if (x[0].find('p')> -1):
                            cmdlist.append('p')
                            arglist.append(' '.join(x[1:]))
            except:
                print("Unable to open file {0}".format(file))
                    

    if (len(cmdlist)==0 and len(filelist)>0):
        cmdlist.append('p')
        arglist.append("*")
    
    for file in filelist:
        if (file.find("[") > -1):
            i1=file.find("[")
            i2=file.find("]")
            ext=file[i1+1:i2]
            file=file[0:i1]
        else:
            ext=0
            
        pyhead(file, ext, cmdlist, arglist, 1, len(filelist)>1, ext != 0, update,doparse=doparse)


######################################################################
# Running as executable
if __name__=='__main__':
    main()
