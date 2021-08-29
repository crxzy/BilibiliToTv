from contextlib import contextmanager
import socket
import select
import time
import requests
import traceback
import re
from lxml import etree

SSDP_VERSION = 1
SSDP_ALL = "ssdp:all"
SSDP_GROUP = ("239.255.255.250", 1900)

@contextmanager
def _send_udp(to, packet):
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
   sock.sendto(packet.encode(), to)
   yield sock
   sock.close()

class Devices:

    def _get_location_url(self):
        t = re.findall('\n(?i)location:\s*(.*)\r\s*', self.__raw, re.M)
        if len(t) > 0:
            return t[0]
        return ''

    def __get_port(self):
        port = re.findall('http://.*?:(\d+).*', self.__raw)
        return int(port[0]) if port else 80

    def __str__(self) -> str:
        return "name:{}@{}:{}, control_url:{}, rendering_contorl_url:{}".format(self.name, self.ip, self.port, self.control_url, self.rendering_control_url)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Devices) and self.ip == o.ip and self.name == o.name and self.port == o.port

    def __init__(self, raw, ip, ssdp_version=1):
        self.ip = ip
        self.ssdp_version = ssdp_version

        self.port = None
        self.name = 'Unknown'
        self.control_url = None
        self.rendering_control_url = None
        self.service_type = None
        self.has_av_transport = False

        #print("\n{}\n".format(raw.decode()))

        try:
            self.__raw = raw.decode()

            self.location = self._get_location_url()
            #print(self.location)

            self.port = self.__get_port()
            #print(self.port)

            raw_desc_xml = requests.get(self.location).text
            #print(raw_desc_xml)    

            root = etree.fromstring(raw_desc_xml)
            ns = {'all': root.nsmap[None]}

            self.name = root.xpath('//all:device/all:friendlyName', namespaces=ns)[0].text.encode('ISO-8859-1').decode('UTF-8')
            services = root.xpath('//all:device/all:serviceList//all:service', namespaces=ns)

            for service in services:
                service_type = None
                control_url = None
                for e in service:
                    if 'serviceType' in e.tag:
                        service_type = e.text
                    if 'controlURL' in e.tag:
                        control_url = e.text
                
                if 'AVTransport' in service_type:
                    self.service_type = service_type
                    self.control_url = control_url
                    break

            self.has_av_transport = self.control_url is not None



        except Exception as e:
            print("ip = {}, init exception: {}\n".format(ip, traceback.format_exc()))


    def play(self, url):
        if not self.has_av_transport:
            raise Exception('this device does not support this operation')

        header = {
            "User-Agent": "bilibiliTv",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "SOAPAction": "\"{}#SetAVTransportURI\"".format(self.service_type),
            "Host": "{}:{}".format(self.ip, self.port),
            "Content-Type": "text/xml",
        }

        template = '''
            <?xml version="1.0" encoding="UTF-8"?>
            <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                <s:Body>
                    <u:SetAVTransportURI xmlns:u="{}">
                        <InstanceID>0</InstanceID>
                        <CurrentURI>{}</CurrentURI>
                        <CurrentURIMetaData></CurrentURIMetaData>
                    </u:SetAVTransportURI>
                </s:Body>
            </s:Envelope>
        '''
        template = template.format(self.service_type, url)
        resp = requests.post("http://{}:{}/{}".format(self.ip, self.port, self.control_url), headers=header, data=template)
        
        return resp.status_code == 200


class Tv:
    def __init__(self):
        pass

    def descover(self, timeout=1):
        payload = "\r\n".join([
              'M-SEARCH * HTTP/1.1',
              'User-Agent: {}/{}'.format("bilibiliToTv", "0.1"),
              'HOST: {}:{}'.format(*SSDP_GROUP),
              'Accept: */*',
              'MAN: "ssdp:discover"',
              'ST: {}'.format(SSDP_ALL),
              'MX: {}'.format(3),
              '',
              ''])
        devices = []

        with _send_udp(SSDP_GROUP, payload) as sock:
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    break
                r, w, x = select.select([sock], [], [sock], 1)
                if sock in r:
                    data, addr = sock.recvfrom(1024)

                    d = Devices(data, addr[0], SSDP_VERSION)

                    if d not in devices:
                        devices.append(d)                            
                elif sock in x:
                    raise Exception('something wrong')

        return devices
