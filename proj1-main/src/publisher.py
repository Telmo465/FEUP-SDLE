from classes import Publisher
import sys

arguments = sys.argv[1:]

pub = Publisher(arguments[0], arguments[1])
pub.run()


