from classes import Subscriber
import sys
import threading

#Ponham um nome deum topico
arguments = sys.argv[1:]

sub = Subscriber(arguments[0], arguments[1])

sub.run()

