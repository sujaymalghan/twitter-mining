####################################################################                            						   #        
# ver    : 1.0                                                     #
# Name : sujay vishwanath malghan                       #
####################################################################

import twitter
import json
import sys 
import time
import json
from functools import partial
from six import string_types
from datetime import datetime
from datetime import timedelta
from functools import partial
from sys import maxsize as max_integer
import collections 
from collections import Counter
import networkx as netx 
import matplotlib.pyplot as plot
from operator import itemgetter

# Verifying the Twitter Developer account's login information
class getAuthorization:
    @staticmethod
    def twitter_login():
        try:
            # Go to http://dev.twitter.com/apps/new to create an app and get values
            # for these credentials, which you'll need to provide in place of these
            # empty string values that are defined as placeholders.
            # See https://developer.twitter.com/en/docs/basics/authentication/overview/oauth

            CONSUMER_KEY = ''
            CONSUMER_SECRET = ''
            OAUTH_TOKEN = ''
            OAUTH_TOKEN_SECRET = ''

            # The twitter.Twitter class is used to create a Twitter API object, 
            # which can be used to interact with the Twitter API endpoints. The constructor takes one argument, 
            # which is the auth parameter, that is set to the OAuth authentication object created earlier

            auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                                       CONSUMER_KEY, CONSUMER_SECRET)

            twitter_api = twitter.Twitter(auth=auth)

            # Nothing to see by displaying twitter_api except that it's now a
            # defined variable
            return twitter_api
        
        except Exception as e:
            print ("Problem during authorizing an Account", e)

