#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
snetworks.py - 23.04.2017
Автор: Ерофеев Павел - ps.erofeev@gmail.com

'''

import nmap # модуль для сканирования ip сетей
from sys import argv # модуль для передачи аргуметов программе в момент ее запуска
import re # модуль для использования регулярных выражений
from os import path # модуль для получения переменных окружения linux


def sort_by_length(input_str): # функция для сортировки ip адресов в полученных списках
    return len(input_str)

def generation_networks_list(users_enter):

    '''
    Функция возвращает список подсетей, полученный из строки, введенной пользователем.
    Функция принимает любое количество подсетей в формате network/mask,
    введеных через пробел, e.g. 192.168.50.0/24 185.7.200.0/24 networks.txt.
    Кроме того, подсети могут быть перечислены в файле c расширением txt.
    Внутри файла сети перечисляются через пробел или с новой строки.

    '''

    if type(users_enter) == str:
        networks_l = users_enter.split() # преобразуем ввод пользователя в список
    else:
        networks_l = users_enter
    networks_ready = [] # создаем итоговый список, который вернет функция
    for network in networks_l:
        if '.txt' in network: # достаем подсети из файла и добавляем их в список networks_ready
            with open(path.expanduser('~') + '/' + network) as f:
                f = f.read()
                networks_from_file = re.split('[\n ]',f.rstrip()) # превращаем считанную строчку в список, используя в качестве разделителя символ новой строки \n или пробел ' ' - [\n ]
            for network in networks_from_file:
                if not network in networks_ready: # можно было бы обойтись без этой проверки, если использовать множества. Но используя множества, наружается последовательность пользовательского ввода данных, что хочется сохранить, поэтому используеются два дополнительных if
                    networks_ready.append(network)
        else:
            if not network in networks_ready:
                networks_ready.append(network)

    return networks_ready

def scan_free_networks(networks_list):

    '''
    Функция для сканирования свободных подсетей на наличие используемых в них ip адресов

    '''

    # создаем списки, которые вернет функция
    free_networks = []
    used_networks = []

    for network in networks_list:
        if '/' in network: # проверка на наличие маски в заданой подсети
                           # маска может отсутствовать, если это loopback или доменное имя (e.g. ya.ru)
            mask = network.split('/')[1] # получаем значение сетевой маски, далее проверяем ее корректность
            if mask.isdigit():
                mask = int(mask)
            else:
                print '\n%s проверить невозможно. Некорректная маска.' % network
                continue
            if mask < 0 or mask > 32:
                print '\n%s проверить невозможно. Некорректная маска.' % network
                continue
            if mask < 20:
                print '\n%s не проверена. Подсеть слишком большая. Максимально допустимая подсеть - /20' % network
                continue

        nm = nmap.PortScanner() # создаем объект для сканирования
        result_scan = nm.scan(hosts = network, arguments='-n -sP -PE')
        '''
        Производим сканирование одной network, результат в виде словаря присваиваем новой
        переменной result_scan. Ключи в переменной arguments:
        '-n' - no DNS resolution;
        '-sP' - указываем протокол для сканирования, в данном случае IP protokol. Так же существуют:
            '-sT' - for TCP';
            '-sU' - for UDP;
            '-sS' - for SCTP;
        '-PE' - ICMP ping type, опция, включающая echo request behavior.
        Подробная информацю по ключам здесь https://nmap.org/book/man-host-discovery.html

        '''
        all_hosts = nm.all_hosts()
        all_hosts.sort(key=sort_by_length)

        if int(result_scan['nmap']['scanstats']['uphosts']) != 0: # проверка на наличие активных хостов в подсети
            used_networks.append((network, all_hosts))
        else:
            free_networks.append(network)

    return used_networks, free_networks


def scan_used_networks(networks_list):

    '''
    Функция для сканирования занятых подсетей на наличие свободных

    '''

    # создаем списки, которые вернет функция
    free_networks = []
    used_networks = []
    need_verify_networks = []

    for network in networks_list:
        nm = nmap.PortScanner()
        mask = 32 # объявление переменой mask с указанием значения по умолчанию
                  # значение по умолчанию требуется для выполнения дальнейшей логики работы данной функции
        if '/' in network: # проверка на наличие маски в заданой подсети
                           # маска может отсутствовать, если это loopback или доменное имя (e.g. ya.ru)
            mask = network.split('/')[1] # получаем значение сетевой маски, далее проверяем ее корректность
            if mask.isdigit():
                mask = int(mask)
            else:
                print '\n%s проверить невозможно. Некорректная маска.' % network
                continue
            if mask < 0 or mask > 32:
                print '\n%s проверить невозможно. Некорректная маска.' % network
                continue
            if mask < 20:
                print '\n%s не проверена. Подсеть слишком большая. Максимально допустимая подсеть - /20' % network
                continue

        # с точки зрения данного блока программы все занятые подсети делятся на подсети с маской < 31
        # и > 30 (31,32). Подсети с маской 31, 32 не проверяются на наличие шлюза.
        if mask < 31:
            result_scan = nm.scan(hosts = network, arguments='-n -sP -PE -PS21,22,23,80,3389')
            '''
            Новый ключ в переменной arguments - '-PS' - TCP SYN Ping. После ключа можно указть список
            портов, по которым устройство будет просканировано (обязательно без пробела!). В нашем случае
            порты будут задейстованы, если не придет ответ на icmp запрос (-PE). Порты включены, так как на
            некоторых устройствах может быть закрыт icmp. Включение портов увеличвает время сканирования,
            но так как данная функция подразумевает сканирование заведомо активных подсетей, то это не
            отразится на общем времени выполнения программы.

            '''
            all_hosts = nm.all_hosts()
            all_hosts.sort(key=sort_by_length)

            if int(result_scan['nmap']['scanstats']['uphosts']) == 0: # проверка, не свободна ли сеть
                free_networks.append(network)
            else:
                '''
                Подразумевается, что любая занятая сеть назначена в первую очередь интерфейсу маршрутизатора
                - первый ip подсети. Поэтому каждая занятая подсеть будет проверяться на то, активен первый
                адрес подсети или нет. Для этого ниже выполняется процедура получения из адреса, введенного
                пользователем, первого адреса подсети.

                Если шлюз неактивен, а в подсети есть активные хосты, считается, что подсеть занята,
                но ее требуется проверить.

                '''
                ip_s = network.split('/')[0] # получаем ip адрес без сетевой маски в формате строки
                ip_l = ip_s.split('.') # разделяем строку на октеты
                ip_bin = '' # объявляем пременную, которой позже присвоим двоичное значение ip
                for octet in ip_l:
                    ip_bin += bin(int(octet))[2:].zfill(8) # получаем двоичное значение ip адреса
                first_ip_bin = ip_bin[0:mask] + '1'.zfill(32-mask) # получаем двоичную послед-ть первого ip
                first_ip_bin_l = [first_ip_bin[i:i+8] for i in range(0,32,8)] # разбиваем послед-ть на 4 части
                for position,octet in enumerate(first_ip_bin_l): # получаем список из 10-ых значений первого ip
                    first_ip_bin_l[position] = str(int(octet,2))
                first_ip = '.'.join(first_ip_bin_l) # получаем первый ip адрес
                if first_ip in all_hosts: # проверка на то, присутствует ли первый ip в активных хостах
                    used_networks.append((network, all_hosts)) # если да, подсеть используется
                else:
                    # подсеть используется, но требует проверки
                    need_verify_networks.append((network, all_hosts))
        else:
            # сканируем подсети /31 и /32 - ptp и loopback
            result_scan = nm.scan(hosts = network, arguments='-n -sP -PE -PS21,22,23,80,3389')
            if int(result_scan['nmap']['scanstats']['uphosts']) == 0:
                free_networks.append(network)
            else:
                used_networks.append((network, nm.all_hosts()))

    return free_networks, need_verify_networks, used_networks


def output_scan_free_networks(used_networks, free_networks):

    '''
    Функция, формирующая строчку для записи или вывода на экран результата сканирования свободных подсетей.

    '''

    line = ''
    if used_networks:
        for network,hosts in used_networks:
            line += '\n%s' %('-'*35)
            line += '\n{0:18} используется:'.format(network)
            for host in hosts:
                line += '\n  {0:18} is up'.format(host)
        line += '\n'
    if free_networks:
        for network in free_networks:
            line += '\n%s' %('*'*35)
            line += '\n{0:18} свободна'.format(network)
        line += '\n'                                                                                              
    return line


def output_scan_used_networks(free_networks, need_verify_networks, used_networks):

    '''
    Функция, формирующая строчку для записи или вывода на экран результата сканирования занятых подсетей.

    '''

    line = ''
    if free_networks:
        for network in free_networks:
            line += '\n%s' %('*'*35)
            line += '\n{0:18} свободна'.format(network)
        line += '\n'
    if need_verify_networks:
        for network,hosts in need_verify_networks:
            line += '\n%s' %('+'*59)
            line += '\n{0:18} используется, но требуется проверить:'.format(network)
            for host in hosts:
                line += '\n  {0:18} is up'.format(host)
        line += '\n'
    if used_networks:
        for network,hosts in used_networks:
            line += '\n%s' %('-'*35)
            line += '\n{0:18} используется:'.format(network)
            for host in hosts:
                line += '\n  {0:18} is up'.format(host)
        line += '\n'

    return line

try:
    if len(argv) > 1:
        users_enter = argv[1:]
        networks_ready = generation_networks_list(users_enter)
        used_networks, free_networks = scan_free_networks(networks_ready)
        print output_scan_free_networks(used_networks, free_networks)

    else:
        mode = raw_input('\nКакие подсети Вы хотите проверить?\nзанятые - ведите u\nсвободные - f или оставьте это поле пустым\nu/f: ')
        mode = mode.lower() # делаем переменную нечуствительной к регистру
        users_enter = raw_input('\nВведите через пробел подсети, требующие проверки. В этой же строке Вы можете указать текcтовый файл,\nсодержащий в себе подсети. Подсети внутри файла должны перечисляться чере пробел или с новой строки.\nПример вводимой строки: 192.168.0.0/24 networks.txt 176.221.14.0/26. В имени файла не допускается\nиспользование пробелов. Максимально допустимая подсеть - /20.\nМаска подсети указывается через /, без пробелов.\n\nВаш ввод: ')
        file_w = raw_input('\nЗаписать результат в файл?\ny/n: ')
        file_w = file_w.lower()
        if file_w == 'y' or file_w == 'yes':
            file_name = raw_input('\nУкажите имя файла (e.g. result.txt),\nили результат будет записан в result_snetworks.txt: ')
            output_on_display = raw_input('\nВывести результат на экран?\ny/n: ')
            output_on_display = output_on_display.lower()

        networks_ready = generation_networks_list(users_enter) # получаем список подсетей для сканирования

        if mode == 'u':
            free_networks, need_verify_networks, used_networks = scan_used_networks(networks_ready)
            output_string = output_scan_used_networks(free_networks, need_verify_networks, used_networks)
            if file_w == 'y' or file_w == 'yes':
                if file_name:
                    if '.txt' in file_name:
                        file_name = file_name
                    else:
                        file_name = file_name + '.txt'
                else:
                    file_name = 'result_snetworks.txt'
                with open (path.expanduser('~') + '/' + file_name, 'w') as f:
                    f.write(output_string)
                if output_on_display == 'y' or output_on_display == 'yes':
                    print output_string
            else:
                print output_string
        else:
            used_networks, free_networks = scan_free_networks(networks_ready)
            output_string = output_scan_free_networks(used_networks, free_networks)
            if file_w == 'y' or file_w == 'yes':
                if file_name:
                    if '.txt' in file_name:
                        file_name = file_name
                    else:
                        file_name = file_name + '.txt'
                else:
                    file_name = 'result_snetworks.txt'
                with open (path.expanduser('~') + '/' + file_name, 'w') as f:
                    f.write(output_string)
                if output_on_display == 'y' or output_on_display == 'yes':
                    print output_string
            else:
                print output_string

except IOError:
    print '\nУказанный Вами файл не найден. Проверьте имя файла и повторите попытку.\n'
except (IndexError, UnicodeDecodeError, nmap.nmap.PortScannerError):
    print '\nУказанные Вами даные некорректны.\nПроверьте их содержимое и повторите попытку.\n'