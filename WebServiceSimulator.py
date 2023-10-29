"""
- Exiting app fixed
- corrected network handling
- TCP port handling from 0 to 65535
- tested with 200ms response from 3 clients
- added error handling
- increased gui window 50px
- buttons greying out added

"""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import PySimpleGUI as sg
from time import sleep
from random import randrange

sg.theme('LightGrey3')
host = 'localhost'
PORT = 8000

# Main data set
liveData = {
    "WebSVCSim": {
        'Mixer1.Temperature.PV': 20,
        'Mixer1.Level.PV': 0,
        'Mixer1.Inlet1.OLS': 1,  # state open/closed
        'Mixer1.Inlet1.CMD': 1,  # turning on/off
        'Mixer1.Inlet2.OLS': 0,
        'Mixer1.Inlet2.CMD': 1,
        'Mixer1.Agitator.OLS': 0,
        'Mixer1.Agitator.CMD': 0,
        'Mixer1.Outlet.OLS': 0,
        'Mixer1.Outlet.CMD': 0,
        # 'temperature_corrected': 0  # used for tesing only
    }
}

# Iteration count
serverAPI = {
    'logServerCountSent': 0,
    'logServerCountRec': 0,
    'logSimCount': 0
}


"""" SIMULATOR ENGINE """


class Simulator:
    def __init__(self):
        self.status = {
            'state': 1,
            'tempFlow': 1,
            'levelFlow': 1,
            'filling': 1,
            'draining': 0,
            'mixing': 0,
        }
        self.mixIter = 0

    def run(self):
        while self.status["state"]:
            """ update values on every iteration """
            if self.status["filling"]:
                self.fillTank()

            if not self.status["filling"] and not self.status["draining"]:
                self.mixTank()

            if self.status["draining"]:
                self.drainTank()

            serverAPI['logSimCount'] += 1
            window['simResponses'].update(serverAPI['logSimCount'])
            simLogString = ""
            for key in liveData["WebSVCSim"]:
                simLogString += f"{key}:  {liveData['WebSVCSim'][key]}" + "\n"
            logSim.update(simLogString)
            sleep(0.5)

    def mixTank(self):
        if self.status["mixing"] and liveData["WebSVCSim"]["Mixer1.Agitator.CMD"]:
            liveData["WebSVCSim"]["Mixer1.Agitator.OLS"] = randrange(
                3700, 3900)
            liveData["WebSVCSim"]["Mixer1.Temperature.PV"] += 5

        self.mixIter += 1
        if self.mixIter == 30:
            self.mixIter = 0
            self.status["mixing"] = 0
            liveData["WebSVCSim"]["Mixer1.Agitator.CMD"] = 0
            liveData["WebSVCSim"]["Mixer1.Agitator.OLS"] = 0
            self.status["draining"] = 1
            liveData["WebSVCSim"]["Mixer1.Outlet.CMD"] = 1

    def fillTank(self):
        if 0 <= liveData["WebSVCSim"]["Mixer1.Level.PV"] < 250 and liveData["WebSVCSim"]["Mixer1.Inlet1.CMD"]:
            liveData["WebSVCSim"]["Mixer1.Level.PV"] += 10

        if liveData["WebSVCSim"]["Mixer1.Level.PV"] == 250:
            liveData["WebSVCSim"]["Mixer1.Inlet1.CMD"] = 0
            liveData["WebSVCSim"]["Mixer1.Inlet2.CMD"] = 1

        if 250 <= liveData["WebSVCSim"]["Mixer1.Level.PV"] < 500 and liveData["WebSVCSim"]["Mixer1.Inlet2.CMD"]:
            liveData["WebSVCSim"]["Mixer1.Level.PV"] += 10

        if liveData["WebSVCSim"]["Mixer1.Level.PV"] == 500:
            liveData["WebSVCSim"]["Mixer1.Inlet2.CMD"] = 0
            self.status["filling"] = 0
            self.status["mixing"] = 1
            liveData["WebSVCSim"]["Mixer1.Agitator.CMD"] = 1

        if liveData["WebSVCSim"]["Mixer1.Inlet1.CMD"] == 1:
            liveData["WebSVCSim"]["Mixer1.Inlet1.OLS"] = 1
        else:
            liveData["WebSVCSim"]["Mixer1.Inlet1.OLS"] = 0

        if liveData["WebSVCSim"]["Mixer1.Inlet2.CMD"] == 1:
            liveData["WebSVCSim"]["Mixer1.Inlet2.OLS"] = 1
        else:
            liveData["WebSVCSim"]["Mixer1.Inlet2.OLS"] = 0

    def drainTank(self):
        if liveData["WebSVCSim"]["Mixer1.Level.PV"] > 0 and liveData["WebSVCSim"]["Mixer1.Outlet.CMD"]:
            liveData["WebSVCSim"]["Mixer1.Level.PV"] -= 10
            liveData["WebSVCSim"]["Mixer1.Temperature.PV"] -= 3

        if liveData["WebSVCSim"]["Mixer1.Level.PV"] == 0:
            liveData["WebSVCSim"]["Mixer1.Outlet.CMD"] = 0
            self.status["draining"] = 0
            self.status["filling"] = 1
            liveData["WebSVCSim"]["Mixer1.Inlet1.CMD"] = 1

        if liveData["WebSVCSim"]["Mixer1.Outlet.CMD"] == 1:
            liveData["WebSVCSim"]["Mixer1.Outlet.OLS"] = 1
        else:
            liveData["WebSVCSim"]["Mixer1.Outlet.OLS"] = 0


