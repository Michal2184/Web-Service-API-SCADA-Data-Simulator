# Web-Service-API-SCADA-Data-Simulator

This API has been made to mainly for testing, learning purpose for wide range of SCADA Data acusation software. Can be used by 2 mainstream SCADA software like Ignition and Wonderware. 
Simulator contains graphical user interface build using PySimpleGUI and is running using two threads to create non blocking Http server returning and accepting JSON loads.

Upon starting you need to provide hostname and port number you would like to use 
- TCP port handling from 0 to 65535
- tested with 200ms response from 3 clients
