from flask_restx import Resource, Namespace
from flask import Flask, jsonify, request, current_app
import sys
from models import db, Employee, Timesheet, Timecheck, Pay
from datetime import datetime
from flask import Response
import json
from sqlalchemy import text
import requests

from ocr_final import extract_text
from werkzeug.utils import secure_filename
import os
from flask_cors import cross_origin


payroll_ns = Namespace('payroll', description='Payroll Overview Page API 목록')
    
# 업데이트된 임금 정보를 받음 
@payroll_ns.route('/payroll')
class PayrollInfoAPI(Resource):
    def get(self):
        data = [
            {
                "month": 8,
                "data": [
                    {
                        "employee": "Somi",
                        "totalHours": 55,
                        "salary": 5500
                    }
                ]
            },
           {
                "month": 7,
                "data": [
                {
                    "employee": "Jiwon",
                    "totalHours": 60,
                    "salary": 6000
                },
                {
                    "employee": "Somi",
                    "totalHours": 55,
                    "salary": 5500
                }
                ]
            },
            {
                "month": 6,
                "data": [
                {
                    "employee": "Somi",
                    "totalHours": 60,
                    "salary": 5000
                },
                {
                    "employee": "Jiwon",
                    "totalHours": 60,
                    "salary": 6000
                }
                ]
            } 
        ]
        return data;
 
#2. uploadImage page
upload_ns = Namespace('upload', description='Upload Image Page API 목록')

#타임시트지 이미지 전송
@upload_ns.route('/upload_img')
class UploadImageAPI(Resource):
    @cross_origin()
    def post(self):
        if 'img_file' not in request.files:
            return {"error": "No file part"}, 400

        file = request.files['img_file']
        if file.filename == '':
            return {"error": "No selected file"}, 400

        # 파일 저장
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # OCR 처리
        try:
            employee_name, manager_name, weekStart, header, data, employeeSign, managerSign = extract_text(filepath)
            # 처리 결과를 바탕으로 응답 데이터 생성
            response_data = {
                "employee_name": employee_name,
                "manager_name": manager_name,
                "weekStart": weekStart,
                "header": header,
                "data": data,
                "employeeSign": employeeSign,
                "managerSign": managerSign
            }
            print("확인:", response_data)
            return jsonify(response_data), 200
        except Exception as e:
            return {"error": str(e)}, 500

    
 
#3. modifyInfo page
modi_ns = Namespace('modify', description='Modify Info Page API 목록')

#ocr 결과 받음
@modi_ns.route('/ocr-result')
class OcrResultAPI(Resource):
    @modi_ns.doc('get_ocr_result',
                 description='OCR 처리된 결과를 가져옵니다.', 
                 responses={200: '성공', 400: '요청 오류'})
    def get(self):
    	return {"hello" : "restx"}