""" HTTP SERVER ENGINE """


class HTTPRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """ check if key after post/ exists   """
        if re.search('/api/*', self.path):
            length = int(self.headers.get('content-length'))
            dataRec = self.rfile.read(length).decode('utf8')
            data = json.loads(dataRec)
            itemsToProcess = len(data)
            for one in range(itemsToProcess):
                item = next(iter(data))
                # saving values
                for key, value in liveData['WebSVCSim'].items():
                    if key == item:
                        liveData['WebSVCSim'][item] = data[item]
                        del data[item]

            logServer.print(
                f"{self.requestline[0:4]} request from {self.client_address[0]} ... OK", )
            serverAPI['logServerCountRec'] += 1
            window["serverRec"].update(serverAPI['logServerCountRec'])
            self.send_response(200)
        else:
            self.send_response(403)
            logServer.print(
                f"{self.requestline[0:4]} request from {self.client_address[0]} ... Failed", )
            serverAPI['logServerCountRec'] += 1
        self.end_headers()

    def do_GET(self):
        if re.search('/api/*', self.path):
            record_id = self.path.split('/')[-1]
            # Query main topic
            if record_id == 'WebSVCSim':
                if record_id in liveData:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    data = json.dumps(liveData[record_id]).encode('utf-8')
                    try:
                        self.wfile.write(data)
                    except ConnectionAbortedError:
                        logServer.print(
                            f"Too many requests from ... {self.client_address[0]}")
                    serverAPI['logServerCountSent'] += 1
                    window["serverSent"].update(
                        serverAPI['logServerCountSent'])
                    logServer.print(
                        f"{self.requestline[0:3]} request from {self.client_address[0]} ... OK", )
                else:
                    self.send_response(404, 'Not Found: record does not exist')
                    logServer.print(
                        f"{self.requestline[0:3]} request from {self.client_address[0]} ... Failed", )
            # Query single items
            elif record_id[0:12] == 'WebSVCSim?q=':
                if record_id[12:] in liveData['WebSVCSim']:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    data = json.dumps(
                        liveData['WebSVCSim'][record_id[12:]]).encode('utf-8')
                    self.wfile.write(data)
                    serverAPI['logServerCountSent'] += 1
                    window["serverSent"].update(
                        serverAPI['logServerCountSent'])
                    logServer.print(
                        f"{self.requestline[0:3]} request from {self.client_address[0]} ... OK", )
                else:
                    self.send_response(404, 'Record do not exist in WebSVCSim')
                    logServer.print(
                        f"{self.requestline[0:3]} request from {self.client_address[0]} ... Bad Query", )
            else:
                self.send_response(403)
                logServer.print(
                    f"{self.requestline[0:3]} request from {self.client_address[0]} ... Bad Address", )
                serverAPI['logServerCountSent'] += 1
        else:
            self.send_response(403)
            logServer.print(
                f"{self.requestline[0:3]} request from {self.client_address[0]} ... Bad Address", )
        self.end_headers()

    def log_message(self, format, *args):
        # stop logging to the console
        return


sim = Simulator()
server = None
running = False
simRunning = False


def startWebServer():
    """ first thread """
    try:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return True
    except:
        return False


def startSim():
    """ second thread """
    try:
        sim.status["state"] = 1
        thread2 = threading.Thread(target=sim.run, daemon=True)
        thread2.start()
        return True
    except:
        return False


