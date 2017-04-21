import sys, traceback
#import framework.stats
from framework.engine import Game 
from game.stages import presentation, memory, invaders, pagination, questions, backpack, content, map, running, asteroids
from game.data import datastore
import urllib2

def main():
    try:
        # Without this the web module doesn't work with in the encrypted version.
        # it gets stuck in a socket.getaddrinfo, don't know why
        try:
          r = urllib2.urlopen("localhost")
          r.close()
        except:
          pass
        g = Game('DGI', None, None)
        
    
        # Set up initial data
        g.datastore = datastore.Datastore()
        
        # Run the game    
        initial_stage = presentation.Presentation(g);
        g.run(initial_stage)   
    except:
        print "An unexpected error occurred, and the application was closed."
        traceback.print_exc()        
        type, value, tb = sys.exc_info()
    
if __name__ == "__main__":
    main()
