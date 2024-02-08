from flask import Flask, jsonify, request, send_file
from flask_restx import Api, Resource
from flask_migrate import Migrate
from sqlalchemy import text

from models import db, Employee, Pay, Timesheet, Image, Timecheck
from resources import payroll_ns, upload_ns, modi_ns
from flask_restx import Api, Resource, Namespace
from flask_cors import CORS
from datetime import datetime

import os

import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
CORS(app)
app.config.from_pyfile('config.py')
db.init_app(app)

api = Api(app, version='1.0', title='Timesheet API', description='Timesheet API', doc='/api-docs')
api.add_namespace(payroll_ns)
api.add_namespace(upload_ns)
api.add_namespace(modi_ns)

with app.app_context():
    db.create_all()

base_url = "http://development.localhost:8000"
api_key = "339b44c46940c17"
api_secret = "8c594aad84a012f"
token = f'{api_key}:{api_secret}'

import requests

@app.route('/users')
def users():
    #users 데이터를 Json 형식으로 반환한다.
    return {"members": [{"id" : 1, "name" : "jihyun"},
                        {"id" : 2, "name" : "jerry"}]}
    
    
@app.route('/api/employee_list', methods=['GET'])
def get_employee_list():
    token = f'{api_key}:{api_secret}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/json'
    }
    url = f'{base_url}/api/resource/Employee' 
    response = requests.get(url, headers=headers)
    print("response: ", response.json())
    get_data = response.json()["data"]
    db.session.commit()
    
    for i in range(len(get_data)): # get employee's erpNext Id
        url = f'{base_url}/api/resource/Employee/{get_data[i]["name"]}' 
        get_employee = Employee.query.filter_by(employee_id=get_data[i]["name"]).first()
        if get_employee:
            continue
        response = requests.get(url, headers=headers)
        employee_info = response.json()["data"]
        db.session.add(Employee(employee_id = employee_info["employee"], first_name = employee_info["first_name"]))
        db.session.commit()

    if response.status_code == 200:
        return response.json()
    else:
        return None



@app.route('/api/pay', methods=['GET'])
def get_pay():
    sql_query = text("""
                SELECT 
                    p.date, 
                    e.first_name AS employee_name,
                    p.total_hour, 
                    p.total_pay
                FROM 
                    pay p
                JOIN 
                    employee e ON p.employee_id = e.employee_id 
                ORDER BY 
                    p.date, e.first_name;""")
    result = db.session.execute(sql_query)
    rows = result.fetchall()
    data = []
    for row in rows:
        '''
        row[0] = date
        row[1] = employee_name
        row[2] = total_hour
        row[3] = total_pay
        '''
        get_row = {
            "time": row[0],
            "employee": row[1],
            "totalHours": int(row[2]),
            "salary": int(row[3])
        }
        data.append(get_row)
    print(data)
    return data
 
if __name__ == '__main__':
    app.run(debug = True)

