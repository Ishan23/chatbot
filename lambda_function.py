"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages orders for flowers.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'OrderFlowers' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
            'message': {'contentType': 'PlainText', 'content': message_content}
            
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def validate_dining(city,cuisine,people,date,time,phone):
    
    locations = ['new york', 'new york city', 'nyc', 'manhhatan', 'brooklyn', 'queens', 'staten island', 'bronx', 'la', 'l.a', 'n.y.c','los angeles',
                'san francisco','seattle','san jose','boston','chicago','washington dc']
                
    cuisines = ['indian','chinese','japanese','korean','south indian','thai','british','french','italian','spanish','lebanese','continental','mexican',
                'amaerican','breakfast','seafood','fast food','steak','pizza','burmese','vietnamese']
                
    if city is not None and city.lower() not in locations:
        return build_validation_result(False,
                                       'city',
                                       'Sorry! I do not know any places to eat in {}, Please choose some other place.  '
                                       'I know some great resteraunts in New York City'.format(city))
    
                                       
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'cuisine',
                                       'Sorry! There are no good places for {} in this area, please choose some other cuisine.  '
                                       'I know some great Indian resteraunts'.format(cuisine))
                                       
    if people is not None:
        
        if int(people)<1:
            return build_validation_result(False,
                                       'people',
                                       'Sorry! There are should be atleast one person.  '
                                       'Please tell me the number of people again'.format(cuisine))
                                       
        if int(people)>10:
            return build_validation_result(False,
                                       'people',
                                       'Sorry! There are no resteraunts which can accomodate {} people.  '
                                       'Please tell me the number of people again'.format(people))
                                       
    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to dine?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'date', 'You can only see dining options from tomorrow onwards. Please choose a new date')
            
    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        hour, minute = time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        if hour < 8:
            # Outside of business hours
            return build_validation_result(False, 'time', 'Sorry, there are no resteraunts open at the given time. Can you choose some other time?')
            
        if phone is not None:
            if len(phone)!=10:
                return build_validation_result(False,
                                       'phone','This number is not valid. Please enter a valid mobile number to get restraunt suggestions.')
                                       
    
    return build_validation_result(True, None, None)
    
    
    
def validate_order_flowers(flower_type, date, pickup_time):
    flower_types = ['lilies', 'roses', 'tulips']
    if flower_type is not None and flower_type.lower() not in flower_types:
        return build_validation_result(False,
                                       'FlowerType',
                                       'We do not have {}, would you like a different type of flower?  '
                                       'Our most popular flowers are roses'.format(flower_type))

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'PickupDate', 'I did not understand that, what date would you like to pick the flowers up?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'PickupDate', 'You can pick up the flowers from tomorrow onwards.  What day would you like to pick them up?')

    if pickup_time is not None:
        if len(pickup_time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'PickupTime', None)

        hour, minute = pickup_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'PickupTime', None)

        if hour < 10 or hour > 16:
            # Outside of business hours
            return build_validation_result(False, 'PickupTime', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    return build_validation_result(True, None, None)


def invokeSQS(intent_request):
    
    location = get_slots(intent_request)["city"]
    cuisine = get_slots(intent_request)["cuisine"]
    people = get_slots(intent_request)["people"]
    date = get_slots(intent_request)["date"]
    time = get_slots(intent_request)["time"]
    phone = get_slots(intent_request)["phone"]
    source = intent_request['invocationSource']
    print(str(source))
    
    #Create a queue
    # Get the service resource
    sqs = boto3.resource('sqs')

    # Create the queue. This returns an SQS.Queue instance
    queue = sqs.create_queue(QueueName='test', Attributes={'DelaySeconds': '5'})

    # You can now access identifiers and attributes
    print(queue.url)
    
    response=queue.send_message(MessageBody='For Lambda2', MessageAttributes={
    'location': {
        'StringValue': location,
        'DataType': 'String'
        },
    'cuisine': {
        'StringValue': cuisine,
        'DataType': 'String'
        },
    'people': {
        'StringValue': people,
        'DataType': 'Number'
        },
    'date': {
        'StringValue': date,
        'DataType': 'String'
        },
    'time': {
        'StringValue': time,
        'DataType': 'String'
        },
    'phone': {
        'StringValue': phone,
        'DataType': 'Number'
        }
    })
    
    print(response.get('MessageId'))
    print(response.get('MD5OfMessageBody'))
   
  

""" --- Functions that control the bot's behavior --- """
def greeting(intent_request):
    
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
        
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        #if flower_type is not None:
          #  output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))
    
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hi! How may I help you?'})


def dining_suggestion_intent(intent_request):
    
    
   
    
    location = get_slots(intent_request)["city"]
    #location={}
    cuisine = get_slots(intent_request)["cuisine"]
    people = get_slots(intent_request)["people"]
    date = get_slots(intent_request)["date"]
    time = get_slots(intent_request)["time"]
    phone = get_slots(intent_request)["phone"]
    source = intent_request['invocationSource']
    
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
        
        validation_result = validate_dining(location,cuisine,people,date,time,phone)
        
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
        
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        #if flower_type is not None:
          #  output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))
    
    invokeSQS(intent_request)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'You are all set! Expect my recommendations shortly! Have a good day!'})
   




def order_flowers(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """
    

    flower_type = get_slots(intent_request)["FlowerType"]
    date = get_slots(intent_request)["PickupDate"]
    pickup_time = get_slots(intent_request)["PickupTime"]
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_order_flowers(flower_type, date, pickup_time)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        if flower_type is not None:
            output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thanks, your order for {} has been placed and will be ready for pickup by {} on {}'.format(flower_type, pickup_time, date)})


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'OrderFlowers':
        return order_flowers(intent_request)
        
    if intent_name == 'GreetingIntent':
        return greeting(intent_request)
        
    if intent_name == 'DiningSuggestionIntent':
        return dining_suggestion_intent(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
