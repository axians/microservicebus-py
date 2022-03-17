
import psutil, utils

networks = []
# interfaces = netifaces.interfaces()
# for interface in interfaces:
#     addrs = netifaces.ifaddresses(interface)
#     if netifaces.AF_INET in addrs.keys():
#         # print(interface)
#         # print(addrs[netifaces.AF_INET][0])
#         # print(utils.getHwAddr(interface))
#         ni = {
#                 "name": interface, 
#                 "ipaddress":addrs[netifaces.AF_INET][0]["addr"], 
#                 "mac_address": utils.getHwAddr(interface), 
#                 "netmask":addrs[netifaces.AF_INET][0]["netmask"],
#                 "type": ''}
#         networks.append(ni)

print (networks)