def stopWebServer():
    try:
        server.shutdown()
        return False
    except:
        logServer.print('Unable to shutdown server...')
        return True


def stopSim():
    try:
        sim.status["state"] = 0
        return False
    except:
        logSim.print('Unable to shutdown SIM...')
        return True


# GUI window layout
btnSize = (10, 2)
logBoxSize = (50, 14)
incomingLogData = ['Logger...']

saveIPbtn = sg.Button('Save', key='-SAVE IP-',
                      size=(10, 1), enable_events=True)
connection_frame = [
    [sg.Text("IP/Hostname: "), sg.Input(default_text="localhost", key='-IP-', size=20),
     sg.Text(f"Default:'{host}'"),
     sg.Text("Port"), sg.Input(default_text="8000", key='-PORT-', size=10),
     # sg.Text(f"Default:{PORT}"),
     sg.Push(),
     saveIPbtn
     ]]

info_frame = [[sg.Text(
    "--- Save Hostname and Port Configuration ---", pad=(250, 7), key='fullAddress')]]

logServer = sg.Multiline(size=logBoxSize, font=('Courier', 8))
logSim = sg.Multiline(size=logBoxSize, font=('Courier', 8))
startServerBtn = sg.Button('Start Server', key='-START SERVER-',
                           size=btnSize, enable_events=True, disabled=True)
# stopServerBtn = sg.Button('Stop Server', key='-STOP SERVER-', size=btnSize, disabled=True)

server_layout = [[logServer],
                 [startServerBtn,
                  # stopServerBtn,
                  sg.Push(),
                  # sg.Text('Rx:'), sg.Text("-", key='serverRec'),
                  # sg.Text('Tx:'), sg.Text("-", key='serverSent')
                  ]]

startSimBtn = sg.Button('Start Sim', key='-START SIM-',
                        size=btnSize, enable_events=True, disabled=True)
stopSimBtn = sg.Button('Stop Sim', key='-STOP SIM-',
                       size=btnSize, disabled=True)

sim_layout = [[logSim],
              [startSimBtn,
               stopSimBtn,
               sg.Push()
               ]]
activity = [[sg.Text('Rx:'), sg.Text("-", key='serverRec'),
             sg.Text('Tx:'), sg.Text("-", key='serverSent'), sg.Text('SIM Step: '), sg.Text("-", key='simResponses')]]
layout = [[sg.Frame('', connection_frame, expand_x=True)],
          [sg.Frame('Server URL', info_frame, expand_x=True)],
          [sg.Frame('SERVER - LOG', server_layout),
           sg.Frame('SIM - LOG', sim_layout)],
          [sg.Frame('STATUS', activity), sg.Push(), sg.Button('Exit', key='Exit', size=btnSize)]]

# Main window
window = sg.Window('WebSVCSim v1.03c', layout,
                   size=(800, 450), icon='logoICO.ico')


# START
while True:
    event, values = window.read()
    if event == 'Exit' or event == sg.WIN_CLOSED:
        # kill loop and threads
        break

    elif event == '-START SERVER-':
        if not running:
            running = startWebServer()
            logServer.print(f"API Started on ... {host}:{PORT}")
            startServerBtn.update(disabled=True)
        else:
            logServer.print("API Already running...")

    elif event == '-STOP SERVER-':
        if running:
            running = stopWebServer()
            logServer.print("API Stopped...")
        else:
            logServer.print("API Already stopped...")

    elif event == '-START SIM-':
        if not simRunning:
            logSim.print("SIM Started...")
            simRunning = startSim()
            startSimBtn.update(disabled=True)
            stopSimBtn.update(disabled=False)
        else:
            logSim.print("SIM Already running...")

    elif event == '-STOP SIM-':
        if simRunning:
            simRunning = stopSim()
            logSim.print("SIM Stopped...")
            startSimBtn.update(disabled=False)
            stopSimBtn.update(disabled=True)
        else:
            logSim.print("SIM Already stopped...")

    elif event == '-SAVE IP-':
        host = values["-IP-"]
        PORT = int(values["-PORT-"])
        server = HTTPServer((f"{host}", PORT), HTTPRequestHandler)
        hostFull = f"http://{host}:{PORT}/api/WebSVCSim"
        window["fullAddress"].update(hostFull)
        saveIPbtn.update(disabled=True)
        startServerBtn.update(disabled=False)
        # stopServerBtn.update(disabled=False)
        stopSimBtn.update(disabled=False)
        startSimBtn.update(disabled=False)