#편집된 타임시트지 전송
@modi_ns.route('/timesheet-edit')
class ModiAPI(Resource):
    @modi_ns.doc('save_timesheet_edit')
    def post(self):
        json_data = request.get_json()

        print('Json data: ', json_data)
        employee_name = json_data['name']
        print('employee name: ', employee_name)

        # Employee 검색
        employee = Employee.query.filter_by(first_name=employee_name).first()
        if not employee:
            print('!!!!No name!!!!')
            return jsonify({"message": "Employee not found"}), 404
        else: 
            print("!!!!yes name")
        # Timesheet 생성 및 저장
        print("json_data: ", json_data)
        timesheet = Timesheet(
            employee_id=employee.employee_id,
            week_starting_date=datetime.strptime(json_data['week_starting_date'], '%m/%d/%Y'),
            pay_per_hour=int(json_data['ratePerHour']),
            over_time_pay=int(json_data['overtimePay']),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(timesheet)
        db.session.commit()  # Timesheet 커밋

        # Timecheck 생성 및 저장
        for entry in json_data['data']:
            date = datetime.strptime(entry['date'], '%m/%d/%Y')
            in_time = datetime.strptime(entry['timeIn'], '%H:%M').time()
            out_time = datetime.strptime(entry['timeOut'], '%H:%M').time()
            timecheck = Timecheck(
                timesheet_id=timesheet.id,
                date=datetime.combine(date, datetime.min.time()),
                in_time=datetime.combine(date, in_time),
                out_time=datetime.combine(date, out_time),
                late_entry=False,
                early_exit=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(timecheck)
            db.session.commit()
            frappe_response_attendance = frappe_attendance(
                attendance_date=datetime.combine(date, datetime.min.time()), 
                status= "Present",
                employee_id = employee.employee_id,
                late_entry = 0,
                early_exit= 0)
            frappe_response_checkin = frappe_checkin(
                employee_id= employee.employee_id,
                in_time=datetime.combine(date, in_time),
                out_time=datetime.combine(date, out_time)
            )
            response_pay = payroll(
                employee_id=employee.employee_id, 
                timesheet_id=timesheet.id, 
                hourly_pay=timesheet.pay_per_hour, 
                week_starting_date=timesheet.week_starting_date
                )
        print("attendance: ", frappe_response_attendance)
        print("check: ",frappe_response_checkin)
        print("pay: ", response_pay, timesheet.week_starting_date, timesheet.pay_per_hour)

        # 응답 객체 생성
        response_data = {"message": "Timesheet data saved successfully"}
        print("Response data:", response_data)  # 콘솔에 출력하여 확인
        return Response(
            response=json.dumps(response_data),
            status=200,
            mimetype='application/json'
        )
        #return jsonify({"message": "Timesheet data saved successfully"}), 200
            

def frappe_attendance(attendance_date, status, employee_id, late_entry = None,early_exit=None):
    url = 'http://development.localhost:8000/api/method/hrms.hr.doctype.attendance.attendance.mark_attendance'    
    headers = {
       'Authorization': 'token 339b44c46940c17:8c594aad84a012f'
    }

    db_param = {
        "attendance_date" : attendance_date,
        "status" : status,
        "employee" : employee_id,
        "late_entry" : late_entry,
        "early_exit" : early_exit
    }

    response = requests.post(url, headers=headers, params=db_param)

    if response.status_code == 200:
        return response
    else:
        return f"Error: {response.status_code}"
    
def frappe_checkin(employee_id, in_time, out_time):
    url = 'http://development.localhost:8000/api/method/hrms.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field'
    
    headers = {
       'Authorization': 'token 339b44c46940c17:8c594aad84a012f'
    }
    db_param_in = {
        "employee_field_value": employee_id,
        "timestamp": in_time,
        "log_type" : "IN",
        "employee_fieldname" : "employee"
    }
    db_param_out = {
        "employee_field_value": employee_id,
        "timestamp" : out_time,
        "log_type" : "OUT",
        "employee_fieldname" : "employee"
    }

    # # Log information about the incoming request
    # print(f"Connection from {request.remote_addr}")

    response = requests.post(url, headers=headers, params=db_param_in)
    response = requests.post(url, headers=headers, params=db_param_out)
    print(response.text)

    if response.status_code == 200:
        return response
    else:
        return f"Error: {response.status_code}"
    
def payroll(employee_id, timesheet_id, hourly_pay, week_starting_date):
    
    weekly_work_hours = 0.0
    weekly_work_payment = 0.0

    base_pay = hourly_pay # 기본 시급
    evening_rate = 1.5  # 오후 6시부터 10시까지의 급여 요율
    night_rate = 2.0  # 오후 10시부터 오전 4시까지의 급여 요율

    sql_query = text("""
        SELECT 
            date,
            total_work_hours,
            CASE 
                WHEN total_work_hours <= 8 THEN total_work_hours * :base_pay
                WHEN total_work_hours > 8 AND max_out_time <= '2024-01-01 18:00:00' THEN (8 * :base_pay) + ((total_work_hours - 8) * :evening_pay)
                WHEN total_work_hours > 8 AND max_out_time > '2024-01-01 18:00:00' AND max_out_time <= '2024-01-01 22:00:00' THEN (8 * :base_pay) + ((total_work_hours - 8) * :evening_pay)
                WHEN total_work_hours > 8 AND (max_out_time > '2024-01-01 22:00:00' OR min_in_time < '2024-01-01 04:00:00') THEN (8 * :base_pay) + ((total_work_hours - 8) * :night_pay)
                ELSE total_work_hours * :base_pay
            END AS daily_wage,
            LEAST(total_work_hours, 8) AS regular_work_hours,
            GREATEST(total_work_hours - 8, 0) AS overtime_hours
        FROM (
            SELECT 
                date,
                SUM(TIMESTAMPDIFF(HOUR, in_time, out_time)) AS total_work_hours,
                MAX(out_time) AS max_out_time,
                MIN(in_time) AS min_in_time
            FROM 
                timecheck
            WHERE 
                timesheet_id = :timesheet_id
                AND date >= :week_starting_date AND date < DATE_ADD(:week_starting_date, INTERVAL 7 DAY)
            GROUP BY 
                date
        ) AS daily_work_hours
        ORDER BY 
            date;
    """)

    params = {
        'base_pay': base_pay, 
        'evening_pay': base_pay * evening_rate, 
        'night_pay': base_pay * night_rate, 
        'timesheet_id': timesheet_id, 
        'week_starting_date' : week_starting_date
    }

    result = db.session.execute(sql_query, params)

    rows = result.fetchall()

    for row in rows:
        '''
        row[0] = date
        row[1] = total_work_hours
        row[2] = daily_wage
        row[3] = regular_work_hours
        row[4] = overtime_hours
        '''
        temp_work_hours = 45 - weekly_work_hours
        if 8 >= temp_work_hours >=0:
            row[2] += base_pay * 0.5 * (float(row[3]) - temp_work_hours)
        elif temp_work_hours <= 0:
            row[2] += base_pay * 0.5 * float(row[3])
        weekly_work_hours += float(row[1])
        get_date = str(row[0].year) +"-" + str(row[0].month).zfill(2)
        weekly_work_payment += float(row[2])

        get_pay = Pay.query.filter_by(employee_id = employee_id, date = get_date).first()
        if get_pay:
            get_pay.total_hour += weekly_work_hours
            get_pay.total_pay += weekly_work_payment
            db.session.commit()
        else:
            db.session.add(Pay(date = get_date, employee_id = employee_id, total_hour = weekly_work_hours, total_pay = weekly_work_payment))
            db.session.commit()
    return "good"