# Handling  HTTP Errors for Twitter
class errorHandling:
    def error_handling(exct, wait_period=2, sleep_when_rate_limited=True):
        
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise exct

        if exct.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None

        elif exct.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        
        #A code of 429 means that the rate limit for the API has been exceeded, 
        #while a code of 420 means that the request was rate limited due to too many requests in a short period of time.
        elif exct.e.code in (429,420):
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise exct # Caller must handle the rate limiting issue
            
        #500: Internal Server Error
        #502: Bad Gateway
        #503: Service Unavailable
        #504: Gateway Timeout
        elif exct.e.code in (500,502,503,504):
            print('Encountered {0} Error. Retrying in {1} seconds'.format(exct.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise exct
        
# Class for all the twitter API calls
class twitter_data:
    #Constructor to set the twitter_api
    def __init__(self, set_twitter_api):
        self.twitter_api = set_twitter_api
        
    #-get the followers IDs -----------------
    def get_friends_followers_ids(self, screen_name=None, user_id=None,
                                  friends_limit=max_integer, followers_limit=max_integer):

        # Must have either screen_name or user_id (logical xor)
        assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"

        # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
        # on API parameters

        get_friends_ids = partial(self.make_twitter_request , self.twitter_api.friends.ids, 
                                  count=5000)
        get_followers_ids = partial(self.make_twitter_request, self.twitter_api.followers.ids, 
                                    count=5000)

        friends_ids, followers_ids = [], []

        for self.twitter_api_func, limit, ids, label in [
                        [get_friends_ids, friends_limit, friends_ids, "friends"], 
                        [get_followers_ids, followers_limit, followers_ids, "followers"]
                    ]:

            if limit == 0: continue

            cursor = -1
            while cursor != 0:

                # Use make_twitter_request via the partially bound callable...
                if screen_name: 
                    response = self.twitter_api_func(screen_name=screen_name, cursor=cursor)
                else: # user_id
                    response = self.twitter_api_func(user_id=user_id, cursor=cursor)

                if response is not None:
                    ids += response['ids']
                    cursor = response['next_cursor']

                #print('Fetched {0} total {1} ids for {2}'.format(len(ids),label, (user_id or screen_name)),file=sys.stderr)

                # XXX: You may want to store data during each iteration to provide an 
                # an additional layer of protection from exceptional circumstances

                if len(ids) >= limit or response is None:
                    break

        # Do something useful with the IDs, like store them to disk...
        return friends_ids[:friends_limit], followers_ids[:followers_limit]
    
    # sending the parameters and references for the callable functions
    def make_twitter_request(self,twitter_api_func,max_errors=10,*args, **kw):
        wait_period = 2
        error_count =0

        while True:
            try:
                return twitter_api_func(*args, **kw)
            except twitter.api.TwitterHTTPError as e:
                error_count = 0
                wait_period = errorHandling.error_handling(e,wait_period)
                if wait_period is None:
                    return

            except URLError as e:
                error_count +=1
                print >> sys.stderr, 'URLError encountered. Continuing.'
                if error_count > max_errors:
                    print >> sys.stderr, 'Too many errors...bailing out.'
                    raise

            except BadStatusLine as e:
                error_count +=1
                print >> sys.stderr, 'BadStatusLine encountered. Continuing.'
                if error_count > max_errors:
                    print >> sys.stderr, 'Too many consecutive errors...bailing out.'
                    raise

        # getting the user Profile information
    def get_user_profile(self, screen_names=None, user_ids=None):
        # Must have either screen_name or user_id (logical xor)
        assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
        items_to_info = {}
        items = screen_names or user_ids
        while len(items) > 0:

            # Process 100 items at a time per the API specifications for /users/lookup.
            # See http://bit.ly/2Gcjfzr for details.

            items_str = ','.join([str(item) for item in items[:100]])
            items = items[100:]

            if screen_names:
                response = self.make_twitter_request(self.twitter_api.users.lookup, 
                                                screen_name=items_str)
            else: # user_ids
                response = self.make_twitter_request(self.twitter_api.users.lookup, 
                                                user_id=items_str)
            for user_info in response:
                if screen_names:
                    items_to_info[user_info['screen_name']] = user_info
                else: # user_ids
                    items_to_info[user_info['id']] = user_info
        return items_to_info
        
    # obtaining the top n followers based on the followers count               
    def get_top_followers(self, all_followers, top_n):
        top_followers = {}
        for follower in all_followers:
            followers_info = self.get_user_profile(user_ids = [follower])
            top_followers.update({followers_info[follower]["id"] : followers_info[follower]["followers_count"]})
        if(len(top_followers) >= top_n):
            min_value = sorted(top_followers.values(), reverse=True)[top_n-1]
        elif(len(top_followers) > 1):
            min_value = sorted(top_followers.values(), reverse=True)[len(top_followers)-1]
        else:
            min_value = 0
        top_followers = {key:value for key,value in top_followers.items() if value >= min_value}
        return top_followers
    
    # The method then returns this list of top reciprocal friends.
    def get_top_n_reciprocal_friends(self, id, top_n = 5):
        friends_ids, followers_ids = self.get_friends_followers_ids(
                                                       user_id = id, 
                                                       friends_limit=50, 
                                                       followers_limit=50)
        return self.get_top_followers(set(friends_ids) & set(followers_ids), top_n = top_n)

    # crawling the top_n followers to get their top_n followers
    def crawl_followers(self, screen_name, minimum_limit=1000, depth=10):
        try:
            userInfo = self.make_twitter_request(self.twitter_api.users.show, screen_name=screen_name)
            id = userInfo['id']
            connection_dictionary = {}
            connection_graph_list = []
            unique_friends = []
            next_queue = self.get_top_n_reciprocal_friends(id)
            connection_dictionary.update({id : list(next_queue)})
            connection_graph_list.append(id)
            connection_graph_list.extend(list(next_queue.keys())) 
            self.graph_obj.add_a_node(id)
            self.graph_obj.add_node(list(next_queue.keys()))
            for n in list(next_queue.keys()):
                self.graph_obj.add_a_edge((id,n))
            d = 1
            next_queue_list = list(next_queue.keys())
            while len(connection_graph_list) < minimum_limit :
                d += 1
                (queue, next_queue_list) = (list(set(next_queue_list)), [])
                for fid in queue:
                    top_n_reciprocal_friends = self.get_top_n_reciprocal_friends(fid)
                    unique_friends = list(set(top_n_reciprocal_friends) - set(connection_graph_list))
                    connection_graph_list += unique_friends
                    #adding new nodes to graph
                    self.graph_obj.add_node(unique_friends)
                    for n in top_n_reciprocal_friends:
                        self.graph_obj.add_a_edge((fid,n))
                    connection_dictionary.update({fid : unique_friends})
                    next_queue_list +=  unique_friends
                    if(len(connection_dictionary) > minimum_limit):
                        return connection_dictionary
            return connection_dictionary
        except:
            print("Error at crawl_followers")

    # creating the graph_class object
    def create_a_graph_obj(self):
        graph_obj  = graph_class()
        self.graph_obj = graph_obj

    #Display the graph output 
    def show_graph(self):
        self.graph_obj.display_graph()



#Graph Class for all the graph related API calls 
class graph_class:
    #Constructor of the class to define the sn = social network graph 
    def __init__(self):
        self.sn_graph = netx.Graph()

    #Add nodes from a list to the existing graph
    def add_node(self, node_list):
        self.sn_graph.add_nodes_from(node_list)

    #Add a node to the existing graph
    def add_a_node(self, node):
        self.sn_graph.add_node(node)

    #Add edges from a list to the existing graph 
    def add_edge(self, edge_list):
        self.sn_graph.add_edges_from(edge_list)

    # Add a edge to the existing graph 
    def add_a_edge(self, edge):
        self.sn_graph.add_edge(*edge)

    # Display the graph information on the console
    def display_graph(self):
        file = open("FinalOutputFile.txt","w") 

        file.write("\nSize of Network in terms of Nodes : " + str(self.sn_graph.number_of_nodes())) 
        print("Network size interms of nodes : ", self.sn_graph.number_of_nodes())

        file.write("\nSize of Network in terms of Edges : : " + str(self.sn_graph.number_of_edges()))
        print("Network size interms of edges : : ",self.sn_graph.number_of_edges())

        file.write("\nSize of Network in terms of Diameter : " + str(netx.diameter(self.sn_graph, e=None, usebounds=False)))
        print("Network size interms of Diameter : " , netx.diameter(self.sn_graph, e=None, usebounds=False))

        file.write("\nSize of Network in terms of Average distance : " +  str(netx.average_shortest_path_length(self.sn_graph, weight=None)))
        print("Network size interms of Average distance : " , netx.average_shortest_path_length(self.sn_graph, weight=None))

        file.close() 
        netx.draw(self.sn_graph, with_labels=True)
        plot.savefig('OutputGraphView.png', bbox_inches=0, orientation='landscape', pad_inches=0.5)
        plot.show()

def main():
    try:
        print("Printing the First Objective : ")
        print("-------------------------------------------------------------------")
        print("Using Professor username on Twitter")
        username="edmundyu1001"
        print("Twitter Username : " , username)
        authorization = getAuthorization()
        Obj = twitter_data(authorization.twitter_login())
        friends_ids, followers_ids = Obj.get_friends_followers_ids(
                                                           username, 
                                                           friends_limit=5000, 
                                                           followers_limit=5000)
        print("\n\Printing  Second objective : ")
        print("-------------------------------------------------------------------")
        print("Fetching friends and followers list of user = ",username)
        print("Friends list for = ",username)
        print(friends_ids)
        print("Followers list of  = ",username)
        print(followers_ids)

        print("\n\nPrinting Third Objective: ")
        print("-------------------------------------------------------------------")
        print("Fetching Reciprocal Friends of the user = ",username)
        print("Selected Reciprocal Friends list :")
        recipr_friends = set(friends_ids) & set(followers_ids)
        print(recipr_friends)

        print("\n\Printing Fourth Objective : ")
        print("-------------------------------------------------------------------")
        print("Fetching top 5 Reciprocal Friends of the user")
        print("Selected Top 5 Friends list :")
        print(Obj.get_top_followers(recipr_friends , top_n = 5))

        
        print("\n\n Printing Fifth objective: ")
        print("-------------------------------------------------------------------")
        print("Moving to the friends of user who are at 'distance-1', 'distance-2' etc form a network")
        Obj.create_a_graph_obj()
        Obj.crawl_followers(screen_name = username, minimum_limit=100, depth = 10)

        print("\n\Printing Sixth and Seventh Objective : ")
        print("-------------------------------------------------------------------")
        print("Creating a social network based on the results from Req 5")
        Obj.show_graph()

    except twitter.api.TwitterHTTPError as e:
        print("Error occured while running the program. Please run again after sometime")

if __name__ == "__main__":
    main()
