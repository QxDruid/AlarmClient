#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import sys
import curses
import time
import datetime
from threading import Thread, Event
from curses.textpad import Textbox, rectangle
stdscr = curses.initscr()

ADDRESS = '192.168.10.23'
PORT = 3425

# вывод сообщения в статус-баре
def set_status(scr, data, color):
    # закрашиваем все строки статус-бара в нужный background
    for i in range(max_y-statusbar_height, max_y-2):
        scr.addstr(i, max_x-statusbar_width, ' '*statusbar_width, color)

    # пишем статус
    scr.addstr(max_y-statusbar_height//2-2, max_x-len(data)//2-statusbar_width//2, data, color)
    status = data

    # Рисуем рамочку
    rectangle(stdscr, max_y-statusbar_height, max_x-statusbar_width, max_y-2, max_x-1)
    scr.refresh()
    
# вывод даты и времени каждую секунду
def set_time(event, status_timer ,scr):
    wait = 0
    # пока флаг завершения потока не установлен
    while not event.is_set():
        # если поставлен флаг о стирании текущего статуса в статусбаре
        # Засекаем время и устанавливаем флаг wait что таймер запущен
        if status_timer.is_set():
            last_time = int(time.time())
            status_timer.clear()
            wait = 1
        
        # если с момента запуска таймера прошло 3 секунды
        # сбрасываем статус
        if wait == 1 and int(time.time() - last_time) > 3:
            set_status(scr, "Connected to server", curses.color_pair(1))
            wait = 0
        
        # каждую секунду выводим в шапку окна актувальное время
        tm = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        scr.addstr(0, max_x-len(tm)-10, ' '*len(tm))
        scr.addstr(0, max_x-len(tm)-10, tm, curses.A_BOLD)
        scr.refresh()
        time.sleep(1)

    set_status(scr, 'Close thread', curses.color_pair(3))

# обновление записей о тревогах 
def update_data(scr, data):
    # Если сообщений принято больше чем вылезает на экран 
    # удаляем самые ранние ( удаляем не из полного списка сообщений а из списка вывода на экран)
    while len(data) >= (max_y-max_y//6)//3:
        data.pop(0)

    # выводим все сообщения из списка на вывод, в рамочке
    i = 1
    for col in data:
        rectangle(scr, i, 1, i + 2, max_x-2)
        scr.addstr(i+1, 3, col)
        i = i + 3
    # обновляем экран
    scr.refresh()



def main(stdscr):

    # параметры экрана
    stdscr.clear()
    curses.noecho()
    curses.curs_set(0)
    stdscr.timeout(100)

    # рисуем линию вокруг главного окна
    rectangle(stdscr, 0,0, max_y-2, max_x-1)

    # выводим заголовок окна
    data = 'Introscope remote monitor'
    stdscr.addstr(0, max_x//2-len(data)//2, data)
    # создаем сокет для подключения к серверу
    sock = socket.socket()

    set_status(stdscr, 'try to connect server', curses.color_pair(3))

    # пытаемся подлючиться
    try:
        sock.connect((ADDRESS, PORT))
    except:
        sys.exit(1)

    set_status(stdscr, 'Connected to server', curses.color_pair(1))

    # запускаем отдельный поток для управления часами в реальном времени, и других операций со временем
    my_thread = Thread(target=set_time, args=(stop_thread, status_timer, stdscr,))
    my_thread.start()

    # отправляем строку инициализации на сервер (говорим что мы клиент)
    sock.send(b'000006')
    sock.send(b'Client')

    # принимаем статус 'Ок' от сервера после инициализации
    data_len = int(sock.recv(6))
    data = str(sock.recv(data_len), 'utf-8')

    i = 1
    while True:
        # Для корректного завершения второго потока (для контроля часов)
        # отлавливаем KeyboardInterrupt при нажатии CTRL+C
        try:
            # ждем пакеты с данными (сначала принимается длина пакета размером 6 байт, а потом сам пакет)
            data_len = int(sock.recv(6))
            data = str(sock.recv(data_len), 'utf-8')
            # Если пришел статус о включении, высвечиваем зеленую табличку
            if data.split()[3] == 'Power On':
                set_status(stdscr, "Power On Signal", curses.color_pair(2))
                status_timer.set()

            # Если ошибка соединения то пытаемся переподключиться
            if not data:
                sock.close()
                set_status(stdscr, 'try to connect server', curses.color_pair(3))
                while True:
                    try:
                        sock.connect((ADDRESS, PORT))
                    except:
                        pass
                set_status(stdscr, 'Connected to server', curses.color_pair(1))
                                        

                sys.exit(1)

            last_time = datetime.datetime.now()
            set_status(stdscr, "NEW MESSAGE", curses.color_pair(3))
            status_timer.set()
            update_data(stdscr, recieved_data)
            i = i + 1

        # при CTRL+C закрываем сокет, закрываем второй поток, выходим из программы
        except KeyboardInterrupt:
            stop_thread.set()
            sock.close()
            my_thread.join()
            sys.exit(1)
        
# список переменных
recieved_data = []
status = ''
stdscr = curses.initscr()
max_y, max_x = stdscr.getmaxyx()
statusbar_width = max_x//4
statusbar_height = 10

# события для потока времени
status_timer = Event()
stop_thread = Event()

# задаем цвета
curses.start_color()
curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK) # <<---- plain text
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN) # <<---- all good 
curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED) # <<----- alarm

# старт программы (функции мэйн)
curses.wrapper(main)
