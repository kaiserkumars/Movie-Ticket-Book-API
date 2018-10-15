# Documentation link : https://documenter.getpostman.com/view/2942307/RWgrxcgm

import flask
import os
import json
from flask_pymongo import PyMongo
from flask import jsonify
from flask import request
from bson.json_util import dumps
from flask import Response

try:
    from .local_settings import *
except ImportError:
    pass


app = flask.Flask(__name__)
# This poject is connected to a mongo database. The configuration is below.
app.config.from_pyfile('config.cfg')
app.config["MONGO_URI"]
app.config["DEBUG"] = False
mongo = PyMongo(app)
# Database name is 'udaan' and the collection name is 'ticketbooker'.
bookticket = mongo.db.ticketbooker

# 404 errorhandler
@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@app.route('/',methods=['GET'])
def eureka():
    return "<h1>Eureka!It works.</h1>",200


# API to accept details of a movie screen. A valid request will add a new screen(document) to thecollection 
@app.route('/screens', methods=['POST'])
def add_screen():
    # parsing request data into python dictionary
    load_data = json.loads(request.data)
    try:
        # Adding a new key-value pair to keep track of reserved seats.
        trackBooking = {}
        for i in load_data['seatInfo']:
            seat_status = {}
            for j in range(load_data['seatInfo'][i]['numberOfSeats']):
                # Initializing all seats with value 0. 0 means unreserved, 1 means reserved
                seat_status[str(j)] = 0
            trackBooking[i] = seat_status            
        load_data['trackBooking'] = trackBooking
        # inserting the screen information in our ticketbooker collection of udaan database.     
        bookticket.insert(load_data)
        return jsonify({'status' : 'OK'})
    except Exception as e:
        return jsonify({'status' : 'Error'})

# API to reserve tickets for given seats in a given screen.
@app.route('/screens/<screen_name>/reserve', methods=['POST'])
def reserve_tickets(screen_name):
    load_data = json.loads(request.data)
    try:
        # findind the requested screen in the databse.
        retrieved_screen_data = bookticket.find_one({'name':screen_name})
        flag = 0
        # if any of the seats is already reserved we break 
        for k in load_data['seats']: # variable k represents the row .
            for i in load_data['seats'][k]:
                # check if row present or not
                if k not in retrieved_screen_data['trackBooking'] :
                    # if row not present then break and return error.
                    flag = 1
                    break
                if retrieved_screen_data['trackBooking'][k][str(i)] == 1:
                    # if seat already reserved then break and return error.
                    flag = 1
                    break
            if flag == 1:
                break

        # incase seats are available we update our database         
        if flag == 0:
            for k in load_data['seats']:
                for i in load_data['seats'][k]:
                     retrieved_screen_data['trackBooking'][k][str(i)] = 1
                     new_values={"$set":retrieved_screen_data}
            # update the respective screen database
            bookticket.update_one({'name':screen_name},new_values)
            return jsonify({'status' : 'OK'}),200
        else:
            return jsonify({'status' : 'Error'}),500
        
    except Exception as e:
        return jsonify({'status' : str(e)}),500


# API to get the available seats for a given screen
@app.route('/screens/<screen_name>/seats', methods=['GET'])
def available_seats(screen_name):
        # all unreserved seats for the given screen
        if 'status' in request.args:
            try:
                retrieved_screen_data = bookticket.find_one({'name':screen_name})
                display_result = {}
                # Making a key-value pair for available seats
                row_seats_reserv_status = {}
                for k in retrieved_screen_data['trackBooking']:
                    unres_seat_list = []
                    for i in retrieved_screen_data['trackBooking'][k]:
                        if retrieved_screen_data['trackBooking'][k][str(i)] == 0:
                            # if seat is unreserved we append to a list
                            unres_seat_list.append(i)
                    row_seats_reserv_status[k] = unres_seat_list

                display_result["seats"] = row_seats_reserv_status
                return jsonify(display_result)
            except Exception as e:
                return jsonify({'status' : 'Error'}),500

        # checking availability of seat according to user preference      
        elif ('numSeats' in request.args) and ('choice' in request.args):
            try:

                numSeats = request.args['numSeats']
                choice_user_row = request.args['choice'][0:1]
                choice_user_seatnum = request.args['choice'][1:]
                retrieved_screen_data = bookticket.find_one({'name':screen_name})
                display_result = {}
                row_seats_reserv_status = {}   
                max_seats_of_row = int(retrieved_screen_data['seatInfo'][choice_user_row]['numberOfSeats'])
                forward_seat_list = []
                backward_seat_list = []
                forward = int(choice_user_seatnum)
                backward = int(choice_user_seatnum)
                # To check for the available seats, the below algorithm looks for contiguous seats including the users choice.
                # We run both backward and forward to search for contiguous seats.
                # We return error if we don't find the contiguous number of seats requested by user in both the directions.

                # Searching in the forward direction, i.e. after the user's preferred seat number.
                for j in range(0,int(numSeats)):
                    if(str(forward) in retrieved_screen_data['trackBooking'][choice_user_row] and retrieved_screen_data['trackBooking'][choice_user_row][str(forward)] == 0 and max_seats_of_row>=int(numSeats)):
                        # we break as soon as we encounter a aisle seat. 
                        if(str(forward) in retrieved_screen_data['seatInfo'][choice_user_row]['aisleSeats']):
                            # insert seat numbers in our forward seat list.
                            forward_seat_list.append(forward)
                            forward+=1
                            break
                        else:
                            # otherwise we keep going until numSeats is reached.
                            forward_seat_list.append(forward)
                            forward+=1
                    # we break if seat number is invalid or seat is  already reserved.
                    else:
                        break
                    
                # Searching in the backward direction, i.e. reverse direction of the user's preferred seat number.
                for j in range(0,int(numSeats)):
                    if(str(backward) in retrieved_screen_data['trackBooking'][choice_user_row] and retrieved_screen_data['trackBooking'][choice_user_row][str(backward)] == 0 and max_seats_of_row>=int(numSeats)):
                        if(str(backward) in retrieved_screen_data['seatInfo'][choice_user_row]['aisleSeats']):
                            # insert seat numbers in our backward seat list.
                            backward_seat_list.append(backward)
                            backward-=1
                            # we break if seat is aisle except if the user's choice seat number itself is an aisle.
                            if(backward!=int(choice_user_seatnum)):
                                break
                        else:
                            backward_seat_list.append(backward)
                            backward-=1
                    # we break if seat number is invalid or seat is  already reserved.
                    else:
                        break
                # we sort the backward seat list so that seat are numbers returned in increasing order. 
                backward_seat_list.sort()
                
                # We check if any of list - forward or backward meets the user's requirement.
                if (len(forward_seat_list) == int(numSeats)) and (int(choice_user_seatnum) in forward_seat_list):
                    row_seats_reserv_status[choice_user_row] = forward_seat_list
                elif (len(backward_seat_list) == int(numSeats)) and (int(choice_user_seatnum) in backward_seat_list):
                    row_seats_reserv_status[choice_user_row] = backward_seat_list

                # forming the result to be displayed
                display_result["availableSeats"] = row_seats_reserv_status
                # If none of the lists meets the requirement we return error.
                if len(row_seats_reserv_status) == 0:
                    return jsonify({'status' : 'Seat not available. Try with a different seat number.'}),500
                return jsonify(display_result)


            except Exception as e:
                return jsonify({'status' : 'Error'}),500



    

if __name__ == '__main__':
    port = int(os.environ.get('PORT',9090))
    app.run(port=port)
