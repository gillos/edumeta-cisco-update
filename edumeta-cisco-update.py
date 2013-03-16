import sys
import getopt
try:
	from requests import *
	from pysnmp.entity.rfc3413.oneliner import cmdgen
	from collections import Counter
	import json
except ImportError:
	print 'this tool requires Python 2.7 and pysnmp and requests'
	print 'sudo pip install requests'
	print 'sudo pip install pysnmp'
	sys.exit()
# sudo pip install requests
# sudo pip install pysnmp	
			
def snmpget(host,oid,cmty='public'):
	errorIndication, errorStatus, errorIndex,varBinds = cmdgen.CommandGenerator().getCmd(cmdgen.CommunityData(host, cmty),cmdgen.UdpTransportTarget((host, 161)),(oid))
	return varBinds[0][1]

def snmpwalk(host,oid,cmty='public'):
	errorIndication, errorStatus, errorIndex,varBinds = cmdgen.CommandGenerator().nextCmd(cmdgen.CommunityData(host, cmty),cmdgen.UdpTransportTarget((host, 161)),(oid))
	return [x[0] for x in varBinds]

def pollwlc(host,cmty='public'):
	return [str(x[1]) for x in snmpwalk(host,'1.3.6.1.4.1.14179.2.2.1.1.3',cmty)]

def getapcount(wlcs,sep='-'):
	aps=sum([pollwlc(wlc) for wlc in wlcs],[])
	return dict(Counter([x.split(sep)[0].upper() for x in aps]))

def usage():
	print 'usage:'
	print '-u username -k api_key --url url -w wlcs (comma separated)'

def parseopt(args):
	url='';api_key='';username='';wlcs=[]
	if len(args)>1:
		try:
			opts=getopt.getopt(args[1:],"u:k:w:",['url='])[0]
		except getopt.GetoptError, err:
			print str(err)
			sys.exit()
		for o,a in opts:
			if o=='-u':
				username=a
			elif o=='-k':
				api_key=a
			elif o=='-w':
				wlcs=a.split(',')
			elif o=='--url':
				url=a
		if url=='' or api_key=='' or username=='' or wlcs==[]:
			usage()
			sys.exit()
	else:
		usage()
		sys.exit()
	return (url,api_key,username,wlcs)
	
if __name__ == '__main__':
	(url,api_key,username,wlcs)=parseopt(sys.argv)
	c=getapcount(wlcs)
	print "%s ap:s" % sum([v for k,v in c.items()])
	r=get("%s?limit=0" % url,headers={'content-type': 'application/json','x-edumeta-username': username,'x-edumeta-api-key':api_key})
	if r.status_code!=codes.ok: sys.exit()
	metacount=0
	for x in json.loads(r.text)['objects']:
		location_ap_no=c.get(x['location_shortname'],0)
		if location_ap_no==0 and (datetime.datetime.strptime(x['last_updated'],'%Y-%m-%dT%H:%M:%S.%f') < (datetime.datetime.now()-datetime.timedelta(days=60))):
			delete("/".join(url.split('/')[:3])+x['resource_uri'],headers={'content-type': 'application/json','x-edumeta-username': username,'x-edumeta-api-key':api_key})
		if x['ap_no']!=location_ap_no:
			patch("%s%s/" % (url,x['id']),headers={'content-type': 'application/json','x-edumeta-username': username,'x-edumeta-api-key': api_key},data=json.dumps({'ap_no':c[x['location_shortname']]}))
			print "%s patched" % x['location_shortname']
		else:
			print "no change at %s: %s ap:s" % (x['location_shortname'],x['ap_no'])
		metacount+=location_ap_no
		if location_ap_no==0:
			print x['location_shortname'],"0"
	print "total ap:s in meta-db: %s" % metacount
