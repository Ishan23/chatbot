from random import randint
import requests
import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def getSuggestions(city,cuisine,people,date,time,phone):
    
    
    header = {"User-agent": "curl/7.43.0", "Accept": "application/json", "user_key": "0479f13c4080048d75740c3f28ac78a0"}
    cuisines={}
    cuisineID=None
    
    city=str(city)
    cuisine=str(cuisine)
    
    if city.lower() in ['new york','nyc','new york city','ny','manhhatan','bronx','staten island','brooklyn','queens']:
        cityURL = 'https://developers.zomato.com/api/v2.1/cities?q=new%20york%20city&count=1'
    elif city.lower() in ['los angeles','la']:
        cityURL = 'https://developers.zomato.com/api/v2.1/cities?q=los%20angeles&count=1'
    else:
        cityURL = 'https://developers.zomato.com/api/v2.1/cities?q='+city.lower()+'&count=1'
        
    response = requests.get(cityURL, headers=header)
    data=response.json()
    data=data['location_suggestions']
    data=data[0]
    cityID=data['id']
    
    cuisineURL = 'https://developers.zomato.com/api/v2.1/cuisines?city_id='

    response = requests.get(cuisineURL+str(cityID), headers=header)
    data=response.json()
    data=data['cuisines']
    
    for i in data:
        j=i['cuisine']
        cuisines[j['cuisine_name'].lower()]=j['cuisine_id']
        
    if cuisine.lower() in cuisines:
        cuisineID=cuisines[cuisine.lower()]
        
    URL='https://developers.zomato.com/api/v2.1/search?entity_id='+str(cityID)+'&entity_type=city&cuisines='+str(cuisineID)
    
    response = requests.get(URL, headers=header)
    data=response.json()
    data=data['restaurants']
    suggestions=[] #
    for i in data:
        j=i['restaurant']
        name=j['name']
        addr=j['location']
        address=addr['address']+'  \n' + addr['city']
        menu_url=j['menu_url']
        cuis=j['cuisines']
        rating=j['user_rating']['aggregate_rating']
        url=j['url']

        s={
            'name':name,
            'address':address,
            'rating':rating,
            'menu':menu_url,
            'cuisine':cuis,
            'url':url}

        suggestions.append(s)

    if suggestions:
        print(suggestions[0])
    
        
    sendSMS(suggestions,phone)
    
    #pushDynamo(city,cuisine,people,date,time,phone,suggestions)
    
    
'''    
def pushDynamo(city,cuisine,people,date,time,phone,suggestions):
    
    q_id=randint(10000,99999)
    
    dynamo=boto3.resource('dynamodb')
    table=dynamo.Table('DiningTable')
    
    table.put_Item(Item={
        
        "q_id":q_id;
        
        "input":{
            'city':city,
            'cuisine':cuisine,
            'people':people,
            'date':date,
            'time':time,
            'phone':phone
        }
            
        'output':{
            
            [
                {
                'name':suggestions[0]['name'],
                'address':suggestions[0]['address'],
                'rating':suggestions[0]['rating'],
                'cuisine':suggestions[0]['cuisine'],
                'menu':suggestions[0]['menu'],
                'url':suggestions[0]['url']
                },
                {
                'name':suggestions[1]['name'],
                'address':suggestions[1]['address'],
                'rating':suggestions[1]['rating'],
                'cuisine':suggestions[1]['cuisine'],
                'menu':suggestions[1]['menu'],
                'url':suggestions[1]['url']
                },
                {
                'name':suggestions[2]['name'],
                'address':suggestions[2]['address'],
                'rating':suggestions[2]['rating'],
                'cuisine':suggestions[2]['cuisine'],
                'menu':suggestions[2]['menu'],
                'url':suggestions[2]['url']
                }
                
            ]
                
            }    
        
    })
        
   ''' 
    
        
def sendSMS(suggestions,phone):
    
    phn = str(phone)
    phn = '+1' + phn
    
    template='Here are your Dining suggestions:\n '
    
    if len(suggestions)>2:
        for i in range(3):
            
            s=suggestions[2-i]
            name=s['name']
            address=s['address']
            rating=s['rating']
            menu=s['menu']
            url=s['url']
            
            index=str(i+1)+'.   '
            
            x='\n\n\n'+index + name.upper() + '\n\n' + 'Address: '+ address + '\n\nRating: ' + rating + '\n\nMenu: ' + menu + '\n\nMore info: ' + url
            template = template + x
            
            
            
    else:
        for i in range(len(suggestions)):
            
            s=suggestions[len(suggestions)-i-1]
            name=s['name']
            address=s['address']
            rating=s['rating']
            menu=s['menu']
            url=s['url']
            
            index=str(i+1)+'.   '
            
            x='\n\n\n'+index + name.upper() + '\n\n' + 'Address: '+ address + '\n\nRating: ' + rating + '\n\nMenu: ' + menu + '\n\nMore Info: ' + url
            template = template + x
        
    msg = template + '\nBon Appetite!'
    
    client = boto3.client('sns')
    client.publish(
        PhoneNumber=phn,
        Message=msg
        )
    
    
def getFromSQS():
    
    city=None
    cuisine=None
    people=None
    date=None
    time=None
    phone=None
    nullCheck=0
    
    # Get the service resource
    sqs = boto3.resource('sqs')

    # Get the queue
    queue = sqs.get_queue_by_name(QueueName='test')

    # Process messages by printing out body and optional author name
    for message in queue.receive_messages(MessageAttributeNames=['location','cuisine','people','date','time','phone']):
    # Get the custom author message attribute if it was set
        city = message.message_attributes.get('location').get('StringValue')
        cuisine = message.message_attributes.get('cuisine').get('StringValue')
        people = message.message_attributes.get('people').get('StringValue')
        date = message.message_attributes.get('date').get('StringValue')
        time = message.message_attributes.get('time').get('StringValue')
        phone = message.message_attributes.get('phone').get('StringValue')
        nullCheck+=1
        

        # Let the queue know that the message is processed
        message.delete()
        
    if nullCheck==0:
        return
    
    print(str(city))
    print(str(cuisine))
    print(str(people))
    print(str(date))
    print(str(time))
    print(str(phone))
    
    getSuggestions(city,cuisine,people,date,time,phone)

def lambda_handler(event, context):
    # TODO implement
    
    
    getFromSQS()
    
    return 