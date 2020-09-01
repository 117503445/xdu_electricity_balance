import requests
import re
import json
import file_util
from flask import Flask, escape, request, render_template, jsonify
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask("xdu_electricity_balance")

port = '80'


class EnergySession(requests.Session):
    BASE = 'http://10.168.55.50:8088'

    def __init__(self, username, password, *args, **kwargs):
        super(EnergySession, self).__init__(*args, **kwargs)
        self.get(self.BASE + "/searchWap/Login.aspx")
        self.post(
            self.BASE + "/ajaxpro/SearchWap_Login,App_Web_fghipt60.ashx",
            json={
                "webName": username,
                "webPass": password
            }, headers={
                "AjaxPro-Method": "getLoginInput",
                'Origin': self.BASE
            }
        )


def crawl(username, password):
    ses = EnergySession(username, password)
    balance_page = ses.get(
        'http://10.168.55.50:8088/searchWap/webFrm/met.aspx'
    ).text
    pattern_name = re.compile('表名称：(.*?)  ', re.S)
    name = re.findall(pattern_name, balance_page)
    pattern_balance = re.compile('剩余量：(.*?) </td>', re.S)
    balance = re.findall(pattern_balance, balance_page)
    s = ''
    kede_s = ''
    for n, b in zip(name, balance):
        s_n = str(n).replace('\r', '').replace('\n', '')
        s += f'表名: {s_n}剩余量: {float(b)}\n'
        if '科德' in n:
            kede_s = float(b)
    return s, kede_s


@app.route('/api/me', methods=['get'])
def me():
    print('me')

    js = file_util.read_all_text('config.json')
    js = json.loads(js)

    users = js['users']

    s = ''

    for user in users:
        print(user['username'], user['password'], )
        serverchans = user['serverchan']
        res, kede = crawl(user['username'], user['password'])
        s += res + '\n'
        for serverchan in serverchans:
            requests.get(
                f'https://sc.ftqq.com/{serverchan}.send?text=电表剩余量{kede}&desp={res}')

    return res


class APSchedulerJobConfig(object):
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'
    JOBS = [
        {
            'id': 'me',
            'func': me,
            'args': '',
            'trigger': {
                'type': 'cron',
                'day_of_week': "0-6",
                'hour': '7',
                'minute': '0',
                'second': '0'
            }
        }
    ]


def init():
    global port
    js = file_util.read_all_text('config.json')
    js = json.loads(js)
    port = js['port']

    app.config.from_object(APSchedulerJobConfig)
    # 初始化Flask-APScheduler，定时任务
    scheduler = APScheduler(BackgroundScheduler(timezone="Asia/Shanghai"))
    scheduler.init_app(app)
    scheduler.start()


def main():
    init()
    global port
    app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    main()
